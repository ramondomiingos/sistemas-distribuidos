#!/bin/bash

# =============================================================================
# benchmark.sh — Benchmark completo do middleware LGPD
#
# Ordem de execução:
#   1. Limpeza inicial do banco (única vez)
#   2. Experimento de escalabilidade: 1 → 2 → 3 → 4 serviços (20 runs cada = 80 total)
#      → Os 20 runs com 4 serviços TAMBÉM servem como benchmark principal.
#         Não há loop separado para o benchmark — os dados são coletados
#         duplamente nessa fase (scalability_summary.csv + benchmark_summary.csv).
#   3. Análise estatística (analyze_results.py)
#   4. Export do banco de dados (CSV + dump SQL)
#
# Ao final, TODAS as requisições permanecem no banco para consultas posteriores.
#
# Independência entre execuções:
#   - Cada run insere 900 contas com UUIDs novos (sem colisão de dados)
#   - Containers de aplicação são reiniciados entre runs para zerar estado
#     em memória e reconectar consumidores Kafka
#   - Bancos e Kafka NÃO são reiniciados entre runs
#
# Saída:
#   output-benchmark/scalability/               — experimento de escalabilidade (80 runs)
#   output-benchmark/benchmark_run_N_*.csv      — stats de recursos (20 runs do n=4)
#   output-benchmark/completude_run_N_*.json    — completude por run (20 runs do n=4)
#   output-benchmark/benchmark_summary.csv      — resumo dos 20 runs com 4 serviços
#   output-benchmark/benchmark_analysis.json    — estatísticas agregadas
#   output-benchmark/db_export/                 — CSV + dump SQL do banco ao final
# =============================================================================

set -eo pipefail

cd "$(dirname "$0")/.."

PYTHON=$(command -v python3 || command -v python)
if [ -z "$PYTHON" ]; then
    echo "ERRO: Python 3 não encontrado." >&2
    exit 1
fi

JMETER=$(command -v jmeter || true)
if [ -z "$JMETER" ]; then
    echo "ERRO: jmeter não encontrado." >&2
    echo "  macOS:  brew install jmeter" >&2
    echo "  Linux:  https://jmeter.apache.org/download_jmeter.cgi" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
REPOUSO_DURATION=60
POS_WAIT_INITIAL=15
POS_TIMEOUT=120   # 2PC max = 30s validate + 60s execute + 30s margem
SCALE_RUNS=20
OUTPUT_DIR="output-benchmark"
SCALE_DIR="$OUTPUT_DIR/scalability"

SCALE_SVC_NAMES=("account"   "payment"   "crm"   "delivery")
SCALE_CONTAINERS=("accounts" "payments"  "crm"   "delivery")
SCALE_PORTS=(8002 8001 8003 8004)   # porta externa conforme docker-compose.yml
# Prefixo real dos consumer groups Kafka (deve bater com group_id em cada main.py)
SCALE_KAFKA_GROUPS=("accounts"  "payment"   "crm"   "delivery")
SCALE_DESCS=(
    "Autentica e autoriza o acesso de usuários a recursos e funcionalidades do sistema."
    "Gerencia o fluxo de valor monetário entre entidades e integra-se com gateways de pagamento."
    "Centraliza e organiza dados relacionados a interações com clientes e histórico de comunicação."
    "Coordena a movimentação física de bens, rastreamento em tempo real e comunicação com transportadoras."
)

mkdir -p "$OUTPUT_DIR" "$SCALE_DIR"

# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------
PHASE_FILE="/tmp/benchmark_phase_$$"
ALL_STATS_PIDS=()   # Rastreia todos os PIDs de coleta para o trap

# ---------------------------------------------------------------------------
# Trap: mata todos os processos filhos de coleta ao sair (Ctrl+C, erro, etc.)
# ---------------------------------------------------------------------------
cleanup_on_exit() {
    echo ""
    echo "  [trap] Encerrando processos filhos de coleta de stats..."
    for pid in "${ALL_STATS_PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    [ -n "${STATS_PID:-}" ] && kill "$STATS_PID" 2>/dev/null || true
    rm -f "$PHASE_FILE" 2>/dev/null || true
    echo "  [trap] Processos encerrados."
}
trap cleanup_on_exit EXIT INT TERM

start_stats_collection() {
    local output_csv="$1"
    echo "Data_Hora,Fase,ID_Container,Nome,CPU_%,Mem_Usage,Mem_%,Net_IO,Block_IO" > "$output_csv"
    echo "repouso" > "$PHASE_FILE"
    (
        while true; do
            TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
            CURRENT_PHASE=$(cat "$PHASE_FILE" 2>/dev/null || echo "unknown")
            docker stats --no-stream --format "{{.ID}},{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.BlockIO}}" | \
                awk -v ts="$TIMESTAMP" -v phase="$CURRENT_PHASE" '{print ts "," phase "," $0}' >> "$output_csv"
            sleep 1
        done
    ) &
    STATS_PID=$!
    ALL_STATS_PIDS+=("$STATS_PID")
}

set_phase() { echo "$1" > "$PHASE_FILE"; }

stop_stats_collection() {
    kill "$STATS_PID" 2>/dev/null || true
    wait "$STATS_PID" 2>/dev/null || true
    rm -f "$PHASE_FILE"
}

wait_middleware_healthy() {
    local MAX="${1:-36}"
    local ATTEMPTS=0
    until curl -s http://localhost:8000/health | grep -q "healthy" || [ "$ATTEMPTS" -ge "$MAX" ]; do
        ATTEMPTS=$((ATTEMPTS + 1))
        echo "    aguardando middleware... tentativa ${ATTEMPTS}/${MAX}"
        sleep 5
    done
    if [ "$ATTEMPTS" -ge "$MAX" ]; then
        echo "ERRO: Middleware não respondeu. Verifique 'docker compose logs middleware'." >&2
        exit 1
    fi
}

wait_container_healthy() {
    local port="$1" label="$2"
    local ATTEMPTS=0
    until curl -s "http://localhost:${port}/health" | grep -q "healthy" || [ "$ATTEMPTS" -ge 24 ]; do
        ATTEMPTS=$((ATTEMPTS + 1)); sleep 5
    done
    if [ "$ATTEMPTS" -ge 24 ]; then
        echo "  AVISO: ${label} não respondeu em 120s."
    fi
}

register_one_service() {
    local name="$1" desc="$2"
    curl -s -X POST http://localhost:8000/api/v1/services/ \
        -H "Content-Type: application/json" \
        -d "{\"service_name\": \"${name}\", \"description\": \"${desc}\"}" > /dev/null
    echo "  [scale] '${name}' registrado."
}

# Aguarda os consumer groups Kafka do serviço terem um membro ativo com partition
# assignment (evita auto_offset_reset="latest" pulando mensagens publicadas antes
# do consumer completar o primeiro fetch e registrar seu offset).
wait_kafka_consumers_ready() {
    local kafka_prefix="$1"   # prefixo real do group_id (ex: "accounts", "payment")
    local validate_group="${kafka_prefix}-validate-group"
    local execute_group="${kafka_prefix}-execute-group"
    local ATTEMPTS=0
    echo "  [kafka] Aguardando consumers ativos: ${validate_group} / ${execute_group}..."
    # Usa awk para verificar que a coluna CONSUMER-ID (col 7) não é "-".
    # grep -q "." passa mesmo quando o grupo existe mas não tem membro ativo
    # (o --describe retorna a linha com CONSUMER-ID="-"), então o awk é necessário.
    until ( docker compose exec -T kafka kafka-consumer-groups.sh \
                --bootstrap-server localhost:9092 \
                --describe --group "${validate_group}" 2>/dev/null \
              | awk 'NR>1 && $7 != "-" {found=1} END {exit !found}' ) && \
          ( docker compose exec -T kafka kafka-consumer-groups.sh \
                --bootstrap-server localhost:9092 \
                --describe --group "${execute_group}" 2>/dev/null \
              | awk 'NR>1 && $7 != "-" {found=1} END {exit !found}' ) || \
          [ "$ATTEMPTS" -ge 24 ]; do
        ATTEMPTS=$((ATTEMPTS + 1)); sleep 5
    done
    if [ "$ATTEMPTS" -ge 24 ]; then
        echo "  AVISO: consumers de '${kafka_prefix}' não ficaram prontos em 120s."
    else
        echo "  [kafka] Consumers de '${kafka_prefix}' prontos (${ATTEMPTS} tentativas)."
    fi
}

# Para, zera offsets Kafka e sobe os containers indicados (não mexe no banco).
# Regra: consumer lag deve ser zerado (--to-latest) ANTES de subir qualquer
# container consumidor, garantindo que o próximo run não processe mensagens
# residuais de runs anteriores (especialmente se o run anterior não completou
# 100% dentro do timeout e deixou mensagens sem commit).
cleanup_containers() {
    local containers="$*"
    echo "  [cleanup] Parando: ${containers}..."
    docker compose stop $containers

    echo "  [cleanup] Zerando offsets Kafka dos serviços ativos..."
    for i in $(seq 0 $((n_svcs-1))); do
        local prefix="${SCALE_KAFKA_GROUPS[$i]}"
        docker compose exec -T kafka kafka-consumer-groups.sh \
            --bootstrap-server localhost:9092 \
            --group "${prefix}-validate-group" \
            --topic "privacy-validate-topic" \
            --reset-offsets --to-latest --execute 2>/dev/null || true
        docker compose exec -T kafka kafka-consumer-groups.sh \
            --bootstrap-server localhost:9092 \
            --group "${prefix}-execute-group" \
            --topic "privacy-execute-topic" \
            --reset-offsets --to-latest --execute 2>/dev/null || true
    done
    docker compose exec -T kafka kafka-consumer-groups.sh \
        --bootstrap-server localhost:9092 \
        --group "middleware-group-privacy-validate-response-topic" \
        --topic "privacy-validate-response-topic" \
        --reset-offsets --to-latest --execute 2>/dev/null || true
    docker compose exec -T kafka kafka-consumer-groups.sh \
        --bootstrap-server localhost:9092 \
        --group "middleware-group-privacy-execute-response-topic" \
        --topic "privacy-execute-response-topic" \
        --reset-offsets --to-latest --execute 2>/dev/null || true

    echo "  [cleanup] Subindo: ${containers}..."
    docker compose start $containers
    wait_middleware_healthy 36
    echo "  [cleanup] Pronto."
}

check_completude() {
    python3 tools/check_completude.py \
        --run "$1" \
        --account-ids "$2" \
        --output "$3" \
        --ts-inicio "$4" \
        --summary "$5"
}

# Fase pós: espera ativa até FINISHED ou timeout
wait_finished() {
    local ts_inicio="$1"
    sleep "$POS_WAIT_INITIAL"
    local WAIT_ELAPSED=$POS_WAIT_INITIAL
    while [ "$WAIT_ELAPSED" -lt "$POS_TIMEOUT" ]; do
        local PENDING
        PENDING=$(docker compose exec -T middleware_db psql -U user -d middlewaredb -t -A \
            -c "SELECT COUNT(*) FROM privacy_requests WHERE status NOT IN ('FINISHED','FAILED') AND created_at >= '${ts_inicio}';" \
            2>/dev/null || echo "0")
        PENDING=$(echo "$PENDING" | tr -d '[:space:]')
        if [ "$PENDING" = "0" ]; then
            echo "  [pos] Todas finalizadas em ${WAIT_ELAPSED}s."
            break
        fi
        echo "  [pos] ${WAIT_ELAPSED}s: ${PENDING} pendentes..."
        sleep 5
        WAIT_ELAPSED=$((WAIT_ELAPSED + 5))
    done
    if [ "$WAIT_ELAPSED" -ge "$POS_TIMEOUT" ]; then
        echo "  [pos] Timeout ${POS_TIMEOUT}s — seguindo."
    fi
}

# ---------------------------------------------------------------------------
# Aguarda middleware inicializar
# ---------------------------------------------------------------------------
echo ""
echo "  [init] Aguardando middleware ficar disponível..."
wait_middleware_healthy 30
echo "  [init] Middleware disponível."

# ---------------------------------------------------------------------------
# Limpeza inicial do banco — UMA ÚNICA VEZ
# Garante estado limpo antes de qualquer experimento.
# Após isso, nenhum dado é apagado até o fim do benchmark.
# ---------------------------------------------------------------------------
echo ""
echo "  [init] Limpando banco de dados para início limpo..."
docker compose exec -T middleware_db psql -U user -d middlewaredb -c "
    TRUNCATE TABLE privacy_requests_services CASCADE;
    TRUNCATE TABLE privacy_requests CASCADE;
    DELETE FROM services;
" > /dev/null
echo "  [init] Banco limpo."

# Reseta os offsets de TODOS os consumer groups para "latest".
# Motivação: os tópicos acumulam mensagens de sessões anteriores.
# O middleware tem lag de dezenas de milhares de mensagens antigas nos tópicos de
# resposta, o que faz ele demorar minutos processando backlog histórico antes de
# chegar nas mensagens do run atual → POS_TIMEOUT estoura → 0% completude.
# Os serviços (crm, delivery) também acumulam lag nos tópicos de validate/execute.
# O --reset-offsets exige que os consumers estejam PARADOS; por isso paramos o
# middleware primeiro (os serviços já estão parados neste ponto).
# Para TODOS os serviços e middleware antes do reset.
# O --reset-offsets exige que NENHUM consumer esteja ativo no grupo.
# Se o container estiver rodando com consumers, o reset é rejeitado pelo Kafka.
echo "  [init] Parando todos os containers de serviço e middleware para reset limpo..."
docker compose stop middleware accounts payments crm delivery

echo "  [init] Resetando offsets dos consumer groups do middleware (response topics)..."
docker compose exec -T kafka kafka-consumer-groups.sh \
    --bootstrap-server localhost:9092 \
    --group "middleware-group-privacy-validate-response-topic" \
    --topic "privacy-validate-response-topic" \
    --reset-offsets --to-latest --execute
docker compose exec -T kafka kafka-consumer-groups.sh \
    --bootstrap-server localhost:9092 \
    --group "middleware-group-privacy-execute-response-topic" \
    --topic "privacy-execute-response-topic" \
    --reset-offsets --to-latest --execute

echo "  [init] Resetando offsets dos consumer groups dos serviços (validate/execute topics)..."
for svc_prefix in accounts payment crm delivery; do
    docker compose exec -T kafka kafka-consumer-groups.sh \
        --bootstrap-server localhost:9092 \
        --group "${svc_prefix}-validate-group" \
        --topic "privacy-validate-topic" \
        --reset-offsets --to-latest --execute 2>/dev/null || true
    docker compose exec -T kafka kafka-consumer-groups.sh \
        --bootstrap-server localhost:9092 \
        --group "${svc_prefix}-execute-group" \
        --topic "privacy-execute-topic" \
        --reset-offsets --to-latest --execute 2>/dev/null || true
done

echo "  [init] Reiniciando middleware após reset..."
docker compose start middleware
wait_middleware_healthy 36
echo "  [init] Offsets resetados e middleware pronto."

# ===========================================================================
# PARTE 1 — EXPERIMENTO DE ESCALABILIDADE (1 → 4 serviços)
# ===========================================================================
echo ""
echo "========================================================"
echo " PARTE 1: EXPERIMENTO DE ESCALABILIDADE"
echo " ${SCALE_RUNS} runs × 4 configurações (1→2→3→4 serviços)"
echo "========================================================"

SCALE_SUMMARY="$SCALE_DIR/scalability_summary.csv"
echo "n_servicos,servicos,run,timestamp_inicio,total_submetido,total_finished,total_erro,completude_%,tempo_processamento_s" > "$SCALE_SUMMARY"

# Benchmark principal: os 20 runs do n=4 também geram estes arquivos
SUMMARY_FILE="$OUTPUT_DIR/benchmark_summary.csv"
echo "run,timestamp_inicio,total_submetido,total_finished,total_erro,completude_%,tempo_processamento_s" > "$SUMMARY_FILE"

# Serviços já estão parados (foram parados acima junto com o middleware para o reset)
echo ""
echo "  [scale] Containers de serviço já parados (parados na fase de reset)."

for n_svcs in 1 2 3 4; do
    NEW_CONTAINER="${SCALE_CONTAINERS[$((n_svcs-1))]}"
    NEW_PORT="${SCALE_PORTS[$((n_svcs-1))]}"
    NEW_NAME="${SCALE_SVC_NAMES[$((n_svcs-1))]}"
    NEW_DESC="${SCALE_DESCS[$((n_svcs-1))]}"
    NEW_KAFKA_PREFIX="${SCALE_KAFKA_GROUPS[$((n_svcs-1))]}"

    echo ""
    echo "  [scale] Subindo: ${NEW_CONTAINER}..."
    # Zera o lag do novo serviço ANTES de iniciá-lo.
    # Container está parado → reset aceito pelo Kafka.
    # Sem isso, o serviço processa mensagens acumuladas de runs anteriores
    # (n_svcs < atual) antes de chegar nas do run atual.
    docker compose exec -T kafka kafka-consumer-groups.sh \
        --bootstrap-server localhost:9092 \
        --group "${NEW_KAFKA_PREFIX}-validate-group" \
        --topic "privacy-validate-topic" \
        --reset-offsets --to-latest --execute 2>/dev/null || true
    docker compose exec -T kafka kafka-consumer-groups.sh \
        --bootstrap-server localhost:9092 \
        --group "${NEW_KAFKA_PREFIX}-execute-group" \
        --topic "privacy-execute-topic" \
        --reset-offsets --to-latest --execute 2>/dev/null || true
    docker compose start "$NEW_CONTAINER"
    wait_container_healthy "$NEW_PORT" "$NEW_CONTAINER"

    # Registra apenas o novo serviço (os anteriores já estão registrados)
    register_one_service "$NEW_NAME" "$NEW_DESC"

    # Aguarda consumer groups Kafka do novo serviço
    wait_kafka_consumers_ready "$NEW_KAFKA_PREFIX"

    # Lista acumulada de serviços e containers ativos
    ACTIVE_SVCS=""
    ACTIVE_CONTAINERS="middleware"
    for i in $(seq 0 $((n_svcs-1))); do
        ACTIVE_SVCS="${ACTIVE_SVCS}${SCALE_SVC_NAMES[$i]},"
        ACTIVE_CONTAINERS="$ACTIVE_CONTAINERS ${SCALE_CONTAINERS[$i]}"
    done
    ACTIVE_SVCS="${ACTIVE_SVCS%,}"

    echo ""
    echo "  [scale] Configuração: ${n_svcs} serviço(s) → [${ACTIVE_SVCS}]"

    for scale_run in $(seq 1 $SCALE_RUNS); do
        TIMESTAMP_RUN=$(date "+%Y%m%d_%H%M%S")
        STATS_CSV="$SCALE_DIR/run_${n_svcs}svcs_${scale_run}_${TIMESTAMP_RUN}.csv"

        echo ""
        echo "  ── ${n_svcs} svc(s) | run ${scale_run}/${SCALE_RUNS}  —  $(date '+%H:%M:%S')"

        start_stats_collection "$STATS_CSV"
        set_phase "repouso"
        sleep "$REPOUSO_DURATION"

        set_phase "pico"
        $PYTHON tools/bulk_insert_and_delete.py --insert-only
        $PYTHON tools/gen_accounts_csv.py
        TS_INICIO_DB=$(date -u "+%Y-%m-%d %H:%M:%S")
        JMETER_JTL="${STATS_CSV%.csv}.jtl"
        JMETER_LOG="/tmp/jmeter_$(date +%s).log"
        jmeter -n \
            -t "$(pwd)/jmeter/benchmark_load.jmx" \
            -JACCOUNTS_CSV="$(pwd)/tools/accounts_for_jmeter.csv" \
            -JNUM_THREADS=900 \
            -JRAMP_UP=15 \
            -JRESULTS_JTL="$JMETER_JTL" \
            -j "$JMETER_LOG" > /dev/null
        grep -E "summary|WARN|ERR" "$JMETER_LOG" | tail -3 || true

        set_phase "pos"
        wait_finished "$TS_INICIO_DB"
        stop_stats_collection

        # Completude via DB
        SCALE_STATS=$(docker compose exec -T middleware_db psql -U user -d middlewaredb -t -A -c \
"SELECT COUNT(*) FILTER (WHERE status='FINISHED'), COUNT(*) FILTER (WHERE status='FAILED'), COUNT(*) FROM privacy_requests WHERE created_at >= '${TS_INICIO_DB}';" \
            2>/dev/null | tr -d ' ') || SCALE_STATS=""
        [ -z "$SCALE_STATS" ] && SCALE_STATS="0|0|0"
        FINISHED_N=$(echo "$SCALE_STATS" | cut -d'|' -f1); FINISHED_N=${FINISHED_N:-0}
        ERRORS_N=$(echo  "$SCALE_STATS"  | cut -d'|' -f2); ERRORS_N=${ERRORS_N:-0}
        TOTAL_N=$(echo   "$SCALE_STATS"  | cut -d'|' -f3); TOTAL_N=${TOTAL_N:-0}
        COMP_N=$(python3 -c "t=int('${TOTAL_N}' or 0); f=int('${FINISHED_N}' or 0); print(round(f/t*100,2) if t>0 else 0.0)")
        TS_FIM=$(date -u "+%Y-%m-%d %H:%M:%S")
        TEMPO_S=$(python3 -c "
from datetime import datetime
print(int((datetime.strptime('$TS_FIM','%Y-%m-%d %H:%M:%S')-datetime.strptime('$TS_INICIO_DB','%Y-%m-%d %H:%M:%S')).total_seconds()))")

        echo "${n_svcs},\"${ACTIVE_SVCS}\",${scale_run},${TS_INICIO_DB},${TOTAL_N},${FINISHED_N},${ERRORS_N},${COMP_N},${TEMPO_S}" >> "$SCALE_SUMMARY"
        echo "  [scale] ${n_svcs} svc(s) run ${scale_run}: ${FINISHED_N}/${TOTAL_N} FINISHED (${COMP_N}%) em ${TEMPO_S}s"

        # n=4 também gera os artefatos do benchmark principal
        if [ "$n_svcs" -eq 4 ]; then
            BENCH_STATS_CSV="$OUTPUT_DIR/benchmark_run_${scale_run}_${TIMESTAMP_RUN}.csv"
            COMPLETUDE_JSON="$OUTPUT_DIR/completude_run_${scale_run}_${TIMESTAMP_RUN}.json"
            cp "$STATS_CSV" "$BENCH_STATS_CSV"
            check_completude "$scale_run" "tools/account_ids.json" "$COMPLETUDE_JSON" "$TS_INICIO_DB" "$SUMMARY_FILE"
            sed -i '' "\$s/,\$/,${TEMPO_S}/" "$SUMMARY_FILE"
            cp tools/account_ids.json "${OUTPUT_DIR}/account_ids_run_${scale_run}_${TIMESTAMP_RUN}.json"
            echo "  [bench] → benchmark_run_${scale_run}_${TIMESTAMP_RUN}.csv + completude + account_ids"
        fi

        # Cleanup entre runs: reinicia containers ativos (sem tocar no banco)
        if [ "$scale_run" -lt "$SCALE_RUNS" ]; then
            cleanup_containers $ACTIVE_CONTAINERS
            # Após restart, aguarda consumers Kafka de cada serviço ativo
            # (o --describe retorna CONSUMER-ID="-" quando o grupo existe mas não
            # tem membro ativo; a função wait_kafka_consumers_ready com awk detecta isso)
            for i in $(seq 0 $((n_svcs-1))); do
                wait_kafka_consumers_ready "${SCALE_KAFKA_GROUPS[$i]}"
            done
        fi
    done
done

echo ""
echo "  [scale] Experimento de escalabilidade concluído."
echo "  Resultados em: $SCALE_DIR/"
cat "$SCALE_SUMMARY"

# ===========================================================================
# ANÁLISE ESTATÍSTICA
# ===========================================================================
echo ""
echo "  [análise] Calculando estatísticas agregadas..."
$PYTHON tools/analyze_results.py --output-dir "$OUTPUT_DIR"

# ===========================================================================
# EXPORT DO BANCO DE DADOS
# ===========================================================================
DB_EXPORT_DIR="$OUTPUT_DIR/db_export"
mkdir -p "$DB_EXPORT_DIR"

echo ""
echo "  [export] Exportando banco de dados para CSV..."

docker compose exec -T middleware_db psql -U user -d middlewaredb -c \
    "\COPY privacy_requests TO STDOUT WITH CSV HEADER" \
    > "$DB_EXPORT_DIR/privacy_requests.csv"
echo "  [export] privacy_requests.csv"

docker compose exec -T middleware_db psql -U user -d middlewaredb -c \
    "\COPY privacy_requests_services TO STDOUT WITH CSV HEADER" \
    > "$DB_EXPORT_DIR/privacy_requests_services.csv"
echo "  [export] privacy_requests_services.csv"

docker compose exec -T middleware_db psql -U user -d middlewaredb -c \
    "\COPY services TO STDOUT WITH CSV HEADER" \
    > "$DB_EXPORT_DIR/services.csv"
echo "  [export] services.csv"

echo "  [export] Gerando dump SQL completo..."
docker compose exec -T middleware_db pg_dump -U user -d middlewaredb \
    > "$DB_EXPORT_DIR/middlewaredb_dump.sql"
echo "  [export] middlewaredb_dump.sql"

echo ""
echo "========================================================"
echo " BENCHMARK COMPLETO"
echo " Escalabilidade: $SCALE_DIR/scalability_summary.csv"
echo " Benchmark:      $SUMMARY_FILE"
echo " Análise:        $OUTPUT_DIR/benchmark_analysis.json"
echo " DB export:      $DB_EXPORT_DIR/"
echo "   ├── privacy_requests.csv"
echo "   ├── privacy_requests_services.csv"
echo "   ├── services.csv"
echo "   └── middlewaredb_dump.sql"
echo "========================================================"
