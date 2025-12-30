# Adaptação à LGPD: Middleware para Implementação do Direito ao Esquecimento em Sistemas Distribuídos

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Kafka](https://img.shields.io/badge/Apache%20Kafka-3.5-red.svg)](https://kafka.apache.org/)
[![Docker](https://img.shields.io/badge/Docker-24+-blue.svg)](https://www.docker.com/)

> **Dissertação de Mestrado**: Proposta de middleware automatizado para orquestração do direito ao esquecimento (LGPD Art. 18, VI) em arquiteturas de microsserviços distribuídos, utilizando o padrão Two-Phase Commit adaptado para comunicação assíncrona via Apache Kafka.

**Autor**: Ramon Domingos  
**Programa**: Mestrado em Tecnologia da Informação
**Ano**: 2025

---

## 📋 Índice

- [Visão Geral](#-visão-geral)
- [Problema de Pesquisa](#-problema-de-pesquisa)
- [Arquitetura](#-arquitetura)
- [Tecnologias](#-tecnologias)
- [Instalação e Execução](#-instalação-e-execução)
- [Documentação](#-documentação)
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

### Teste Rápido

```bash
# Criar requisição de privacidade
curl -X POST http://localhost:8000/api/v1/privacy-requests/ \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "123456789",
    "request_type": "DELETE",
    "reason": "Solicitação do titular conforme LGPD Art. 18"
  }'

# Resposta esperada:
# {
#   "id": 1,
#   "account_id": "123456789",
#   "request_type": "DELETE",
#   "status": "PENDING",
#   ...
# }

# Aguardar processamento (2-5 segundos)
sleep 5

# Consultar status
curl http://localhost:8000/api/v1/privacy-requests/1

# Status esperado: "COMPLETED" ou "FAILED"
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

## 💡 Casos de Uso

### Caso 1: Exclusão Bem-Sucedida ✅

**Cenário**: Titular solicita exclusão, todos os serviços aprovam.

```bash
# 1. Criar requisição
POST /api/v1/privacy-requests/
{
  "account_id": "123456789",
  "request_type": "DELETE"
}

# 2. Resultado
# Status: COMPLETED
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
  "request_type": "DELETE"
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

<!-- ## 📖 Publicações

### Artigos Submetidos

1. **DOMINGOS, R.** "Privacy-by-Design em Microsserviços: Framework para Direito ao Esquecimento". Simpósio Brasileiro de Bancos de Dados (SBBD), 2025. *(submetido)*

2. **DOMINGOS, R.; [ORIENTADOR]**. "Two-Phase Commit Assíncrono para Exclusão Distribuída em Conformidade com LGPD". Journal of Internet Services and Applications (JISA), 2025. *(em preparação)*

### Apresentações

- **Workshop de Privacidade e Proteção de Dados**, [Instituição], Dez/2025
- **Seminário de Pesquisa em Sistemas Distribuídos**, [Instituição], Nov/2025

--- -->

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
📧 Email: [orientador]@[instituicao].br

**Instituição**: UNIVERSIDADE FEDERAL DO RIO GRANDO DO NORTE
**Programa**: Mestrado profissional em Tecnologia da Informação  
**Linha de Pesquisa**: Engenharia de Software

---

## 🙏 Agradecimentos

- **[Orientador]** - Orientação e suporte acadêmico
- **[Instituição]** - Infraestrutura e recursos
- **Comunidade Open Source** - FastAPI, Kafka, PostgreSQL, OpenTelemetry


---

## 📚 Citação

Se você utilizar este trabalho em sua pesquisa, por favor cite:
#TODO

```bibtex
@mastersthesis{domingos2025lgpd,
  author  = {Ramon Domingos},
  title   = {Adaptação à LGPD: Proposta de Middleware para a Implementação 
             do Direito ao Esquecimento em Sistemas Distribuídos},
  school  = {UNIVERSIDADE FEDERAL DO RIO GRANDO DO NORTE},
  year    = {2026},
  type    = {Dissertação de Mestrado},
  address = {[Natal, RN]},
  month   = {Fevereiro}
}
```

---

<div align="center">

**⭐ Se este projeto foi útil para sua pesquisa, considere dar uma estrela!**

[![Star on GitHub](https://img.shields.io/github/stars/ramondomiingos/sistemas-distribuidos?style=social)](https://github.com/ramondomiingos/sistemas-distribuidos)

</div>
