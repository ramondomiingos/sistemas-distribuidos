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
- **[Experimentos](#experimentos)** — reprodução dos resultados do artigo
- **[Visão Geral do Projeto](#-visão-geral)** — contexto acadêmico e arquitetura
- **[Documentação Complementar](#-documentação)** — documentação acadêmica detalhada

---

## Selos Considerados

Os selos considerados são: **Disponíveis**, **Funcionais**, **Sustentáveis** e **Experimentos Reprodutíveis**.

- **Disponível (SeloD)**: o artefato está publicamente acessível no GitHub com licença MIT, incluindo código-fonte completo, scripts de experimento e dados brutos dos resultados na pasta `/output-benchmark`.
- **Funcional (SeloF)**: o artefato pode ser executado em ambiente local via Docker Compose, reproduzindo o comportamento descrito no artigo — incluindo o protocolo 2PC completo e a coleta de métricas de recursos. O README apresenta lista de dependências com versões, descrição do ambiente, instruções de instalação e um exemplo de execução mínima.
- **Sustentável (SeloS)**: o código está modularizado em componentes bem definidos (middleware, microsserviços, biblioteca `pacote_privacy`), acompanhado de documentação acadêmica detalhada (`DOCUMENTACAO_ACADEMICA*.md`), manual de integração (`MANUAL_INTEGRACAO_NOVOS_SERVICOS.md`) e seção de experimentos com reivindicações identificadas explicitamente no README.
- **Reprodutível (SeloR)**: as principais reivindicações do artigo (completude 100% do protocolo 2PC e eficiência de recursos) podem ser reproduzidas por meio de scripts automatizados (`tools/benchmark.sh`, `tools/bulk_insert_and_delete.py`, `tools/check_completude.py`) que replicam integralmente a metodologia experimental descrita no artigo, incluindo as três execuções independentes com coleta de métricas em série temporal rotulada por fase.

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
| Python | 3.9+ | Apenas para scripts de benchmark |
| Git | qualquer | |
| Bash | 3.2+ | Compatível com macOS bash padrão |

### Portas Utilizadas

As seguintes portas devem estar livres no host: `3000, 5001–5004, 5432–5437, 8000, 8080, 9090, 9092, 2181`.

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

```bash
pip install psycopg2-binary faker requests
```

| Pacote | Uso |
|--------|-----|
| psycopg2-binary | Conexão direta com PostgreSQL para inserção de dados |
| faker | Geração de dados sintéticos (nomes, emails) |
| requests | Submissão das requisições HTTP ao middleware |

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
├── Accounts (Port 5001)           - Gestão de usuários
├── Payments (Port 5002)           - Transações financeiras
├── CRM (Port 5003)                - Dados sensíveis (LGPD Art. 5, II)
├── Delivery (Port 5004)           - Logística e entregas
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
- Portas 3000, 5001-5004, 5432-5437, 8000, 9090, 9092 disponíveis

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
curl http://localhost:5001/health      # Accounts
curl http://localhost:5002/health      # Payments

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

## Experimentos

Esta seção descreve como reproduzir os dois resultados principais do artigo.

**Pré-requisito**: instale as dependências Python do host antes de executar os experimentos:

```bash
pip install psycopg2-binary faker requests
```

---

### Reivindicação 1 — Completude do Protocolo 2PC (100%)

**Afirmação do artigo**: o middleware garante a execução integral do direito ao esquecimento — todas as 900 requisições percorrem as duas fases do protocolo (PREPARE\_DELETE e PERFORM\_DELETE) com sucesso, e os registros são removidos de todos os quatro microsserviços participantes.

**Resultado esperado**: completude de 100% e 0 registros remanescentes em cada banco de dados.

**Tempo estimado**: ~5 minutos por execução (inserção + processamento).

**Recursos esperados**: pico de ~47% CPU no container do middleware, ~75 MiB RAM por container.

**Passos**:

```bash
# 1. Certifique-se de que todos os containers estão em execução
docker compose ps

# 2. (Opcional) Limpe dados de execuções anteriores
docker compose exec middleware_db psql -U user -d middlewaredb \
  -c "DELETE FROM privacy_request_services; DELETE FROM privacy_requests;"

# 3. Execute o script de inserção e exclusão (900 contas)
python tools/bulk_insert_and_delete.py

# Saída esperada:
#   ✓ 900/900 contas inseridas
#   Requisições submetidas: 900 | Erros: 0

# 4. Aguarde o processamento (até 5 minutos)
# O script abaixo monitora o progresso:
python3 tools/check_completude.py \
  --run 1 \
  --account-ids tools/account_ids.json \
  --output /tmp/completude_resultado.json \
  --ts-inicio "$(date '+%Y-%m-%d %H:%M:%S')" \
  --summary /tmp/summary.csv

# 5. Verifique o resultado
cat /tmp/completude_resultado.json
```

**Interpretação do resultado**:
- `completude_pct: 100.0` — todas as requisições concluíram o protocolo 2PC
- `registros_restantes_por_servico: {"accounts_users": 0, "payments_orders": 0, "crm_user_info": 0, "delivery_deliveries": 0}` — deleção completa em todos os microsserviços

---

### Reivindicação 2 — Eficiência de Recursos (Benchmark Completo)

**Afirmação do artigo**: o middleware concentra o consumo de CPU durante o pico (~47%), com overhead residual no pós-processamento (~11%), enquanto o consumo de memória permanece estável e inferior a 75 MiB por container em todas as condições.

**Resultado esperado**: séries temporais de CPU e memória com o padrão repouso → pico → recuperação descrito no artigo, com médias e desvios padrão reproduzindo os valores das tabelas.

**Tempo estimado**: ~15–20 minutos por execução completa (3× ~5 min + intervalos). O benchmark completo (3 execuções) leva aproximadamente 60–70 minutos.

**Recursos esperados**: pico de ~50% CPU total da máquina host durante a fase de carga.

**Passos**:

```bash
# A partir da raiz do repositório:
bash tools/benchmark.sh

# O script gera automaticamente em output-pdf/:
#   benchmark_run_1_<timestamp>.csv  — série temporal de recursos (run 1)
#   benchmark_run_2_<timestamp>.csv  — série temporal de recursos (run 2)
#   benchmark_run_3_<timestamp>.csv  — série temporal de recursos (run 3)
#   completude_run_1_<timestamp>.json — completude run 1
#   completude_run_2_<timestamp>.json — completude run 2
#   completude_run_3_<timestamp>.json — completude run 3
#   benchmark_summary.csv            — resumo das 3 execuções
```

**Verificar resultados**:

```bash
# Resumo de completude
cat output-pdf/benchmark_summary.csv

# Calcular médias de CPU por fase (middleware)
# Filtrar apenas o container do middleware, separar por fase:
grep "middleware" output-pdf/benchmark_run_1_*.csv | \
  awk -F',' '{gsub(/%/,"",$5); print $2, $5}' | \
  sort | awk '{sum[$1]+=$2; cnt[$1]++} END {for(p in sum) print p, sum[p]/cnt[p]}'
```

**Interpretação**: a coluna `Fase` nos CSVs assume os valores `repouso`, `pico` e `pos`, permitindo comparação direta com as tabelas do artigo. Os valores de CPU do middleware devem estar próximos de 1,7% (repouso), 47,5% (pico) e 10,8% (pós), com desvio padrão < 3% entre execuções.

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

| Métrica | Valor Médio | Desvio Padrão |
|---------|-------------|---------------|
| **Tempo de Validação** | 234ms | ±45ms |
| **Tempo de Execução** | 567ms | ±120ms |
| **Tempo Total (E2E)** | 801ms | ±165ms |
| **Taxa de Sucesso** | 94.5% | - |

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
