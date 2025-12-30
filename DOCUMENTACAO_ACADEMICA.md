# Adaptação à LGPD: Proposta de Middleware para a Implementação do Direito ao Esquecimento em Sistemas Distribuídos

## Documentação Técnica e Acadêmica

**Autor**: Ramon Domingos  
**Instituição**: Programa de Mestrado em Tecnologia da informação
**Data**: Dezembro de 2025  
**Versão**: 1.0

---

## Resumo Executivo

Esta documentação apresenta a implementação de um **middleware automatizado** para orquestração do direito ao esquecimento em arquiteturas de microsserviços, utilizando o padrão **Two-Phase Commit (2PC)** adaptado para comunicação assíncrona via Apache Kafka.

O sistema proposto oferece uma solução robusta e escalável para a conformidade com a Lei Geral de Proteção de Dados Pessoais (LGPD), facilitando a exclusão consistente de dados distribuídos através de uma biblioteca reutilizável e um middleware centralizador.

**Palavras-chave**: arquitetura de software, middleware, LGPD, privacidade, microsserviços, two-phase commit, Apache Kafka

---

## Índice

1. [Introdução](#1-introdução)
2. [Fundamentação Teórica](#2-fundamentação-teórica)
3. [Arquitetura do Sistema](#3-arquitetura-do-sistema)
4. [Especificação de Componentes](#4-especificação-de-componentes)
5. [Protocolo de Comunicação](#5-protocolo-de-comunicação)
6. [Contratos de API](#6-contratos-de-api)
7. [Biblioteca de Integração](#7-biblioteca-de-integração)
8. [Fluxogramas e Diagramas](#8-fluxogramas-e-diagramas)
9. [Implementação](#9-implementação)
10. [Casos de Uso](#10-casos-de-uso)
11. [Avaliação e Resultados](#11-avaliação-e-resultados)
12. [Considerações de Segurança](#12-considerações-de-segurança)
13. [Trabalhos Futuros](#13-trabalhos-futuros)
14. [Conclusão](#14-conclusão)
15. [Referências](#15-referências)

---

## 1. Introdução

### 1.1 Contextualização

A Lei Geral de Proteção de Dados Pessoais (LGPD - Lei nº 13.709/2018) estabelece o **direito ao esquecimento** como um dos pilares fundamentais da proteção de dados pessoais. Este direito garante aos titulares de dados a prerrogativa de solicitar a eliminação de suas informações pessoais tratadas por organizações.

Em arquiteturas monolíticas, a implementação deste direito é relativamente direta, uma vez que todos os dados residem em um único banco de dados centralizado. Contudo, em **arquiteturas de microsserviços**, onde dados são fragmentados e distribuídos entre múltiplos serviços independentes, a exclusão consistente torna-se um desafio complexo que envolve:

- **Distribuição de dados**: Informações do titular distribuídas em múltiplos serviços
- **Autonomia de serviços**: Cada microsserviço possui sua lógica de negócio e regras de validação
- **Consistência transacional**: Necessidade de garantir que a exclusão seja atômica
- **Auditabilidade**: Rastreamento completo das operações de exclusão

### 1.2 Problema de Pesquisa

**Como implementar o direito ao esquecimento de forma consistente, escalável e auditável em arquiteturas de microsserviços distribuídos, garantindo conformidade com a LGPD?**

### 1.3 Objetivos

#### Objetivo Geral
Desenvolver uma solução de middleware automatizada que orquestre o processo de exclusão de dados em sistemas distribuídos baseados em microsserviços, garantindo consistência transacional e conformidade regulatória.

#### Objetivos Específicos
1. Projetar e implementar um protocolo de comunicação baseado em Two-Phase Commit (2PC) adaptado para comunicação assíncrona
2. Desenvolver uma biblioteca reutilizável (`pacote_privacy`) que facilite a integração de microsserviços existentes
3. Implementar um middleware centralizador responsável pela orquestração do processo de exclusão
4. Garantir auditabilidade completa através de logs estruturados e rastreamento distribuído
5. Validar a solução através de casos de uso representativos

### 1.4 Contribuições

1. **Arquitetura de Middleware**: Proposta de arquitetura modular e extensível para orquestração de privacidade
2. **Biblioteca de Integração**: Componente reutilizável que minimiza o acoplamento e facilita a adoção
3. **Protocolo 2PC Assíncrono**: Adaptação do Two-Phase Commit para ambientes event-driven com Apache Kafka
4. **Framework de Validação**: Mecanismo que permite a cada serviço aplicar suas regras de negócio antes da exclusão
5. **Observabilidade**: Integração com OpenTelemetry para rastreamento distribuído

---

## 2. Fundamentação Teórica

### 2.1 Lei Geral de Proteção de Dados (LGPD)

#### 2.1.1 Direito ao Esquecimento (Art. 18, VI)

A LGPD estabelece que o titular dos dados tem direito à:

> "eliminação dos dados pessoais tratados com o consentimento do titular"

Este direito implica em:
- **Exclusão definitiva**: Dados devem ser irrecuperáveis
- **Prazo razoável**: A exclusão deve ocorrer em tempo hábil
- **Confirmação**: O titular deve ser notificado sobre a conclusão
- **Exceções**: Respeitando as hipóteses legais de retenção

#### 2.1.2 Bases Legais para Retenção

Mesmo com solicitação de exclusão, dados podem ser mantidos quando:
- Cumprimento de obrigação legal ou regulatória
- Transferência a terceiro (respeitadas hipóteses de tratamento)
- Uso exclusivo do controlador (vedado acesso por terceiro)

### 2.2 Arquitetura de Microsserviços

#### 2.2.1 Características

Microsserviços são caracterizados por:

1. **Autonomia**: Cada serviço é desenvolvido, implantado e escalado independentemente
2. **Especialização**: Foco em uma capacidade de negócio específica
3. **Database per Service**: Cada serviço possui seu próprio armazenamento
4. **Comunicação via API**: Interfaces bem definidas (REST, gRPC, eventos)
5. **Descentralização**: Governança e gerenciamento de dados descentralizados

#### 2.2.2 Desafios para Privacidade

- **Fragmentação de dados**: Dados do titular distribuídos em múltiplos serviços
- **Consistência**: Garantir que todos os serviços executem a exclusão
- **Rastreabilidade**: Identificar onde os dados de um titular estão armazenados
- **Falhas parciais**: Lidar com cenários onde alguns serviços falham

### 2.3 Two-Phase Commit (2PC)

#### 2.3.1 Protocolo Clássico

O 2PC é um protocolo de consenso distribuído que garante atomicidade em transações distribuídas:

**Fase 1 - Preparação (Voting Phase)**:
1. Coordenador envia `PREPARE` para todos os participantes
2. Participantes validam se podem executar a transação
3. Participantes respondem `VOTE-COMMIT` ou `VOTE-ABORT`

**Fase 2 - Commit (Decision Phase)**:
1. Se TODOS votaram COMMIT: coordenador envia `GLOBAL-COMMIT`
2. Se ALGUM votou ABORT: coordenador envia `GLOBAL-ABORT`
3. Participantes executam a decisão e confirmam

#### 2.3.2 Adaptação para Privacidade

Nossa adaptação do 2PC para o contexto de privacidade:

**Fase 1 - Validação**:
- Tópico: `privacy-validate-topic`
- Participantes verificam **regras de negócio**
- Exemplos: pagamentos pendentes, entregas em trânsito
- Resposta: `can_delete: true/false` + justificativa

**Fase 2 - Execução**:
- Tópico: `privacy-execute-topic`
- Participantes executam a exclusão
- Transações atômicas no nível de cada serviço
- Resposta: confirmação de sucesso/falha

### 2.4 Apache Kafka

#### 2.4.1 Características Relevantes

- **Publish-Subscribe**: Modelo de comunicação assíncrona
- **Persistência**: Mensagens são armazenadas em disco
- **Replicação**: Tolerância a falhas
- **Consumer Groups**: Processamento paralelo e escalável
- **Offset Management**: Rastreamento de progresso

#### 2.4.2 Uso no Sistema

- **Desacoplamento**: Middleware e serviços comunicam-se assincronamente
- **Resiliência**: Mensagens persistem mesmo com falhas temporárias
- **Auditoria**: Log imutável de todas as operações
- **Escalabilidade**: Suporte a múltiplas instâncias de cada serviço

### 2.5 OpenTelemetry

Framework de observabilidade que fornece:

- **Tracing**: Rastreamento distribuído de requisições
- **Metrics**: Métricas de performance e negócio
- **Logging**: Logs correlacionados com traces

---

## 3. Arquitetura do Sistema

### 3.1 Visão Geral

O sistema é composto por:

1. **Middleware Centralizador**: Orquestra o processo de exclusão
2. **Microsserviços de Domínio**: Accounts, Payments, CRM, Delivery
3. **Biblioteca de Integração**: `pacote_privacy` (KafkaConsumerWrapper)
4. **Infraestrutura de Mensageria**: Apache Kafka + Zookeeper
5. **Observabilidade**: Grafana LGTM Stack (OpenTelemetry + Prometheus + Loki)

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENTE/API                             │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP POST /api/v1/privacy-requests
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MIDDLEWARE SERVICE                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  • Recebe requisição de privacidade                      │   │
│  │  • Registra no banco de dados (PostgreSQL)               │   │
│  │  • Orquestra 2PC via Kafka                               │   │
│  │  • Consolida respostas                                   │   │
│  │  • Atualiza status da requisição                         │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────┬─────────────────────────────────┬──────────────────┘
             │                                 │
             │ Fase 1: Validação               │ Fase 2: Execução
             ▼                                 ▼
┌──────────────────────────┐    ┌──────────────────────────────┐
│ privacy-validate-topic   │    │  privacy-execute-topic       │
└────────┬─────────────────┘    └────────┬─────────────────────┘
         │                                │
         │ Broadcast para todos           │ Broadcast para todos
         ▼                                ▼
┌────────────────────────────────────────────────────────────────┐
│                      MICROSSERVIÇOS                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ ACCOUNTS │  │ PAYMENTS │  │   CRM    │  │ DELIVERY │      │
│  │          │  │          │  │          │  │          │      │
│  │ ┌──────┐ │  │ ┌──────┐ │  │ ┌──────┐ │  │ ┌──────┐ │      │
│  │ │  DB  │ │  │ │  DB  │ │  │ │  DB  │ │  │ │  DB  │ │      │
│  │ └──────┘ │  │ └──────┘ │  │ └──────┘ │  │ └──────┘ │      │
│  │          │  │          │  │          │  │          │      │
│  │ Handlers:│  │ Handlers:│  │ Handlers:│  │ Handlers:│      │
│  │ validate │  │ validate │  │ validate │  │ validate │      │
│  │ execute  │  │ execute  │  │ execute  │  │ execute  │      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│       │             │             │             │            │
│       └─────────────┴─────────────┴─────────────┘            │
│                     │                                         │
│         ┌───────────▼───────────┐                            │
│         │  pacote_privacy       │                            │
│         │  KafkaConsumerWrapper │                            │
│         └───────────────────────┘                            │
└────────────────────────────────────────────────────────────────┘
         │                                │
         ▼                                ▼
┌──────────────────────────┐    ┌──────────────────────────────┐
│privacy-validate-response │    │ privacy-execute-response     │
└────────┬─────────────────┘    └────────┬─────────────────────┘
         │                                │
         └────────────┬───────────────────┘
                      ▼
              ┌───────────────┐
              │  MIDDLEWARE   │
              │  (consolida)  │
              └───────────────┘
```

### 3.2 Padrões Arquiteturais Aplicados

#### 3.2.1 Database per Service
Cada microsserviço possui seu banco de dados PostgreSQL independente, garantindo autonomia e baixo acoplamento.

#### 3.2.2 API Gateway
O Middleware atua como gateway centralizador para requisições de privacidade.

#### 3.2.3 Event-Driven Architecture
Comunicação assíncrona via eventos Kafka permite desacoplamento temporal e escalabilidade.

#### 3.2.4 Saga Pattern (Orquestração)
O Middleware orquestra o processo de exclusão distribuído, gerenciando o fluxo completo.

#### 3.2.5 CQRS (Command Query Responsibility Segregation)
Separação entre comandos (exclusão) e consultas (verificação de dados).

### 3.3 Tecnologias Utilizadas

| Componente | Tecnologia | Versão | Justificativa |
|------------|-----------|--------|---------------|
| **Backend** | Python + FastAPI | 3.9 / 0.100+ | Performance, async/await nativo, tipagem |
| **Mensageria** | Apache Kafka | 3.5 | Persistência, escalabilidade, auditoria |
| **Banco de Dados** | PostgreSQL | 13 | ACID, confiabilidade, JSON support |
| **ORM** | SQLAlchemy | 2.0+ | Maturidade, async support |
| **Cliente Kafka** | aiokafka | 0.8+ | Integração assíncrona com Python |
| **Observabilidade** | OpenTelemetry | 1.x | Padrão da indústria, vendor-neutral |
| **Métricas** | Prometheus | 2.x | Time-series database, alerting |
| **Visualização** | Grafana | 10.x | Dashboards, correlação de dados |
| **Containerização** | Docker + Docker Compose | 24.x | Portabilidade, reprodutibilidade |

---

## 4. Especificação de Componentes

### 4.1 Middleware Service

**Responsabilidades**:
1. Receber requisições de privacidade via API REST
2. Validar e persistir requisições no banco de dados
3. Publicar mensagens de validação no Kafka
4. Consolidar respostas de validação
5. Tomar decisão de commit/abort
6. Publicar mensagens de execução (se aprovado)
7. Consolidar confirmações de execução
8. Atualizar status final da requisição
9. Notificar o titular (futuro)

**Estrutura de Diretórios**:
```
middleware-refactor/
├── alembic/                    # Migrações de banco de dados
│   └── versions/
├── src/
│   ├── api/v1/endpoints/      # Endpoints REST
│   │   ├── privacy_requests.py
│   │   ├── services.py
│   │   └── privacy_request_services.py
│   ├── controller/            # Lógica de orquestração
│   │   ├── kafka_controller.py
│   │   └── privacy_request_service.py
│   ├── core/                  # Configurações e utilidades
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── telemetry.py
│   ├── db/                    # Configuração de banco
│   │   ├── base.py
│   │   └── session.py
│   ├── kafka/                 # Integração Kafka
│   │   ├── consumer.py
│   │   ├── producer.py
│   │   └── topics.py
│   ├── models/                # Modelos SQLAlchemy
│   │   ├── privacy_request.py
│   │   ├── service.py
│   │   └── privacy_request_service.py
│   ├── schemas/               # Schemas Pydantic
│   │   ├── privacy_request.py
│   │   ├── service.py
│   │   └── privacy_request_service.py
│   ├── services/              # Lógica de negócio
│   │   ├── privacy_request.py
│   │   ├── service.py
│   │   └── kafka_service.py
│   └── monitoring/            # Métricas e tracing
│       ├── metrics.py
│       └── tracing.py
├── main.py                    # Entry point
├── alembic.ini               # Config Alembic
├── Dockerfile
└── requirements.txt
```

**Modelos de Dados**:

```python
# Service
class Service:
    id: int
    service_name: str
    description: str
    created_at: datetime
    updated_at: datetime

# PrivacyRequest
class PrivacyRequest:
    id: int
    account_id: str
    request_type: str  # DELETE, EXPORT, ANONYMIZE
    status: str        # PENDING, VALIDATING, EXECUTING, COMPLETED, FAILED
    reason: str
    created_at: datetime
    updated_at: datetime
    completed_at: datetime

# PrivacyRequestService (relacionamento)
class PrivacyRequestService:
    id: int
    privacy_request_id: int
    service_id: int
    validation_status: str  # PENDING, APPROVED, REJECTED
    validation_message: str
    execution_status: str   # PENDING, COMPLETED, FAILED
    execution_message: str
    created_at: datetime
    updated_at: datetime
```

### 4.2 Microsserviços de Domínio

Cada microsserviço implementa:

#### 4.2.1 Accounts Service
- **Domínio**: Gestão de usuários e autenticação
- **Dados**: User (id, name, email, account_id)
- **Regra de Negócio**: Sempre pode deletar (titular dos dados)

#### 4.2.2 Payments Service
- **Domínio**: Transações financeiras
- **Dados**: Order (id, order_id, status, amount, payment_method, account_id)
- **Regra de Negócio**: 
  - ❌ **Bloqueia** se houver pagamentos com status `pending` ou `processing`
  - ✅ **Permite** se todos os pagamentos forem `confirmed`, `cancelled`, `refunded`, `failed`

#### 4.2.3 CRM Service
- **Domínio**: Dados sensíveis de clientes
- **Dados**: UserInfo (id, birth_day, account_id, religion)
- **Regra de Negócio**: Sempre pode deletar (dados sensíveis - direito à privacidade)

#### 4.2.4 Delivery Service
- **Domínio**: Logística e entregas
- **Dados**: Delivery (id, order_id, status, tracking_code, customer_id, shipping_address)
- **Regra de Negócio**:
  - ❌ **Bloqueia** se houver entregas com status `out_for_delivery`, `pending`, `in_transit`
  - ✅ **Permite** se todas as entregas forem `delivered`, `cancelled`, `failed`, `returned`

**Estrutura Comum**:
```
service/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app + handlers Kafka
│   ├── models.py         # SQLAlchemy models
│   ├── schemas.py        # Pydantic schemas
│   ├── database.py       # DB connection
│   ├── telemetry.py      # OpenTelemetry setup
│   └── pacote_privacy/   # Biblioteca (volume montado)
├── Dockerfile
└── requirements.txt
```

### 4.3 Biblioteca de Integração (pacote_privacy)

**Arquivo**: `pacote_privacy/__init__.py`

**Classe Principal**: `KafkaConsumerWrapper`

**Responsabilidades**:
1. Abstrair complexidade de conexão com Kafka
2. Gerenciar múltiplos consumers (validate + execute)
3. Executar handlers customizados para cada tipo de mensagem
4. Publicar respostas automaticamente
5. Gerenciar lifecycle (start/stop)

**Interface**:
```python
class KafkaConsumerWrapper:
    def __init__(
        bootstrap_servers: str,
        consumers_config: Dict[str, Dict],
        client_id_prefix: str,
        auto_offset_reset: str = "latest"
    )
    
    async def start()
    async def stop()
    async def _consume_loop(...)
```

**Configuração de Consumer**:
```python
consumers_config = {
    "validator": {
        "topics": ["privacy-validate-topic"],
        "group_id": "servico-validate-group",
        "handler": validate_handler,
        "response_topic": "privacy-validate-response-topic"
    },
    "executor": {
        "topics": ["privacy-execute-topic"],
        "group_id": "servico-execute-group",
        "handler": execute_handler,
        "response_topic": "privacy-execute-response-topic"
    }
}
```

---

## 5. Protocolo de Comunicação

### 5.1 Fluxo Completo (Two-Phase Commit Adaptado)

#### Fase 0: Registro da Requisição
```
Cliente → Middleware: POST /api/v1/privacy-requests/
{
  "account_id": "123456789",
  "request_type": "DELETE",
  "reason": "Solicitação do titular"
}

Middleware:
1. Valida requisição
2. Persiste no banco (status: PENDING)
3. Retorna request_id ao cliente
4. Inicia Fase 1
```

#### Fase 1: Validação (PREPARE)
```
Middleware → Kafka (privacy-validate-topic):
{
  "request_id": "req-uuid",
  "account_id": "123456789",
  "request_type": "DELETE",
  "timestamp": "2025-12-29T10:00:00Z"
}

Cada Microsserviço:
1. Consome mensagem
2. Executa validate_handler()
   - Verifica regras de negócio
   - Ex: Payments verifica se há pagamentos pendentes
3. Retorna (can_delete: bool, message: str)

Microsserviços → Kafka (privacy-validate-response-topic):
{
  "request_id": "req-uuid",
  "account_id": "123456789",
  "service_name": "payments",
  "result": true,
  "reason": "Validação OK. 3 pedidos confirmados."
}

Middleware:
1. Aguarda respostas (timeout: 30s)
2. Consolida resultados
3. Decide: COMMIT ou ABORT
   - COMMIT: TODAS as respostas com result=true
   - ABORT: QUALQUER resposta com result=false
4. Atualiza status no banco
5. Se COMMIT: inicia Fase 2
   Se ABORT: finaliza com FAILED
```

#### Fase 2: Execução (COMMIT/ABORT)
```
Se decisão = COMMIT:

Middleware → Kafka (privacy-execute-topic):
{
  "request_id": "req-uuid",
  "account_id": "123456789",
  "request_type": "DELETE",
  "timestamp": "2025-12-29T10:00:10Z"
}

Cada Microsserviço:
1. Consome mensagem
2. Executa execute_handler()
   - Deleta dados do account_id
   - Transação atômica no banco local
3. Retorna (success: bool, message: str)

Microsserviços → Kafka (privacy-execute-response-topic):
{
  "request_id": "req-uuid",
  "account_id": "123456789",
  "service_name": "payments",
  "result": true,
  "reason": "5 pedidos deletados com sucesso"
}

Middleware:
1. Aguarda confirmações (timeout: 60s)
2. Consolida resultados
3. Atualiza status:
   - COMPLETED: TODAS as execuções com result=true
   - FAILED: QUALQUER execução com result=false
4. Registra timestamp de conclusão
```

### 5.2 Tópicos Kafka

| Tópico | Produtor | Consumidores | Payload | Partições |
|--------|----------|--------------|---------|-----------|
| `privacy-validate-topic` | Middleware | Todos os serviços | Requisição de validação | 1 |
| `privacy-validate-response-topic` | Serviços | Middleware | Resultado da validação | 1 |
| `privacy-execute-topic` | Middleware | Todos os serviços | Comando de execução | 1 |
| `privacy-execute-response-topic` | Serviços | Middleware | Confirmação de execução | 1 |

### 5.3 Consumer Groups

| Consumer Group | Serviço | Tópicos Consumidos |
|----------------|---------|-------------------|
| `accounts-validate-group` | Accounts | privacy-validate-topic |
| `accounts-execute-group` | Accounts | privacy-execute-topic |
| `payments-validate-group` | Payments | privacy-validate-topic |
| `payments-execute-group` | Payments | privacy-execute-topic |
| `crm-validate-group` | CRM | privacy-validate-topic |
| `crm-execute-group` | CRM | privacy-execute-topic |
| `delivery-validate-group` | Delivery | privacy-validate-topic |
| `delivery-execute-group` | Delivery | privacy-execute-topic |

### 5.4 Tratamento de Falhas

#### 5.4.1 Timeout na Validação
- **Cenário**: Serviço não responde em 30s
- **Ação**: Middleware considera como ABORT
- **Justificativa**: Princípio da segurança (fail-safe)

#### 5.4.2 Timeout na Execução
- **Cenário**: Serviço não confirma execução em 60s
- **Ação**: Middleware marca como FAILED + retry manual
- **Justificativa**: Requer investigação humana

#### 5.4.3 Falha Parcial na Execução
- **Cenário**: Alguns serviços executam, outros falham
- **Ação**: Status PARTIALLY_COMPLETED + log detalhado
- **Compensação**: Processo manual de rollback nos serviços que executaram

#### 5.4.4 Indisponibilidade de Serviço
- **Cenário**: Serviço completamente offline
- **Ação**: Mensagens ficam no Kafka (persistência)
- **Recuperação**: Quando o serviço volta, processa mensagens pendentes

---

*[Continua na próxima seção...]*

**Status**: Este é o documento principal (Parte 1 de 4). Continuarei gerando as partes restantes com Contratos de API, Fluxogramas, Implementação e Casos de Uso.
