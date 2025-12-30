# Manual de Integração de Novos Serviços ao Middleware de Privacidade LGPD

> **Versão**: 1.0  
> **Data**: Dezembro 2025  
> **Autor**: Ramon Domingos  
> **Baseado em**: Serviços reais (Accounts, Payments, CRM, Delivery)

---

## 📋 Índice

1. [Visão Geral](#1-visão-geral)
2. [Pré-requisitos](#2-pré-requisitos)
3. [Passo-a-Passo Simplificado](#3-passo-a-passo-simplificado)
4. [Exemplos Reais do Projeto](#4-exemplos-reais-do-projeto)
5. [Padrões de Handlers](#5-padrões-de-handlers)
6. [Testes](#6-testes)
7. [Troubleshooting](#7-troubleshooting)
8. [Checklist](#8-checklist)

---

## 1. Visão Geral

### 1.1 Objetivo

Este manual mostra **como integrar um novo microsserviço** ao middleware de privacidade LGPD em **3 passos simples**:

1. Importar o pacote de privacidade (`KafkaConsumerWrapper`)
2. Criar 2 funções: `validate_handler` e `execute_handler`
3. Configurar Kafka no startup da aplicação

### 1.2 O que você vai implementar

**Fase 1 - VALIDATE** (`validate_handler`):
- Recebe `account_id` via Kafka
- Verifica suas regras de negócio
- Retorna `(True/False, "mensagem")`

**Fase 2 - EXECUTE** (`execute_handler`):
- Recebe `account_id` via Kafka
- Deleta dados do banco
- Retorna `(True, "mensagem")` ou `(False, "erro")`

**KafkaConsumerWrapper**:
- Gerencia consumers Kafka automaticamente
- Publica respostas nos tópicos corretos
- Já está implementado no pacote

### 1.3 Fluxo Simplificado

```
┌─────────────────────────────────────────────────────────┐
│  MIDDLEWARE  →  Publica evento  →  KAFKA                │
│                                      ↓                  │
│  SEU SERVIÇO  ←  Consome evento  ←  KAFKA               │
│       ↓                                                 │
│  validate_handler() ou execute_handler()                │
│       ↓                                                 │
│  Retorna (True/False, "mensagem")                       │
│       ↓                                                 │
│  KafkaConsumerWrapper publica resposta → KAFKA          │
│                                      ↓                  │
│  MIDDLEWARE  ←  Consolida respostas  ←  KAFKA           │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Pré-requisitos

### 2.1 Dependências

Adicione ao seu `requirements.txt`:

```txt
fastapi
uvicorn
sqlalchemy
psycopg2-binary
aiokafka
```

### 2.2 Variáveis de Ambiente

Configure no seu `.env` ou `docker-compose.yml`:

```bash
DATABASE_URL=postgresql://user:pass@db:5432/seu_servico
KAFKA_BROKER=kafka:9092
```

### 2.3 Estrutura Mínima

```
seu-servico/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI + handlers
│   ├── models.py            # SQLAlchemy models
│   └── pacote_privacy.py    # ⭐ Copie de outro serviço
├── Dockerfile
└── requirements.txt
```

---

## 3. Passo-a-Passo Simplificado

### PASSO 1: Copiar o pacote de privacidade

O pacote `pacote_privacy.py` já existe nos serviços. **Copie de qualquer serviço existente**:

```bash
# Copie de accounts, payments, crm ou delivery
cp accounts/app/pacote_privacy.py seu-servico/app/
```

**Ou copie este código** direto para `seu-servico/app/pacote_privacy.py`:

```python
from typing import Dict, Callable, Any
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

class KafkaConsumerWrapper:
    """
    Wrapper para gerenciar múltiplos consumers Kafka com handlers personalizados.
    """
    def __init__(
        self,
        bootstrap_servers: str,
        consumers_config: Dict[str, Dict[str, Any]],
        client_id_prefix: str = "service",
    ):
        self.bootstrap_servers = bootstrap_servers
        self.consumers_config = consumers_config
        self.client_id_prefix = client_id_prefix
        self.consumers = {}
        self.producer = None
        self.tasks = []

    async def start(self):
        """Inicia producer e consumers."""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            client_id=f"{self.client_id_prefix}-producer",
        )
        await self.producer.start()
        logger.info(f"Producer iniciado: {self.client_id_prefix}")

        for name, config in self.consumers_config.items():
            consumer = AIOKafkaConsumer(
                *config["topics"],
                bootstrap_servers=self.bootstrap_servers,
                group_id=config["group_id"],
                client_id=f"{self.client_id_prefix}-{name}",
                auto_offset_reset="earliest",
                enable_auto_commit=True,
            )
            await consumer.start()
            self.consumers[name] = consumer
            logger.info(f"Consumer iniciado: {name} | Topics: {config['topics']}")

            # Cria task para consumir mensagens
            task = asyncio.create_task(
                self._consume_messages(consumer, config["handler"], config["response_topic"])
            )
            self.tasks.append(task)

    async def _consume_messages(
        self, 
        consumer: AIOKafkaConsumer, 
        handler: Callable,
        response_topic: str
    ):
        """Consome mensagens e chama handler."""
        async for msg in consumer:
            try:
                logger.info(f"Mensagem recebida: {msg.value.decode()}")
                
                # Chama handler (retorna tupla: success, message)
                success, message = await handler(msg, self.producer)
                
                # Prepara resposta
                txt = json.loads(msg.value.decode())
                response = {
                    "privacy_request_id": txt.get("privacy_request_id"),
                    "service": self.client_id_prefix,
                    "success": success,
                    "message": message,
                }
                
                # Publica resposta
                await self.producer.send(
                    response_topic,
                    json.dumps(response).encode(),
                )
                logger.info(f"Resposta enviada: {response}")
                
            except Exception as e:
                logger.error(f"Erro ao processar mensagem: {e}", exc_info=True)

    async def stop(self):
        """Para todos os consumers e producer."""
        for task in self.tasks:
            task.cancel()
        
        for consumer in self.consumers.values():
            await consumer.stop()
        
        if self.producer:
            await self.producer.stop()
        
        logger.info("Kafka wrapper encerrado")
```

### PASSO 2: Importar no seu main.py

No início do seu `main.py`:

```python
from typing import Optional
from fastapi import FastAPI
import os
import logging
import json
from aiokafka import AIOKafkaProducer
from aiokafka.structs import ConsumerRecord
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# ⭐ IMPORTAR O PACOTE
from .pacote_privacy import KafkaConsumerWrapper

# Configurações
DATABASE_URL = os.getenv("DATABASE_URL")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BROKER", "kafka:9092")

# ⭐ DEFINIR TÓPICOS (padrão do projeto)
PRIVACY_VALIDATE_TOPIC = "privacy-validate-topic"
PRIVACY_VALIDATE_RESPONSE_TOPIC = "privacy-validate-response-topic"
PRIVACY_EXECUTE_TOPIC = "privacy-execute-topic"
PRIVACY_EXECUTE_RESPONSE_TOPIC = "privacy-execute-response-topic"

# Setup banco
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# FastAPI app
app = FastAPI(title='seu-servico')

# ⭐ VARIÁVEL GLOBAL para o wrapper
kafka_wrapper: Optional[KafkaConsumerWrapper] = None
```

### PASSO 3: Implementar os 2 handlers

**3.1 - Handler de Validação**

Este handler verifica se **pode deletar** baseado nas suas regras de negócio:

```python
async def validate_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    """
    FASE 1 - VALIDAÇÃO
    
    Retorna:
        (True, "mensagem")  → Pode prosseguir
        (False, "motivo")   → Não pode prosseguir
    """
    txt = json.loads(msg.value.decode())
    account_id = txt["account_id"]
    
    logger.info(f"[VALIDATE] Processando account_id: {account_id}")
    
    db = SessionLocal()
    try:
        # Exemplo: Buscar registros do usuário
        from .models import SeuModel
        registros = db.query(SeuModel).filter(SeuModel.account_id == account_id).all()
        
        if not registros:
            logger.info(f"[VALIDATE] Nenhum registro encontrado")
            return True, "Nenhum registro encontrado"
        
        # ⭐ APLICAR SUAS REGRAS DE NEGÓCIO AQUI
        # Exemplo: Bloquear se houver status pendente
        pendentes = [r for r in registros if r.status == "pending"]
        if pendentes:
            logger.warning(f"[VALIDATE] {len(pendentes)} registros pendentes")
            return False, f"Existem {len(pendentes)} registros pendentes"
        
        logger.info(f"[VALIDATE] OK - {len(registros)} registros podem ser deletados")
        return True, f"Validação OK - {len(registros)} registros"
        
    except Exception as e:
        logger.error(f"[VALIDATE] Erro: {e}", exc_info=True)
        return False, f"Erro ao validar: {str(e)}"
    finally:
        db.close()
```

**3.2 - Handler de Execução**

Este handler **efetivamente deleta** os dados:

```python
async def execute_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    """
    FASE 2 - EXECUÇÃO
    
    Retorna:
        (True, "mensagem sucesso")  → Deletou com sucesso
        (False, "mensagem erro")    → Erro ao deletar
    """
    txt = json.loads(msg.value.decode())
    account_id = txt["account_id"]
    
    logger.info(f"[EXECUTE] Processando account_id: {account_id}")
    
    db = SessionLocal()
    try:
        from .models import SeuModel
        
        # Buscar registros
        registros = db.query(SeuModel).filter(SeuModel.account_id == account_id).all()
        
        if not registros:
            logger.info(f"[EXECUTE] Nenhum registro para deletar")
            return True, "Nenhum registro para deletar"
        
        # ⭐ DELETAR REGISTROS
        count = len(registros)
        for registro in registros:
            db.delete(registro)
        
        db.commit()
        logger.info(f"[EXECUTE] {count} registros deletados com sucesso")
        return True, f"{count} registros deletados"
        
    except Exception as e:
        db.rollback()
        logger.error(f"[EXECUTE] Erro: {e}", exc_info=True)
        return False, f"Erro ao deletar: {str(e)}"
    finally:
        db.close()
```

### PASSO 4: Configurar Kafka no startup

Adicione os eventos de **startup** e **shutdown** do FastAPI:

```python
@app.on_event("startup")
async def startup_event():
    """Inicializa consumers Kafka no startup."""
    global kafka_wrapper
    
    # ⭐ CONFIGURAÇÃO DOS CONSUMERS
    consumers_config = {
        "validator": {
            "topics": [PRIVACY_VALIDATE_TOPIC],
            "group_id": "seu-servico-validate-group",  # ← Mude aqui
            "handler": validate_handler,
            "response_topic": PRIVACY_VALIDATE_RESPONSE_TOPIC,
        },
        "executor": {
            "topics": [PRIVACY_EXECUTE_TOPIC],
            "group_id": "seu-servico-execute-group",   # ← Mude aqui
            "handler": execute_handler,
            "response_topic": PRIVACY_EXECUTE_RESPONSE_TOPIC,
        },
    }
    
    # ⭐ INICIALIZAR WRAPPER
    kafka_wrapper = KafkaConsumerWrapper(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        consumers_config=consumers_config,
        client_id_prefix="seu-servico",  # ← Mude aqui
    )
    
    await kafka_wrapper.start()
    app.state.kafka_wrapper = kafka_wrapper
    logger.info("[STARTUP] Kafka wrapper inicializado")


@app.on_event("shutdown")
async def shutdown_event():
    """Encerra consumers Kafka no shutdown."""
    if kafka_wrapper:
        await kafka_wrapper.stop()
        logger.info("[SHUTDOWN] Kafka wrapper encerrado")
```

### ✅ Pronto!

Seu serviço agora está integrado ao middleware de privacidade LGPD!

---

## 4. Exemplos Reais do Projeto

### 4.1 Serviço Accounts (Mais Simples)

**Validação**: Sempre aprovado (sem regras de negócio)

```python
async def validate_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    txt = json.loads(msg.value.decode())
    logger.info(f"[VALIDATE] account_id={txt['account_id']}")
    
    db = SessionLocal()
    user = db.query(User).filter(User.account_id == txt["account_id"]).first()
    db.close()
    
    if user is None:
        return True, "Usuário não encontrado"
    
    return True, "Validação OK"
```

**Execução**: Delete simples

```python
async def execute_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    txt = json.loads(msg.value.decode())
    logger.info(f"[EXECUTE] account_id={txt['account_id']}")
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.account_id == txt["account_id"]).first()
        if user is None:
            return True, "Usuário não encontrado"
        
        db.delete(user)
        db.commit()
        return True, "Usuário deletado"
    except Exception as e:
        db.rollback()
        return False, f"Erro: {e}"
    finally:
        db.close()
```

### 4.2 Serviço Payments (Com Regra de Negócio)

**Validação**: Bloqueia se houver pagamentos pendentes

```python
async def validate_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    txt = json.loads(msg.value.decode())
    logger.info(f"[VALIDATE] account_id={txt['account_id']}")
    
    db = SessionLocal()
    try:
        orders = db.query(Order).filter(Order.account_id == txt["account_id"]).all()
        
        if not orders:
            return True, "Nenhum pedido encontrado"
        
        # ⭐ REGRA: Não pode ter pedidos pendentes
        pending = [o for o in orders if o.status in ["pending", "processing"]]
        if pending:
            return False, f"{len(pending)} pedidos pendentes"
        
        return True, f"Validação OK. {len(orders)} pedidos"
    finally:
        db.close()
```

**Execução**: Delete todos os pedidos

```python
async def execute_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    txt = json.loads(msg.value.decode())
    logger.info(f"[EXECUTE] account_id={txt['account_id']}")
    
    db = SessionLocal()
    try:
        orders = db.query(Order).filter(Order.account_id == txt["account_id"]).all()
        
        if not orders:
            return True, "Nenhum pedido para deletar"
        
        count = len(orders)
        for order in orders:
            db.delete(order)
        
        db.commit()
        return True, f"{count} pedidos deletados"
    except Exception as e:
        db.rollback()
        return False, f"Erro: {e}"
    finally:
        db.close()
```

---

## 5. Padrões de Handlers

---

## 5. Padrões de Handlers

### 5.1 Template: Validação Sempre Aprovada

Use quando **não houver regras de negócio específicas**:

```python
async def validate_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    txt = json.loads(msg.value.decode())
    account_id = txt["account_id"]
    
    logger.info(f"[VALIDATE] account_id={account_id}")
    
    # Sem regras de negócio, sempre aprovado
    return True, "Validação OK"
```

### 5.2 Template: Validação com Regra de Negócio

Use quando **precisar verificar condições antes de permitir exclusão**:

```python
async def validate_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    txt = json.loads(msg.value.decode())
    account_id = txt["account_id"]
    
    logger.info(f"[VALIDATE] account_id={account_id}")
    
    db = SessionLocal()
    try:
        # Buscar registros
        registros = db.query(MeuModel).filter(MeuModel.account_id == account_id).all()
        
        if not registros:
            return True, "Nenhum registro encontrado"
        
        # ⭐ APLICAR SUA REGRA AQUI
        # Exemplo: Bloquear se status = "active"
        ativos = [r for r in registros if r.status == "active"]
        if ativos:
            return False, f"{len(ativos)} registros ativos. Não pode deletar."
        
        return True, f"OK - {len(registros)} registros podem ser deletados"
    except Exception as e:
        logger.error(f"Erro: {e}")
        return False, f"Erro ao validar: {e}"
    finally:
        db.close()
```

### 5.3 Template: Execução Simples (1 tabela)

Use quando **tiver apenas 1 tabela para deletar**:

```python
async def execute_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    txt = json.loads(msg.value.decode())
    account_id = txt["account_id"]
    
    logger.info(f"[EXECUTE] account_id={account_id}")
    
    db = SessionLocal()
    try:
        # Buscar e deletar
        registros = db.query(MeuModel).filter(MeuModel.account_id == account_id).all()
        
        if not registros:
            return True, "Nenhum registro para deletar"
        
        count = len(registros)
        for registro in registros:
            db.delete(registro)
        
        db.commit()
        logger.info(f"{count} registros deletados")
        return True, f"{count} registros deletados"
    except Exception as e:
        db.rollback()
        logger.error(f"Erro: {e}")
        return False, f"Erro ao deletar: {e}"
    finally:
        db.close()
```

### 5.4 Template: Execução Múltiplas Tabelas

Use quando **tiver várias tabelas relacionadas**:

```python
async def execute_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    txt = json.loads(msg.value.decode())
    account_id = txt["account_id"]
    
    logger.info(f"[EXECUTE] account_id={account_id}")
    
    db = SessionLocal()
    try:
        deleted = {}
        
        # ⭐ DELETAR EM ORDEM (relacionamentos)
        # 1. Tabelas dependentes primeiro
        deleted["detalhes"] = len(db.query(Detalhes).filter(Detalhes.account_id == account_id).all())
        db.query(Detalhes).filter(Detalhes.account_id == account_id).delete()
        
        # 2. Tabela principal por último
        deleted["principal"] = len(db.query(Principal).filter(Principal.account_id == account_id).all())
        db.query(Principal).filter(Principal.account_id == account_id).delete()
        
        db.commit()
        total = sum(deleted.values())
        logger.info(f"{total} registros deletados: {deleted}")
        return True, f"{total} registros deletados"
    except Exception as e:
        db.rollback()
        logger.error(f"Erro: {e}")
        return False, f"Erro ao deletar: {e}"
    finally:
        db.close()
```

---

## 6. Testes

### 6.1 Teste Manual: Verificar Consumers

### 6.1 Teste Manual: Verificar Consumers

Após iniciar o serviço, verifique se os consumers foram criados:

```bash
# 1. Listar consumer groups
docker compose exec kafka kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 --list | grep seu-servico

# Esperado:
# seu-servico-validate-group
# seu-servico-execute-group

# 2. Ver detalhes do consumer
docker compose exec kafka kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group seu-servico-validate-group \
  --describe
```

### 6.2 Teste End-to-End

Teste completo passando pelo middleware:

```bash
# 1. Criar requisição de privacidade
curl -X POST http://localhost:8000/api/v1/privacy-requests/ \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "test123",
    "request_type": "DELETE",
    "reason": "Teste de integração"
  }'

# Resposta: {"id": 1, ...}

# 2. Aguardar processamento
sleep 5

# 3. Verificar resultado
curl http://localhost:8000/api/v1/privacy-requests/1

# 4. Verificar logs do seu serviço
docker compose logs seu-servico | grep "test123"
```

### 6.3 Teste Manual Kafka (Debug)

Publique mensagens diretamente no Kafka para testar:

```bash
# 1. Publicar no tópico de validação
docker compose exec kafka kafka-console-producer.sh \
  --bootstrap-server localhost:9092 \
  --topic privacy-validate-topic

# Cole e pressione Enter:
{"privacy_request_id": 999, "account_id": "test456", "request_type": "DELETE"}

# 2. Consumir resposta
docker compose exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic privacy-validate-response-topic \
  --from-beginning \
  --max-messages 1

# Esperado: {"privacy_request_id": 999, "service": "seu-servico", "success": true, ...}
```

---

## 7. Troubleshooting

### 7.1 Consumers não iniciam

**Erro**: `Failed to connect to Kafka`

**Solução**:
```bash
# Verificar se Kafka está rodando
docker compose ps kafka

# Verificar logs
docker compose logs kafka | tail -50

# Testar conectividade
docker compose exec seu-servico ping kafka
```

### 7.2 Handlers não são chamados

**Sintoma**: Mensagens ficam no tópico mas não são processadas

**Solução**:
```bash
# 1. Verificar lag do consumer
docker compose exec kafka kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group seu-servico-validate-group \
  --describe

# Se LAG > 0, mensagens não estão sendo consumidas

# 2. Verificar logs do serviço
docker compose logs seu-servico | grep "Mensagem recebida"

# 3. Verificar configuração do startup
# Confirme que @app.on_event("startup") está sendo executado
docker compose logs seu-servico | grep "Kafka wrapper inicializado"
```

### 7.3 Erro ao deletar dados

**Sintoma**: `execute_handler` retorna erro

**Solução**:
```python
# Adicione logging detalhado
logger.info(f"Registros encontrados: {len(registros)}")
logger.info(f"IDs: {[r.id for r in registros]}")

# Verifique constraints do banco
# Pode haver foreign keys impedindo deleção
```

### 7.4 Tópicos não existem

**Erro**: `UnknownTopicOrPartitionError`

**Solução**:
```bash
# Listar tópicos
docker compose exec kafka kafka-topics.sh \
  --bootstrap-server localhost:9092 --list

# Criar tópicos manualmente (se auto-create estiver desabilitado)
docker compose exec kafka kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create \
  --topic privacy-validate-topic \
  --partitions 3 \
  --replication-factor 1
```

---

## 8. Checklist

### ✅ Desenvolvimento

- [ ] `pacote_privacy.py` copiado para o projeto
- [ ] `validate_handler` implementado com regras de negócio
- [ ] `execute_handler` implementado com lógica de exclusão
- [ ] Variáveis de ambiente configuradas (DATABASE_URL, KAFKA_BROKER)
- [ ] Tópicos Kafka definidos nas constantes
- [ ] `@app.on_event("startup")` configurado com KafkaConsumerWrapper
- [ ] `@app.on_event("shutdown")` configurado para cleanup
- [ ] Models do banco possuem coluna `account_id`
- [ ] Logging configurado (INFO level)

### ✅ Testes

- [ ] Serviço inicia sem erros (`docker compose up`)
- [ ] Consumer groups criados no Kafka (2 groups)
- [ ] Endpoint `/health` respondendo
- [ ] Teste end-to-end via middleware executado
- [ ] Validação retornando resposta correta
- [ ] Execução deletando dados do banco
- [ ] Logs sendo gerados corretamente

### ✅ Deploy

- [ ] Dockerfile criado
- [ ] Serviço adicionado ao `docker-compose.yml`
- [ ] Banco de dados configurado (se necessário)
- [ ] Documentação interna atualizada
- [ ] README do serviço criado

---

## 9. Resumo Rápido

### O que você precisa fazer:

1. **Copiar `pacote_privacy.py`** de outro serviço
2. **Criar 2 funções** no seu `main.py`:
   - `validate_handler(msg, producer)` → retorna `(True/False, "mensagem")`
   - `execute_handler(msg, producer)` → retorna `(True/False, "mensagem")`
3. **Configurar startup** com `KafkaConsumerWrapper`

### Código Mínimo Completo:

```python
# main.py
from fastapi import FastAPI
from typing import Optional
import os, json, logging
from aiokafka import AIOKafkaProducer
from aiokafka.structs import ConsumerRecord
from .pacote_privacy import KafkaConsumerWrapper

# Configuração
DATABASE_URL = os.getenv("DATABASE_URL")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BROKER", "kafka:9092")
PRIVACY_VALIDATE_TOPIC = "privacy-validate-topic"
PRIVACY_VALIDATE_RESPONSE_TOPIC = "privacy-validate-response-topic"
PRIVACY_EXECUTE_TOPIC = "privacy-execute-topic"
PRIVACY_EXECUTE_RESPONSE_TOPIC = "privacy-execute-response-topic"

logger = logging.getLogger(__name__)
app = FastAPI()
kafka_wrapper: Optional[KafkaConsumerWrapper] = None

# ⭐ HANDLER DE VALIDAÇÃO
async def validate_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    txt = json.loads(msg.value.decode())
    # SUA LÓGICA AQUI
    return True, "Validação OK"

# ⭐ HANDLER DE EXECUÇÃO
async def execute_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    txt = json.loads(msg.value.decode())
    # SUA LÓGICA AQUI
    return True, "Execução OK"

# ⭐ STARTUP
@app.on_event("startup")
async def startup_event():
    global kafka_wrapper
    consumers_config = {
        "validator": {
            "topics": [PRIVACY_VALIDATE_TOPIC],
            "group_id": "seu-servico-validate-group",
            "handler": validate_handler,
            "response_topic": PRIVACY_VALIDATE_RESPONSE_TOPIC,
        },
        "executor": {
            "topics": [PRIVACY_EXECUTE_TOPIC],
            "group_id": "seu-servico-execute-group",
            "handler": execute_handler,
            "response_topic": PRIVACY_EXECUTE_RESPONSE_TOPIC,
        },
    }
    kafka_wrapper = KafkaConsumerWrapper(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        consumers_config=consumers_config,
        client_id_prefix="seu-servico",
    )
    await kafka_wrapper.start()

# ⭐ SHUTDOWN
@app.on_event("shutdown")
async def shutdown_event():
    if kafka_wrapper:
        await kafka_wrapper.stop()
```

**Pronto! Só isso é necessário.** 🚀

---

## 10. Referências

### Documentação do Projeto

- [DOCUMENTACAO_ACADEMICA.md](./DOCUMENTACAO_ACADEMICA.md) - Arquitetura completa
- [DOCUMENTACAO_ACADEMICA_PARTE2.md](./DOCUMENTACAO_ACADEMICA_PARTE2.md) - Contratos de API
- [README.md](./README.md) - Visão geral do projeto

### Exemplos Reais

Consulte os serviços já integrados:

```bash
# Accounts (mais simples)
cat accounts/app/main.py

# Payments (com validação)
cat payments/app/main.py

# CRM (dados sensíveis)
cat crm/app/main.py

# Delivery (múltiplas tabelas)
cat delivery/app/main.py
```

### Contato

- **Autor**: Ramon Domingos
- **Email**: ramon.domingos@[instituicao].br
- **GitHub**: [@ramondomiingos](https://github.com/ramondomiingos)

---

<div align="center">

**🎓 Desenvolvido como parte da dissertação de mestrado em Sistemas Distribuídos**

*Versão 2.0 - Simplificada e baseada em implementações reais*

</div>
