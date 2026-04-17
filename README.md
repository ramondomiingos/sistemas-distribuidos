# Adaptação à LGPD: Middleware para Implementação do Direito ao Esquecimento em Sistemas Distribuídos

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Kafka](https://img.shields.io/badge/Apache%20Kafka-3.5-red.svg)](https://kafka.apache.org/)
[![Docker](https://img.shields.io/badge/Docker-24+-blue.svg)](https://www.docker.com/)

> **Dissertação de Mestrado**: Proposta de middleware automatizado para orquestração do direito ao esquecimento (LGPD Art. 18, VI) em arquiteturas de microsserviços distribuídos, utilizando o padrão Two-Phase Commit adaptado para comunicação assíncrona via Apache Kafka.

**Autor**: Ramon Domingos

**Programa**: Mestrado em Tecnologia da Informação

**Instituição**: Universidade Federal do Rio Grande do Norte (UFRN)

**Orientador**: Eiji Adachi

**Ano**: 2026

---

## Resumo

Este artefato acompanha o artigo **"Adaptação à LGPD: Middleware para Implementação do Direito ao Esquecimento em Sistemas Distribuídos"**. O artigo propõe e avalia um middleware que orquestra o direito ao esquecimento (Art. 18, VI da LGPD) em arquiteturas de microsserviços, utilizando uma adaptação do protocolo Two-Phase Commit (2PC) para comunicação assíncrona via Apache Kafka. O artefato inclui o código-fonte completo do middleware, quatro microsserviços de exemplo, uma biblioteca de integração reutilizável (`pacote_privacy`), scripts de benchmark automatizados e os resultados brutos dos experimentos que embasam as afirmações do artigo.

---

## Estrutura do README

Este README está organizado da seguinte forma:

- **[Selos Considerados](#selos-considerados)** — selos de avaliação do artefato
- **[Informações Básicas](#informações-básicas)** — requisitos de hardware e software
- **[Dependências](#dependências)** — versões de todas as dependências
- **[Preocupações com Segurança](#preocupações-com-segurança)** — riscos e recomendações
- **[Instalação](#-instalação-e-execução)** — clone, build e inicialização
- **[Teste Mínimo](#teste-mínimo)** — verificação rápida da instalação
- **[Metodologia do Benchmark](#metodologia-do-benchmark)** — design experimental, protocolo de testes e coleta de métricas
- **[Experimentos](#experimentos)** — reprodução dos resultados do artigo
- **[Visão Geral do Projeto](#-visão-geral)** — contexto acadêmico e arquitetura
- **[Documentação Complementar](#-documentação)** — documentação acadêmica detalhada

---

## Selos Considerados

Os selos considerados são: **Disponíveis**, **Funcionais**, **Sustentáveis** e **Experimentos Reprodutíveis**.

- **Disponível (SeloD)**: o artefato está publicamente acessível no GitHub com licença MIT, incluindo código-fonte completo, scripts de experimento e resultados brutos dos benchmarks na pasta `output-benchmark/`.
- **Funcional (SeloF)**: o artefato pode ser executado em ambiente local via Docker Compose, reproduzindo o comportamento descrito no artigo — incluindo o protocolo 2PC completo e a coleta de métricas de recursos. O README apresenta lista de dependências com versões, descrição do ambiente, instruções de instalação e um exemplo de execução mínima.
- **Sustentável (SeloS)**: o código está modularizado em componentes bem definidos (middleware, microsserviços, biblioteca `pacote_privacy`), acompanhado de documentação acadêmica detalhada (`DOCUMENTACAO_ACADEMICA*.md`), manual de integração (`MANUAL_INTEGRACAO_NOVOS_SERVICOS.md`) e seção de experimentos com reivindicações identificadas explicitamente no README.
- **Reprodutível (SeloR)**: as principais reivindicações do artigo (completude do protocolo 2PC e eficiência de recursos) podem ser reproduzidas por meio de scripts automatizados (`tools/benchmark.sh`, `tools/bulk_insert_and_delete.py`, `tools/check_completude.py`, `tools/analyze_results.py`) que replicam integralmente a metodologia experimental descrita no artigo, incluindo 80 execuções de escalabilidade (1→4 serviços, 20 runs cada) — das quais os 20 runs com n=4 servem também como benchmark principal — com coleta de métricas em série temporal rotulada por fase (repouso/pico/pós), reinício dos containers de aplicação entre runs para garantir isolamento de estado, e análise estatística completa (média, mediana, percentis p90/p95/p99, IQR e intervalo de confiança 95% via bootstrap).

---

## Informações Básicas

### Ambiente de Execução

| Recurso | Mínimo Recomendado |
|---------|-------------------|
| **CPU** | 4 núcleos (8 recomendado) |
| **RAM** | 8 GB disponível |
| **Disco** | 5 GB livres |
| **SO** | Linux ou macOS (testado em macOS 14+, Ubuntu 22.04) |

### Software Necessário

| Software | Versão Mínima | Observação |
|----------|--------------|------------|
| Docker Engine | 24.x | |
| Docker Compose | 2.x (plugin) | `docker compose version` |
| Python | 3.9+ | Scripts de inserção e análise |
| Apache JMeter | 5.6+ | Geração de carga concorrente |
| Git | qualquer | |
| Bash | 3.2+ | Compatível com macOS bash padrão |

### Portas Utilizadas

As seguintes portas devem estar livres no host: `3000, 5432–5436, 8000–8004, 8010–8014, 8080, 9090, 9092, 2181`.

---

## Dependências

### Dependências dos Serviços (gerenciadas pelo Docker)

Todas as dependências de runtime são instaladas automaticamente via `docker compose up --build`. As versões principais são:

| Dependência | Versão | Uso |
|-------------|--------|-----|
| Python | 3.9 | Runtime de todos os serviços |
| FastAPI | 0.100+ | Framework HTTP do middleware e microsserviços |
| aiokafka | 0.8+ | Cliente Kafka assíncrono |
| SQLAlchemy | 2.0+ | ORM PostgreSQL |
| Apache Kafka | 3.5 | Message broker |
| PostgreSQL | 13 | Banco de dados (5 instâncias independentes) |
| OpenTelemetry | 1.x | Observabilidade distribuída |
| Prometheus | 2.x | Coleta de métricas |
| Grafana LGTM | 10.x | Visualização |

### Dependências dos Scripts de Benchmark (host)

**Python:**
```bash
pip install -r tools/requirements.txt
```

| Pacote | Uso |
|--------|-----|
| psycopg2-binary | Inserção direta nos bancos dos microsserviços via psycopg2 |
| faker | Geração de dados sintéticos (nomes, e-mails, endereços) |
| requests | Submissão individual de requisições HTTP (testes avulsos) |
| numpy / pandas | Manipulação de dados na geração do notebook e análise estatística |
| matplotlib / seaborn | Geração dos gráficos e heatmaps do notebook (`create_notebook.py`) |
| scipy | Regressão linear para detecção de degradação de CPU entre runs (`linregress`) |

**Apache JMeter** (geração de carga concorrente no benchmark):
```bash
# macOS
brew install jmeter

# Linux — baixe em https://jmeter.apache.org/download_jmeter.cgi
# e adicione o binário ao PATH
```

O JMeter é responsável por disparar as 900 requisições de exclusão de forma concorrente no benchmark. Ele lê os `account_ids` reais pré-inseridos de um CSV (`tools/accounts_for_jmeter.csv`) e submete um `POST /api/v1/privacy-requests/` por thread, com ramp-up configurável. O plano de teste está em `jmeter/benchmark_load.jmx`.

### Acesso a Recursos de Terceiros

Nenhum. O artefato é completamente auto-contido — todos os serviços (Kafka, PostgreSQL, Grafana, Prometheus) sobem via Docker Compose sem dependência de nuvem ou serviços externos.

---

## Preocupações com Segurança

O artefato **não apresenta riscos de segurança** para os avaliadores. Todas as credenciais configuradas (usuário/senha de banco de dados, etc.) são padrões de desenvolvimento local (`user`/`password`) e os serviços ficam expostos apenas em `localhost`. Não há conexão com serviços externos nem armazenamento de dados reais.

**Recomendação**: execute o artefato em uma máquina de desenvolvimento ou VM isolada, não em ambiente de produção.

---

## 📋 Índice

- [Visão Geral](#-visão-geral)
- [Problema de Pesquisa](#-problema-de-pesquisa)
- [Arquitetura](#-arquitetura)
- [Tecnologias](#-tecnologias)
- [Instalação e Execução](#-instalação-e-execução)
- [Documentação](#-documentação)
- [Manual de Integração](#-manual-de-integração)
- [Casos de Uso](#-casos-de-uso)
- [Resultados](#-resultados)

---

## 🎯 Visão Geral

Este projeto apresenta uma **solução de middleware automatizada** para implementação do **direito ao esquecimento** em sistemas distribuídos baseados em microsserviços, garantindo conformidade com a **Lei Geral de Proteção de Dados Pessoais (LGPD - Lei nº 13.709/2018)**.

### Características Principais

- ✅ **Orquestração Distribuída**: Protocolo Two-Phase Commit (2PC) adaptado para eventos
- ✅ **Biblioteca Reutilizável**: `pacote_privacy` para fácil integração
- ✅ **Consistência Transacional**: Garantia de decisões unânimes (commit/abort)
- ✅ **Auditabilidade Completa**: OpenTelemetry + logs estruturados
- ✅ **Escalabilidade Horizontal**: Suporte a réplicas e particionamento
- ✅ **Baixo Acoplamento**: Comunicação assíncrona via Apache Kafka

### Diferencial Acadêmico

Este trabalho contribui com:

1. **Protocolo 2PC Assíncrono**: Adaptação do Two-Phase Commit clássico para ambientes event-driven
2. **Framework de Validação**: Mecanismo que permite a cada microsserviço aplicar suas próprias regras de negócio
3. **Arquitetura de Referência**: Modelo replicável para conformidade LGPD em microsserviços
4. **Análise de Performance**: Métricas de latência, throughput e consistência

---

## 🔍 Problema de Pesquisa

### Contexto

A LGPD estabelece o **direito ao esquecimento** (Art. 18, VI), garantindo ao titular dos dados a prerrogativa de solicitar a eliminação de suas informações pessoais. Em arquiteturas monolíticas, esta implementação é direta. Porém, em **microsserviços distribuídos**:

- **Fragmentação de Dados**: Informações do titular distribuídas em múltiplos serviços independentes
- **Autonomia de Serviços**: Cada microsserviço possui regras de negócio específicas
- **Consistência**: Necessidade de garantir exclusão atômica em todos os serviços
- **Auditabilidade**: Rastreamento completo para compliance regulatório

### Questão de Pesquisa

> **"Como implementar o direito ao esquecimento de forma consistente, escalável e auditável em arquiteturas de microsserviços distribuídos, garantindo conformidade com a LGPD?"**

### Hipótese

Um middleware centralizador, utilizando padrão Two-Phase Commit adaptado para comunicação assíncrona via message broker, pode orquestrar o processo de exclusão distribuída, garantindo consistência transacional e auditabilidade completa.

---

## 🏗 Arquitetura

### Visão Geral do Sistema

```
┌─────────────────────────────────────────────────────────┐
│                   CLIENTE / API                         │
└────────────────────┬────────────────────────────────────┘
                     │ POST /api/v1/privacy-requests/
                     ▼
┌─────────────────────────────────────────────────────────┐
│              MIDDLEWARE (Orquestrador)                  │
│  • Recebe requisições de privacidade                    │
│  • Orquestra 2PC via Kafka                              │
│  • Consolida respostas e decide commit/abort            │
└────────────┬────────────────────┬───────────────────────┘
             │                    │
    Fase 1   │                    │  Fase 2
  (Validate) │                    │  (Execute)
             ▼                    ▼
┌─────────────────────────────────────────────────────────┐
│                   APACHE KAFKA                          │
│  Topics:                                                │
│  • privacy-validate-topic                               │
│  • privacy-validate-response-topic                      │
│  • privacy-execute-topic                                │
│  • privacy-execute-response-topic                       │
└────┬─────────┬─────────┬─────────┬──────────────────────┘
     │         │         │         │
     ▼         ▼         ▼         ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ ACCOUNTS │ │ PAYMENTS │ │   CRM    │ │ DELIVERY │
│          │ │          │ │          │ │          │
│ validate │ │ validate │ │ validate │ │ validate │
│ execute  │ │ execute  │ │ execute  │ │ execute  │
│          │ │          │ │          │ │          │
│ [DB]     │ │ [DB]     │ │ [DB]     │ │ [DB]     │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
```

### Padrões Arquiteturais Aplicados

| Padrão | Aplicação |
|--------|-----------|
| **Database per Service** | Cada microsserviço possui seu banco de dados independente |
| **Event-Driven Architecture** | Comunicação assíncrona via eventos Kafka |
| **Saga Pattern (Orquestração)** | Middleware coordena transação distribuída |
| **Two-Phase Commit (Adaptado)** | Fase 1: Validação, Fase 2: Execução |
| **CQRS** | Separação entre comandos (delete) e consultas (read) |

---

## 🛠 Tecnologias

### Core Stack

| Componente | Tecnologia | Versão | Justificativa |
|------------|-----------|--------|---------------|
| **Backend** | Python + FastAPI | 3.9 / 0.100+ | Performance, async/await, tipagem estática |
| **Mensageria** | Apache Kafka | 3.5 | Persistência, escalabilidade, auditoria |
| **Banco de Dados** | PostgreSQL | 13 | ACID, confiabilidade, suporte JSON |
| **ORM** | SQLAlchemy | 2.0+ | Maturidade, async support |
| **Cliente Kafka** | aiokafka | 0.8+ | Integração assíncrona com Python |
| **Observabilidade** | OpenTelemetry | 1.x | Padrão vendor-neutral, tracing distribuído |
| **Métricas** | Prometheus | 2.x | Time-series database, alerting |
| **Visualização** | Grafana LGTM | 10.x | Logs, métricas, traces unificados |
| **Containerização** | Docker + Compose | 24.x | Portabilidade, reprodutibilidade |

### Componentes do Sistema

```
├── Middleware (Port 8000)         - Orquestrador 2PC
├── Accounts (Port 8002)           - Gestão de usuários
├── Payments (Port 8001)           - Transações financeiras
├── CRM (Port 8003)                - Dados sensíveis (LGPD Art. 5, II)
├── Delivery (Port 8004)           - Logística e entregas
├── Kafka (Port 9092)              - Message broker
├── Zookeeper (Port 2181)          - Coordenação Kafka
├── PostgreSQL (Ports 5432-5437)   - 5 bancos independentes
├── Grafana (Port 3000)            - Observabilidade
└── Prometheus (Port 9090)         - Métricas
```

---

## 🚀 Instalação e Execução

### Pré-requisitos

- Docker 24.x ou superior
- Docker Compose 2.x ou superior
- 8 GB RAM disponível
- Portas 3000, 5432–5436, 8000–8004, 8010–8014, 8080, 9090, 9092, 2181 disponíveis
- Apache JMeter 5.6+ (`brew install jmeter` no macOS) — necessário apenas para o benchmark

### Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/ramondomiingos/sistemas-distribuidos.git
cd sistemas-distribuidos

# 2. Construa e inicie os containers
docker compose up --build

# 3. Aguarde inicialização (cerca de 60 segundos)
# Verifique logs:
docker compose logs -f middleware

# 4. (Opcional) Popule dados de teste
python tools/insert_values.py
```

### Verificação da Instalação

```bash
# 1. Verificar saúde dos serviços
curl http://localhost:8000/health      # Middleware
curl http://localhost:8002/health      # Accounts
curl http://localhost:8001/health      # Payments
curl http://localhost:8003/health      # CRM
curl http://localhost:8004/health      # Delivery

# 2. Verificar Kafka consumers (deve mostrar 8 grupos)
docker compose exec kafka kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 --list

# Esperado:
# accounts-validate-group
# accounts-execute-group
# payments-validate-group
# payments-execute-group
# crm-validate-group
# crm-execute-group
# delivery-validate-group
# delivery-execute-group

# 3. Acessar Grafana
open http://localhost:3000
# Login: admin / admin
```

---

## Teste Mínimo

Este teste verifica que o protocolo 2PC está operacional de ponta a ponta.

```bash
# 1. Inserir dados de um titular de teste
docker compose exec accounts_db psql -U user -d accounts_db -c \
  "INSERT INTO users (name, email, account_id) VALUES ('Teste', 'teste@exemplo.com', 'test-account-001');"

# 2. Submeter requisição de exclusão ao middleware
curl -s -X POST http://localhost:8000/api/v1/privacy-requests/ \
  -H "Content-Type: application/json" \
  -d '{"account_id": "test-account-001", "operation": "DELETE"}' | python3 -m json.tool

# Resposta esperada: {"id": "...", "status": "CREATED", ...}
# Anote o "id" retornado.

# 3. Aguardar processamento (5–15 segundos)
sleep 10

# 4. Verificar status final (substitua <ID> pelo id retornado)
curl -s http://localhost:8000/api/v1/privacy-requests/<ID> | python3 -m json.tool
# Status esperado: "FINISHED"

# 5. Confirmar que o registro foi removido
docker compose exec accounts_db psql -U user -d accounts_db -c \
  "SELECT COUNT(*) FROM users WHERE account_id = 'test-account-001';"
# Resultado esperado: 0
```

**Tempo esperado**: menos de 30 segundos após a inicialização completa dos serviços.

---

## Metodologia do Benchmark

Esta seção descreve o design experimental adotado para avaliação do middleware, incluindo protocolo de testes, geração de carga, coleta de métricas e critérios de independência entre execuções.

### Visão Geral

O benchmark é composto por um único experimento de escalabilidade executado pelo script `tools/benchmark.sh`. Os 20 runs da configuração com 4 serviços (n=4) servem simultaneamente como **benchmark principal**, eliminando redundância e contaminação de dados.

| Experimento | Configuração | Runs | Requisições/run | Total de requisições |
|---|---|---|---|---|
| Escalabilidade | 1, 2, 3 e 4 serviços | 20 por configuração (80 total) | 900 | 72.000 |
| ↳ *n=4 também é o benchmark principal* | 4 serviços (fixo) | 20 (inclusos acima) | 900 | — |

### Protocolo Avaliado

Cada requisição de exclusão percorre o protocolo 2PC assíncrono sobre Kafka:

1. **Fase de validação**: middleware publica em `privacy-validate-topic`; cada microsserviço responde em `privacy-validate-response-topic` com aprovação ou rejeição baseada em regras de negócio (ex.: Payments bloqueia se há pagamento pendente; Delivery bloqueia se há entrega em trânsito)
2. **Fase de execução**: se todos aprovaram, middleware publica em `privacy-execute-topic`; cada microsserviço apaga os dados e confirma em `privacy-execute-response-topic`

O status final de cada requisição é `FINISHED` (todos executaram com sucesso), `FAILED` (algum bloqueou ou erro ocorreu) ou `PARTIALLY_COMPLETED` (inconsistência entre serviços).

### Estrutura de Cada Run

Cada execução segue três fases instrumentadas:

| Fase | Duração | Descrição |
|---|---|---|
| `repouso` | 30 s | Sistema ocioso — coleta baseline de recursos sem carga |
| `pico` | variável (~17 s) | Inserção de 900 contas + submissão JMeter + processamento 2PC completo (validate e execute). A fase encerra somente após todas as requisições atingirem status terminal (`FINISHED`/`FAILED`), capturando o pico real de CPU gerado pelo processamento assíncrono das respostas Kafka |
| `pos` | 30 s | Cooldown após conclusão do 2PC — coleta baseline de recuperação de recursos |

### Geração de Carga

A fase `pico` de cada run é composta por três etapas em sequência:

**1. Inserção de dados** — `tools/bulk_insert_and_delete.py --insert-only`

Cria 900 contas com UUIDs gerados do zero via conexões psycopg2 diretas aos bancos dos microsserviços. Os IDs são persistidos em `tools/account_ids.json`. UUIDs frescos a cada run eliminam colisão entre execuções.

**2. Geração do CSV** — `tools/gen_accounts_csv.py`

Converte `account_ids.json` para `tools/accounts_for_jmeter.csv` (uma linha por `account_id`, com header). Este arquivo é a entrada do JMeter.

**3. Submissão concorrente** — Apache JMeter (`jmeter/benchmark_load.jmx`)

O JMeter dispara 900 threads com ramp-up de 15 segundos. Cada thread lê um `account_id` único do CSV via `CSVDataSet` (modo `shareMode.all` — fila compartilhada, sem repetição) e envia um `POST /api/v1/privacy-requests/`. As métricas de latência HTTP de submissão são salvas em arquivo `.jtl` por run.

```
tools/account_ids.json
       ↓ gen_accounts_csv.py
tools/accounts_for_jmeter.csv
       ↓ JMeter (900 threads, ramp-up 15s)
POST /api/v1/privacy-requests/  ×900 concorrentes
       ↓
Kafka → 2PC → FINISHED/FAILED
```

O JTL registra a **latência de submissão** (tempo de resposta do POST). A **latência de processamento 2PC** (do `CREATED` ao `FINISHED`) é medida separadamente via banco de dados (`created_at` → `updated_at`).

### Experimento 1 — Escalabilidade (1 → 4 Serviços)

Os serviços são adicionados **cumulativamente**: a configuração com N serviços mantém todos os N−1 anteriores ativos e registrados, acrescentando apenas o novo. Isso simula o crescimento incremental de um ambiente de produção e permite observar como o protocolo 2PC se comporta à medida que mais participantes entram no consenso.

Para cada configuração (1, 2, 3 e 4 serviços), são realizados 20 runs independentes, totalizando 80 runs nesta parte.

### Experimento 2 — Benchmark Principal (20 Runs, 4 Serviços)

Os 20 runs da última configuração de escalabilidade (n=4, todos os serviços ativos) são **também** os runs do benchmark principal. O script `benchmark.sh` coleta duplamente os artefatos para essa configuração: além do `scalability_summary.csv`, gera `benchmark_run_N_*.csv`, `completude_run_N_*.json`, `account_ids_run_N_*.json` e escreve no `benchmark_summary.csv`. Isso elimina a necessidade de uma fase separada, reduzindo o tempo total de ~4–6 h para **~1,5 h**.

### Independência entre Runs

A independência entre execuções é garantida por quatro mecanismos:

- **UUIDs únicos por run**: nenhuma conta criada em run N colide com as de run N+1
- **Reinício dos containers de aplicação** (`docker compose restart`) entre runs: zera estado em memória, reconecta consumers Kafka e reinicia connection pools
- **Bancos de dados e Kafka preservados**: os dados acumulam entre runs, permitindo análise histórica completa ao final
- **TRUNCATE nos bancos dos microsserviços** antes da primeira participação de cada serviço no experimento de escalabilidade: runs anteriores (n=1, 2, 3) inserem dados em *todos* os serviços via `bulk_insert_and_delete.py`, mas o 2PC apaga apenas os dados dos serviços participantes. Sem esse mecanismo, ao entrar em n=4 o banco do `delivery` acumula registros de runs anteriores (~54.000 linhas), provocando contenção com o autovacuum do PostgreSQL e degradação de latência com cauda longa de 8–10 s. O TRUNCATE garante que cada serviço estreia com tabela limpa e baseline uniforme.

O banco do middleware é limpo **uma única vez** no início do benchmark, antes de qualquer experimento.

### Coleta de Métricas

**Métricas de recursos** — amostradas a cada 1 segundo via `docker stats` para todos os containers, durante todas as fases:
- CPU %
- Memória (MB e %)
- Net IO acumulado (TX/RX em MB)
- Block IO acumulado (leitura/escrita em MB)

**Métricas de completude** — apuradas ao final de cada run via consulta direta ao banco do middleware, filtrando pelo timestamp UTC de início do run:
- Total de requisições submetidas
- Total com status `FINISHED`
- Total com status `FAILED`
- Percentual de completude
- Tempo total de processamento (segundos)

### Análise Estatística

Ao final do benchmark, `tools/analyze_results.py` computa:

- Média, desvio padrão, mediana, P25, P75, P90, P95, P99 e IQR
- Intervalos de confiança 95% via bootstrap não-paramétrico (2.000 reamostras, seed=42) — não assume normalidade da distribuição
- Coeficiente de Variação (CV = σ/μ × 100%) calculado sobre as **médias por run** de CPU e memória na fase `pico` — isola variabilidade inter-run (RNF07), excluindo métricas de Net I/O por serem contadores cumulativos com variância por artefato de amostragem
- Análise de escalabilidade: crescimento normalizado T(n)/T(1) e overhead relativo por configuração de serviços
- Correlação de Pearson entre CPU e latência (observacional)

### Export do Banco de Dados

Ao término, o banco completo é exportado para `output-benchmark/db_export/`:

| Arquivo | Conteúdo |
|---|---|
| `privacy_requests.csv` | Todas as requisições com status e timestamps |
| `privacy_requests_services.csv` | Detalhes de validação/execução por serviço |
| `services.csv` | Serviços registrados |
| `middlewaredb_dump.sql` | Dump SQL completo para restauração posterior |

---

## Experimentos

Esta seção descreve como reproduzir os resultados do artigo.

**Pré-requisitos**:

```bash
# Dependências Python
pip install -r tools/requirements.txt

# Apache JMeter (geração de carga concorrente)
brew install jmeter        # macOS
# Linux: https://jmeter.apache.org/download_jmeter.cgi
```

---

### Reivindicação 1 — Completude do Protocolo 2PC

**Afirmação**: o middleware garante a execução integral do direito ao esquecimento — todas as 900 requisições percorrem as duas fases do protocolo com sucesso, e os registros são removidos de todos os microsserviços participantes.

**Resultado esperado**: completude de 100% e 0 registros remanescentes em cada banco de dados.

```bash
# 1. Certifique-se de que todos os containers estão em execução
docker compose ps

# 2. Insira 900 contas e gere o CSV para o JMeter
python tools/bulk_insert_and_delete.py --insert-only
python tools/gen_accounts_csv.py

# 3. Marque o timestamp APÓS a inserção (mede apenas o tempo do protocolo 2PC)
TS_INICIO=$(date -u '+%Y-%m-%d %H:%M:%S')

# 4. Dispare 900 requisições concorrentes via JMeter
jmeter -n \
  -t jmeter/benchmark_load.jmx \
  -JACCOUNTS_CSV="$(pwd)/tools/accounts_for_jmeter.csv" \
  -JNUM_THREADS=900 -JRAMP_UP=15 \
  -JRESULTS_JTL=/tmp/teste_completude.jtl \
  -j /tmp/jmeter.log

# 5. Aguarde o processamento (até 2 minutos) e verifique
python3 tools/check_completude.py \
  --run 1 \
  --account-ids tools/account_ids.json \
  --output /tmp/completude_resultado.json \
  --ts-inicio "$TS_INICIO" \
  --summary /tmp/summary.csv

cat /tmp/completude_resultado.json
```

**Interpretação**:
- `completude_pct: 100.0` — todas as requisições concluíram o protocolo 2PC
- `registros_restantes_por_servico: {... 0 em todos}` — deleção completa em todos os microsserviços

---

### Reivindicação 2 — Comportamento sob Carga (Benchmark Completo)

**Afirmação**: o middleware apresenta consumo de CPU concentrado na fase de pico, com recuperação consistente na fase pós-carga, e consumo de memória estável ao longo das execuções.

**Tempo estimado**: o benchmark completo (80 runs de escalabilidade, dos quais os 20 do n=4 também são o benchmark principal) leva aproximadamente **~1,5 horas**.

```bash
# Executa o benchmark completo a partir da raiz do repositório
bash tools/benchmark.sh
```

**Saídas geradas em `output-benchmark/`**:

```
output-benchmark/
├── scalability/
│   ├── scalability_summary.csv           — resumo dos 80 runs de escalabilidade
│   ├── run_Nsvcs_R_<ts>.csv              — série temporal de recursos por run
│   └── run_Nsvcs_R_<ts>.jtl             — latências HTTP do JMeter por run
├── benchmark_run_N_<ts>.csv             — série temporal de recursos (runs 1–20)
├── benchmark_run_N_<ts>.jtl            — latências HTTP do JMeter (runs 1–20)
├── completude_run_N_<ts>.json           — completude por run (runs 1–20)
├── benchmark_summary.csv               — resumo tabular dos 20 runs principais
├── benchmark_analysis.json             — estatísticas agregadas completas
└── db_export/
    ├── privacy_requests.csv
    ├── privacy_requests_services.csv
    ├── services.csv
    └── middlewaredb_dump.sql
```

**Verificação rápida dos resultados**:

```bash
# Resumo de completude por run
cat output-benchmark/benchmark_summary.csv

# Estatísticas completas (média, mediana, percentis, IQR, IC 95% bootstrap)
cat output-benchmark/benchmark_analysis.json

# Médias de CPU do middleware por fase (run 1)
grep "middleware" output-benchmark/benchmark_run_1_*.csv | \
  awk -F',' '{gsub(/%/,"",$5); print $2, $5}' | \
  sort | awk '{sum[$1]+=$2; cnt[$1]++} END {for(p in sum) print p, sum[p]/cnt[p]}'
```

A coluna `Fase` nos CSVs assume os valores `repouso`, `pico` e `pos`, permitindo segmentação direta das métricas por momento do experimento. O arquivo `benchmark_analysis.json` reporta, por métrica: média ± desvio padrão, mediana (p50), IQR (p25–p75), p90, p95, p99 e intervalo de confiança 95% via bootstrap.

---

## 💡 Manual de Integração

Existe um [manual](./MANUAL_INTEGRACAO_NOVOS_SERVICOS.md), com checklist para integrar um novo serviço ao middleware. Usando esse passo a passo, você irá conseguir integrar esse middleware em seu ecossistema.

---

## 💡 Casos de Uso

### Caso 1: Exclusão Bem-Sucedida ✅

**Cenário**: Titular solicita exclusão, todos os serviços aprovam.

```bash
# 1. Criar requisição
POST /api/v1/privacy-requests/
{
  "account_id": "123456789",
  "operation": "DELETE"
}

# 2. Resultado
# Status: FINISHED
# Dados removidos de:
# - Accounts: 1 usuário
# - Payments: 3 pedidos
# - CRM: 1 registro sensível
# - Delivery: 2 entregas
```

### Caso 2: Rejeição por Regra de Negócio ❌

**Cenário**: Titular possui pagamento pendente.

```bash
# 1. Criar requisição
POST /api/v1/privacy-requests/
{
  "account_id": "987654321",
  "operation": "DELETE"
}

# 2. Resultado
# Status: FAILED
# Motivo: "Payments bloqueou: 1 pagamento com status 'pending'"
# Ação: Titular deve resolver pendências financeiras
```

### Caso 3: Falha Parcial ⚠️

**Cenário**: Validação aprovada, mas um serviço falha na execução.

```bash
# Status: PARTIALLY_COMPLETED
# Dados removidos de: Accounts, Payments, CRM
# Falha em: Delivery (erro de conexão)
# Ação: Retry manual ou automático
```

---

## 📚 Documentação

### Documentos Acadêmicos

1. **[DOCUMENTACAO_ACADEMICA.md](./DOCUMENTACAO_ACADEMICA.md)** (Parte 1)
   - Introdução e fundamentação teórica
   - Arquitetura do sistema
   - Especificação de componentes
   - Protocolo de comunicação

2. **[DOCUMENTACAO_ACADEMICA_PARTE2.md](./DOCUMENTACAO_ACADEMICA_PARTE2.md)**
   - Contratos de API detalhados (REST + Kafka)
   - Biblioteca de integração (`pacote_privacy`)
   - Implementação de handlers

3. **[DOCUMENTACAO_ACADEMICA_PARTE3.md](./DOCUMENTACAO_ACADEMICA_PARTE3.md)**
   - Fluxogramas completos
   - Diagramas de sequência
   - Arquitetura visual

4. **[DOCUMENTACAO_ACADEMICA_PARTE4.md](./DOCUMENTACAO_ACADEMICA_PARTE4.md)**
   - Implementação detalhada
   - Casos de uso
   - Avaliação e resultados
   - Trabalhos futuros

---

## 📊 Resultados

### Métricas de Performance

> Os valores abaixo serão atualizados após a execução do benchmark completo (`bash tools/benchmark.sh`).
> Os resultados definitivos ficam em `output-benchmark/benchmark_analysis.json` e `output-benchmark/estatisticas_consolidadas.csv`.

| Métrica | Fonte | Limiar (RNF) |
|---------|-------|--------------|
| **Completude (% FINISHED)** | `benchmark_summary.csv` | ≥ 99,5% (RNF01) |
| **Latência 2PC P95** | `db_export/privacy_requests.csv` | ≤ 10 s (RNF02) |
| **Latência HTTP P99** | `*.jtl` (JMeter) | ≤ 500 ms (RNF03) |
| **CPU middleware (pico, máx)** | `benchmark_run_N_*.csv` | ≤ 70% (RNF04) |
| **Crescimento T(4)/T(1)** | `scalability/scalability_summary.csv` | ≤ 2,0× (RNF05) |
| **CV CPU e Memória (média por run, fase pico)** | `benchmark_run_N_*.csv` | ≤ 15% (RNF07) |

### Garantias de Consistência

| Aspecto | Garantia | Mecanismo |
|---------|----------|-----------|
| **Atomicidade** | ✅ Parcial | 2PC garante decisão unânime |
| **Consistência** | ✅ Forte | Validação antes de execução |
| **Isolamento** | ⚠️ Eventual | Consumer groups Kafka |
| **Durabilidade** | ✅ Forte | PostgreSQL + log Kafka |

### Conformidade LGPD

| Requisito Legal | Status |
|-----------------|--------|
| Art. 18, VI - Direito ao Esquecimento | ✅ Conforme |
| Art. 37 - Relatório de Impacto |  |
| Art. 46 - Segurança |  |
| Art. 48 - Comunicação ao Titular | |

---

## 🤝 Contribuições

Este é um projeto de pesquisa acadêmica. Contribuições são bem-vindas através de:

1. **Issues**: Reporte bugs ou sugira melhorias
2. **Pull Requests**: Correções ou novas funcionalidades
3. **Discussões**: Ideias para trabalhos futuros

### Guia de Contribuição

```bash
# 1. Fork o projeto
# 2. Crie uma branch
git checkout -b feature/minha-contribuicao

# 3. Commit suas mudanças
git commit -m "feat: adiciona funcionalidade X"

# 4. Push para o branch
git push origin feature/minha-contribuicao

# 5. Abra um Pull Request
```

---

## 📞 Contato

**Ramon Domingos**
📧 Email: ramon.domingos.098@ufrn.edu.br
🔗 LinkedIn: [linkedin.com/in/ramondomiingos](https://linkedin.com/in/ramondomiingos)
🐙 GitHub: [@ramondomiingos](https://github.com/ramondomiingos)

**Orientador**: Eiji Adachi
**Instituição**: Universidade Federal do Rio Grande do Norte
**Programa**: Mestrado Profissional em Tecnologia da Informação
**Linha de Pesquisa**: Engenharia de Software

---

## 🙏 Agradecimentos

- **Eiji Adachi** - Orientação e suporte acadêmico
- **UFRN** - Infraestrutura e recursos
- **Comunidade Open Source** - FastAPI, Kafka, PostgreSQL, OpenTelemetry

---

## 📚 Citação

Se você utilizar este trabalho em sua pesquisa, por favor cite:

```bibtex
@mastersthesis{domingos2026lgpd,
  author  = {Ramon Domingos},
  title   = {Adaptação à LGPD: Proposta de Middleware para a Implementação
             do Direito ao Esquecimento em Sistemas Distribuídos},
  school  = {Universidade Federal do Rio Grande do Norte},
  year    = {2026},
  type    = {Dissertação de Mestrado},
  address = {Natal, RN},
  month   = {Fevereiro}
}
```

---

## LICENSE

Este projeto está licenciado sob a licença **MIT**.

```
MIT License

Copyright (c) 2026 Ramon Domingos

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<div align="center">

**⭐ Se este projeto foi útil para sua pesquisa, considere dar uma estrela!**

[![Star on GitHub](https://img.shields.io/github/stars/ramondomiingos/sistemas-distribuidos?style=social)](https://github.com/ramondomiingos/sistemas-distribuidos)

</div>
