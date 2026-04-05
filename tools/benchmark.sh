#!/bin/bash

# =============================================================================
# benchmark.sh — Coleta de recursos + insert/delete (3 execuções)
#
# Fases por execução:
#   1. Repouso  : REPOUSO_DURATION segundos antes do disparo
#   2. Pico     : disparo do insert+delete (900 contas), coleta contínua
#   3. Pós      : POS_DURATION segundos após término do script Python
#
# Saída:
#   output-pdf/benchmark_run_<N>_<timestamp>.csv  — stats de recursos
#   output-pdf/completude_run_<N>_<timestamp>.json — resultado de completude
#   output-pdf/benchmark_summary.csv              — resumo das 3 execuções
# =============================================================================

set -eo pipefail

REPOUSO_DURATION=60     # segundos de repouso antes do disparo
POS_DURATION=120        # segundos de coleta após término do processamento
TOTAL_RUNS=3
OUTPUT_DIR="output-pdf"
MIDDLEWARE_DB_HOST="localhost"
MIDDLEWARE_DB_PORT="5437"
MIDDLEWARE_DB_USER="user"
MIDDLEWARE_DB_NAME="middlewaredb"
MIDDLEWARE_DB_PASS="password"

# Portas dos bancos dos microsserviços (bash 3 compatible)
ACCOUNTS_PORT=5436
PAYMENTS_PORT=5435
CRM_PORT=5433
DELIVERY_PORT=5434

mkdir -p "$OUTPUT_DIR"

SUMMARY_FILE="$OUTPUT_DIR/benchmark_summary.csv"
echo "run,timestamp_inicio,total_submetido,total_finished,total_erro,completude_%,tempo_processamento_s" > "$SUMMARY_FILE"

# ---------------------------------------------------------------------------
# Função: garante que os 4 serviços estão cadastrados no middleware
# ---------------------------------------------------------------------------
seed_services() {
    echo ""
    echo "  [seed] Verificando serviços cadastrados no middleware..."

    # Busca nomes já cadastrados
    EXISTING=$(curl -s http://localhost:8000/api/v1/services/ | python3 -c \
        "import sys,json; print('\n'.join(s['service_name'] for s in json.load(sys.stdin)))" 2>/dev/null || echo "")

    NAMES=("account" "payment" "crm" "delivery")
    DESCS=(
        "Autentica e autoriza o acesso de usuários a recursos e funcionalidades do sistema. Gerencia informações de perfil de usuários, credenciais de acesso e controla permissões e papéis dentro da plataforma."
        "Gerencia o fluxo de valor monetário entre entidades. Implementa protocolos de comunicação seguros para autorização, captura e reembolso de transações financeiras. Mantém registros de transações e integra-se com gateways de pagamento."
        "Centraliza e organiza dados relacionados a interações com clientes. Permite o registro e acompanhamento de leads, oportunidades de venda, histórico de comunicação e atividades de marketing e suporte."
        "Coordena a movimentação física de bens do ponto de origem ao destino. Envolve o gerenciamento de rotas, agendamento de coletas e entregas e rastreamento em tempo real da localização dos itens."
    )
    for i in 0 1 2 3; do
        NAME="${NAMES[$i]}"
        DESC="${DESCS[$i]}"
        if echo "$EXISTING" | grep -qx "$NAME"; then
            echo "    [seed] Serviço '${NAME}' já existe — ignorando"
        else
            HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
                -X POST http://localhost:8000/api/v1/services/ \
                -H "Content-Type: application/json" \
                -d "{\"service_name\": \"${NAME}\", \"description\": \"${DESC}\"}")
            echo "    [seed] Serviço '${NAME}' cadastrado (HTTP ${HTTP_STATUS})"
        fi
    done
    echo "  [seed] Serviços verificados."
}

seed_services

# ---------------------------------------------------------------------------
# Função: coleta docker stats em background para um arquivo CSV
# Uso: start_stats_collection <output_csv>
# Retorna o PID na variável STATS_PID
# ---------------------------------------------------------------------------
PHASE_FILE="/tmp/benchmark_phase_$$"

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
}

set_phase() {
    echo "$1" > "$PHASE_FILE"
}

stop_stats_collection() {
    kill "$STATS_PID" 2>/dev/null || true
    wait "$STATS_PID" 2>/dev/null || true
    rm -f "$PHASE_FILE"
}

stop_stats_collection() {
    kill "$STATS_PID" 2>/dev/null || true
    wait "$STATS_PID" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# Função: calcula completude após processamento (usa docker compose exec)
# ---------------------------------------------------------------------------
check_completude() {
    local run=$1
    local account_ids_file=$2
    local output_json=$3
    local ts_inicio=$4
    local summary_file=$5

    python3 tools/check_completude.py \
        --run "$run" \
        --account-ids "$account_ids_file" \
        --output "$output_json" \
        --ts-inicio "$ts_inicio" \
        --summary "$summary_file"
}

# ---------------------------------------------------------------------------
# Loop principal: 3 execuções
# ---------------------------------------------------------------------------
for run in $(seq 1 $TOTAL_RUNS); do
    TIMESTAMP_RUN=$(date "+%Y%m%d_%H%M%S")
    STATS_CSV="$OUTPUT_DIR/benchmark_run_${run}_${TIMESTAMP_RUN}.csv"
    COMPLETUDE_JSON="$OUTPUT_DIR/completude_run_${run}_${TIMESTAMP_RUN}.json"

    echo ""
    echo "========================================================"
    echo " EXECUÇÃO $run / $TOTAL_RUNS  —  $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================================"

    # --- Fase repouso ---
    echo ""
    echo "  [repouso] Coletando ${REPOUSO_DURATION}s em repouso..."
    start_stats_collection "$STATS_CSV"
    set_phase "repouso"
    sleep "$REPOUSO_DURATION"

    # --- Fase pico: disparo do script Python ---
    echo ""
    echo "  [pico] Iniciando insert+delete (900 contas)..."
    set_phase "pico"
    TS_INICIO_DB=$(date "+%Y-%m-%d %H:%M:%S")
    python tools/bulk_insert_and_delete.py
    echo "  [pico] Script Python concluído."

    # --- Fase pós-processamento ---
    echo ""
    echo "  [pos] Coletando ${POS_DURATION}s pós-disparo..."
    set_phase "pos"
    sleep "$POS_DURATION"

    stop_stats_collection
    echo "  [stats] Coleta de recursos finalizada → $STATS_CSV"

    # --- Completude ---
    echo ""
    echo "  [completude] Calculando completude..."
    check_completude "$run" "tools/account_ids.json" "$COMPLETUDE_JSON" "$TS_INICIO_DB" "$SUMMARY_FILE"

    # Calcula tempo de processamento (tempo entre disparo e todos FINISHED)
    TS_FIM=$(date "+%Y-%m-%d %H:%M:%S")
    TEMPO_S=$(python3 -c "
from datetime import datetime
t1 = datetime.strptime('$TS_INICIO_DB', '%Y-%m-%d %H:%M:%S')
t2 = datetime.strptime('$TS_FIM', '%Y-%m-%d %H:%M:%S')
print(int((t2-t1).total_seconds()))
")
    # Atualiza tempo na última linha do summary
    sed -i '' "\$s/,\$/${TEMPO_S}/" "$SUMMARY_FILE"

    echo ""
    echo "  Execução $run concluída. Stats: $STATS_CSV | Completude: $COMPLETUDE_JSON"

    # Intervalo entre execuções (exceto após a última)
    if [ "$run" -lt "$TOTAL_RUNS" ]; then
        echo ""
        echo "  Aguardando 60s antes da próxima execução..."
        sleep 60
    fi
done

echo ""
echo "========================================================"
echo " BENCHMARK CONCLUÍDO — resumo: $SUMMARY_FILE"
echo "========================================================"
cat "$SUMMARY_FILE"
