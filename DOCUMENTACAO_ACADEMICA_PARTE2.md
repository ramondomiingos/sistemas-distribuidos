# Documentação Acadêmica - Parte 2: Contratos de API e Especificações

## 6. Contratos de API

### 6.1 Middleware API (REST)

**Base URL**: `http://localhost:8000`

#### 6.1.1 Criar Requisição de Privacidade

```http
POST /api/v1/privacy-requests/
Content-Type: application/json
```

**Request Body**:
```json
{
  "account_id": "string (required)",
  "request_type": "DELETE | EXPORT | ANONYMIZE (required)",
  "reason": "string (optional)"
}
```

**Response 201 Created**:
```json
{
  "id": 1,
  "account_id": "123456789",
  "request_type": "DELETE",
  "status": "PENDING",
  "reason": "Solicitação do titular conforme LGPD Art. 18",
  "created_at": "2025-12-29T10:00:00.000Z",
  "updated_at": "2025-12-29T10:00:00.000Z",
  "completed_at": null
}
```

**Response 400 Bad Request**:
```json
{
  "detail": "account_id é obrigatório"
}
```

**Response 422 Unprocessable Entity**:
```json
{
  "detail": [
    {
      "loc": ["body", "request_type"],
      "msg": "value is not a valid enumeration member",
      "type": "type_error.enum"
    }
  ]
}
```

---

#### 6.1.2 Listar Requisições de Privacidade

```http
GET /api/v1/privacy-requests/
```

**Query Parameters**:
- `skip`: int (default: 0) - Paginação
- `limit`: int (default: 100) - Itens por página
- `status`: string (optional) - Filtrar por status
- `account_id`: string (optional) - Filtrar por titular

**Response 200 OK**:
```json
[
  {
    "id": 1,
    "account_id": "123456789",
    "request_type": "DELETE",
    "status": "COMPLETED",
    "reason": "Solicitação do titular",
    "created_at": "2025-12-29T10:00:00.000Z",
    "updated_at": "2025-12-29T10:02:30.000Z",
    "completed_at": "2025-12-29T10:02:30.000Z"
  },
  {
    "id": 2,
    "account_id": "987654321",
    "request_type": "DELETE",
    "status": "FAILED",
    "reason": "Titular solicitou exclusão",
    "created_at": "2025-12-29T11:00:00.000Z",
    "updated_at": "2025-12-29T11:00:45.000Z",
    "completed_at": null
  }
]
```

---

#### 6.1.3 Obter Requisição por ID

```http
GET /api/v1/privacy-requests/{request_id}
```

**Path Parameters**:
- `request_id`: int (required)

**Response 200 OK**:
```json
{
  "id": 1,
  "account_id": "123456789",
  "request_type": "DELETE",
  "status": "COMPLETED",
  "reason": "Solicitação do titular",
  "created_at": "2025-12-29T10:00:00.000Z",
  "updated_at": "2025-12-29T10:02:30.000Z",
  "completed_at": "2025-12-29T10:02:30.000Z",
  "services": [
    {
      "service_name": "accounts",
      "validation_status": "APPROVED",
      "validation_message": "Usuário pode ser deletado",
      "execution_status": "COMPLETED",
      "execution_message": "1 usuário deletado"
    },
    {
      "service_name": "payments",
      "validation_status": "APPROVED",
      "validation_message": "Nenhum pagamento pendente",
      "execution_status": "COMPLETED",
      "execution_message": "5 pedidos deletados"
    },
    {
      "service_name": "crm",
      "validation_status": "APPROVED",
      "validation_message": "Dados sensíveis podem ser removidos",
      "execution_status": "COMPLETED",
      "execution_message": "1 registro de UserInfo deletado"
    },
    {
      "service_name": "delivery",
      "validation_status": "APPROVED",
      "validation_message": "Nenhuma entrega em trânsito",
      "execution_status": "COMPLETED",
      "execution_message": "3 entregas deletadas"
    }
  ]
}
```

**Response 404 Not Found**:
```json
{
  "detail": "Requisição de privacidade não encontrada"
}
```

---

#### 6.1.4 Registrar Serviço

```http
POST /api/v1/services/
Content-Type: application/json
```

**Request Body**:
```json
{
  "service_name": "string (required, unique)",
  "description": "string (optional)"
}
```

**Response 201 Created**:
```json
{
  "id": 1,
  "service_name": "accounts",
  "description": "Serviço de gerenciamento de usuários",
  "created_at": "2025-12-29T09:00:00.000Z",
  "updated_at": "2025-12-29T09:00:00.000Z"
}
```

**Response 400 Bad Request**:
```json
{
  "detail": "Serviço 'accounts' já está registrado"
}
```

---

#### 6.1.5 Listar Serviços Registrados

```http
GET /api/v1/services/
```

**Response 200 OK**:
```json
[
  {
    "id": 1,
    "service_name": "accounts",
    "description": "Serviço de gerenciamento de usuários",
    "created_at": "2025-12-29T09:00:00.000Z",
    "updated_at": "2025-12-29T09:00:00.000Z"
  },
  {
    "id": 2,
    "service_name": "payments",
    "description": "Serviço de processamento de pagamentos",
    "created_at": "2025-12-29T09:00:00.000Z",
    "updated_at": "2025-12-29T09:00:00.000Z"
  },
  {
    "id": 3,
    "service_name": "crm",
    "description": "Serviço de dados sensíveis de clientes",
    "created_at": "2025-12-29T09:00:00.000Z",
    "updated_at": "2025-12-29T09:00:00.000Z"
  },
  {
    "id": 4,
    "service_name": "delivery",
    "description": "Serviço de logística e entregas",
    "created_at": "2025-12-29T09:00:00.000Z",
    "updated_at": "2025-12-29T09:00:00.000Z"
  }
]
```

---

### 6.2 Mensagens Kafka (Event-Driven)

#### 6.2.1 Mensagem de Validação

**Tópico**: `privacy-validate-topic`  
**Produtor**: Middleware  
**Consumidores**: Accounts, Payments, CRM, Delivery

**Schema**:
```json
{
  "request_id": "string (UUID)",
  "account_id": "string",
  "request_type": "DELETE | EXPORT | ANONYMIZE",
  "timestamp": "string (ISO 8601)",
  "metadata": {
    "correlation_id": "string",
    "trace_id": "string (OpenTelemetry)"
  }
}
```

**Exemplo**:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "account_id": "123456789",
  "request_type": "DELETE",
  "timestamp": "2025-12-29T10:00:00.000Z",
  "metadata": {
    "correlation_id": "corr-12345",
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
  }
}
```

---

#### 6.2.2 Resposta de Validação

**Tópico**: `privacy-validate-response-topic`  
**Produtores**: Accounts, Payments, CRM, Delivery  
**Consumidor**: Middleware

**Schema**:
```json
{
  "request_id": "string (UUID)",
  "account_id": "string",
  "service_name": "string",
  "result": "boolean",
  "reason": "string",
  "timestamp": "string (ISO 8601)",
  "metadata": {
    "processing_time_ms": "number",
    "trace_id": "string"
  }
}
```

**Exemplo (Aprovado)**:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "account_id": "123456789",
  "service_name": "payments",
  "result": true,
  "reason": "Validação OK. 3 pedidos encontrados, todos com status 'confirmed'",
  "timestamp": "2025-12-29T10:00:05.234Z",
  "metadata": {
    "processing_time_ms": 234,
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
  }
}
```

**Exemplo (Rejeitado)**:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "account_id": "987654321",
  "service_name": "payments",
  "result": false,
  "reason": "Não é possível deletar: 2 pagamentos com status 'pending'",
  "timestamp": "2025-12-29T11:00:05.120Z",
  "metadata": {
    "processing_time_ms": 120,
    "trace_id": "5cf03g4688c45db7b4df030e1f1f5847"
  }
}
```

---

#### 6.2.3 Mensagem de Execução

**Tópico**: `privacy-execute-topic`  
**Produtor**: Middleware  
**Consumidores**: Accounts, Payments, CRM, Delivery

**Schema**:
```json
{
  "request_id": "string (UUID)",
  "account_id": "string",
  "request_type": "DELETE | EXPORT | ANONYMIZE",
  "timestamp": "string (ISO 8601)",
  "metadata": {
    "correlation_id": "string",
    "trace_id": "string"
  }
}
```

**Exemplo**:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "account_id": "123456789",
  "request_type": "DELETE",
  "timestamp": "2025-12-29T10:00:10.000Z",
  "metadata": {
    "correlation_id": "corr-12345",
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
  }
}
```

---

#### 6.2.4 Resposta de Execução

**Tópico**: `privacy-execute-response-topic`  
**Produtores**: Accounts, Payments, CRM, Delivery  
**Consumidor**: Middleware

**Schema**:
```json
{
  "request_id": "string (UUID)",
  "account_id": "string",
  "service_name": "string",
  "result": "boolean",
  "reason": "string",
  "timestamp": "string (ISO 8601)",
  "metadata": {
    "records_deleted": "number",
    "processing_time_ms": "number",
    "trace_id": "string"
  }
}
```

**Exemplo (Sucesso)**:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "account_id": "123456789",
  "service_name": "payments",
  "result": true,
  "reason": "Deleção concluída com sucesso",
  "timestamp": "2025-12-29T10:00:15.567Z",
  "metadata": {
    "records_deleted": 5,
    "processing_time_ms": 567,
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
  }
}
```

**Exemplo (Falha)**:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "account_id": "123456789",
  "service_name": "payments",
  "result": false,
  "reason": "Erro ao deletar: Database connection timeout",
  "timestamp": "2025-12-29T10:00:70.000Z",
  "metadata": {
    "records_deleted": 0,
    "processing_time_ms": 60000,
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
  }
}
```

---

### 6.3 Microsserviços - APIs Internas

Cada microsserviço expõe endpoints REST para suas operações de negócio. Aqui apresentamos os endpoints relevantes:

#### 6.3.1 Accounts Service (Porta 5001)

```http
POST /users/
GET /users/
GET /users/{account_id}
DELETE /users/{account_id}  # NÃO usar diretamente - usar Middleware
```

**Modelo User**:
```json
{
  "id": 1,
  "account_id": "123456789",
  "name": "João Silva",
  "email": "joao@example.com",
  "created_at": "2025-01-15T10:00:00Z"
}
```

---

#### 6.3.2 Payments Service (Porta 5002)

```http
POST /orders/
GET /orders/
GET /orders/{order_id}
GET /orders/account/{account_id}
```

**Modelo Order**:
```json
{
  "id": 1,
  "order_id": "ORD-2025-001",
  "account_id": "123456789",
  "status": "confirmed",
  "amount": 199.90,
  "payment_method": "credit_card",
  "created_at": "2025-01-15T14:30:00Z"
}
```

**Status Possíveis**: `pending`, `processing`, `confirmed`, `cancelled`, `refunded`, `failed`

---

#### 6.3.3 CRM Service (Porta 5003)

```http
POST /user-info/
GET /user-info/
GET /user-info/{account_id}
```

**Modelo UserInfo**:
```json
{
  "id": 1,
  "account_id": "123456789",
  "birth_day": "1990-05-15",
  "religion": "Católica",
  "created_at": "2025-01-15T10:05:00Z"
}
```

---

#### 6.3.4 Delivery Service (Porta 5004)

```http
POST /deliveries/
GET /deliveries/
GET /deliveries/{tracking_code}
GET /deliveries/customer/{customer_id}
```

**Modelo Delivery**:
```json
{
  "id": 1,
  "order_id": "ORD-2025-001",
  "customer_id": "123456789",
  "status": "delivered",
  "tracking_code": "BR123456789XX",
  "shipping_address": "Rua Exemplo, 123 - São Paulo/SP",
  "created_at": "2025-01-16T09:00:00Z",
  "delivered_at": "2025-01-20T15:30:00Z"
}
```

**Status Possíveis**: `pending`, `in_transit`, `out_for_delivery`, `delivered`, `failed`, `cancelled`, `returned`

---

## 7. Biblioteca de Integração (pacote_privacy)

### 7.1 Arquitetura da Biblioteca

A biblioteca `pacote_privacy` é o componente central que facilita a integração de microsserviços existentes com o framework de privacidade. Ela abstrai toda a complexidade de conexão com Kafka, gerenciamento de consumers e publicação de respostas.

### 7.2 Interface da Biblioteca

#### 7.2.1 KafkaConsumerWrapper

**Inicialização**:
```python
from pacote_privacy import KafkaConsumerWrapper

# Handlers customizados do serviço
async def validate_handler(account_id: str, request_id: str) -> tuple[bool, str]:
    """
    Valida se o serviço pode executar a exclusão.
    
    Args:
        account_id: ID do titular dos dados
        request_id: ID da requisição de privacidade
        
    Returns:
        (can_delete: bool, reason: str)
    """
    # Implementar regras de negócio
    pass

async def execute_handler(account_id: str, request_id: str) -> tuple[bool, str]:
    """
    Executa a exclusão dos dados.
    
    Args:
        account_id: ID do titular dos dados
        request_id: ID da requisição de privacidade
        
    Returns:
        (success: bool, message: str)
    """
    # Implementar deleção
    pass

# Configuração
consumers_config = {
    "validator": {
        "topics": ["privacy-validate-topic"],
        "group_id": "meu-servico-validate-group",
        "handler": validate_handler,
        "response_topic": "privacy-validate-response-topic"
    },
    "executor": {
        "topics": ["privacy-execute-topic"],
        "group_id": "meu-servico-execute-group",
        "handler": execute_handler,
        "response_topic": "privacy-execute-response-topic"
    }
}

# Instanciar wrapper
kafka_wrapper = KafkaConsumerWrapper(
    bootstrap_servers=os.getenv("KAFKA_BROKER", "kafka:9092"),
    consumers_config=consumers_config,
    client_id_prefix="meu-servico",
    auto_offset_reset="latest"
)
```

**Lifecycle Management**:
```python
from fastapi import FastAPI

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    await kafka_wrapper.start()
    print("Kafka wrapper inicializado")

@app.on_event("shutdown")
async def shutdown_event():
    await kafka_wrapper.stop()
    print("Kafka wrapper encerrado")
```

---

### 7.3 Implementação de Handlers

#### 7.3.1 Exemplo: Payments Service

**validate_handler**:
```python
from sqlalchemy import select
from app.database import get_db
from app.models import Order

async def validate_handler(account_id: str, request_id: str) -> tuple[bool, str]:
    """
    Valida se há pagamentos pendentes que impedem a exclusão.
    
    Regra de Negócio:
    - Bloqueia se houver pagamentos com status 'pending' ou 'processing'
    - Permite se todos os pagamentos forem 'confirmed', 'cancelled', 'refunded', 'failed'
    """
    db = next(get_db())
    
    try:
        # Buscar todos os pedidos do account_id
        stmt = select(Order).where(Order.account_id == account_id)
        result = db.execute(stmt)
        orders = result.scalars().all()
        
        if not orders:
            return True, f"Nenhum pedido encontrado para account_id {account_id}"
        
        # Verificar status bloqueadores
        blocking_statuses = ["pending", "processing"]
        blocked_orders = [
            order for order in orders 
            if order.status in blocking_statuses
        ]
        
        if blocked_orders:
            order_ids = [o.order_id for o in blocked_orders]
            return False, (
                f"Não é possível deletar: {len(blocked_orders)} pagamento(s) "
                f"com status pendente ou em processamento. "
                f"Order IDs: {', '.join(order_ids)}"
            )
        
        return True, (
            f"Validação OK. {len(orders)} pedido(s) encontrado(s), "
            f"todos com status permitido para exclusão"
        )
        
    except Exception as e:
        return False, f"Erro na validação: {str(e)}"
    finally:
        db.close()
```

**execute_handler**:
```python
async def execute_handler(account_id: str, request_id: str) -> tuple[bool, str]:
    """
    Executa a exclusão de todos os pedidos do account_id.
    """
    db = next(get_db())
    
    try:
        # Buscar pedidos
        stmt = select(Order).where(Order.account_id == account_id)
        result = db.execute(stmt)
        orders = result.scalars().all()
        
        if not orders:
            return True, f"Nenhum pedido para deletar (account_id: {account_id})"
        
        # Deletar em transação atômica
        count = len(orders)
        for order in orders:
            db.delete(order)
        
        db.commit()
        
        return True, f"Deleção concluída: {count} pedido(s) removido(s)"
        
    except Exception as e:
        db.rollback()
        return False, f"Erro na deleção: {str(e)}"
    finally:
        db.close()
```

---

#### 7.3.2 Exemplo: Delivery Service

**validate_handler**:
```python
async def validate_handler(account_id: str, request_id: str) -> tuple[bool, str]:
    """
    Valida se há entregas em trânsito que impedem a exclusão.
    
    Regra de Negócio:
    - Bloqueia se houver entregas com status 'out_for_delivery', 'pending', 'in_transit'
    - Permite se todas as entregas forem 'delivered', 'cancelled', 'failed', 'returned'
    """
    db = next(get_db())
    
    try:
        stmt = select(Delivery).where(Delivery.customer_id == account_id)
        result = db.execute(stmt)
        deliveries = result.scalars().all()
        
        if not deliveries:
            return True, f"Nenhuma entrega encontrada para customer_id {account_id}"
        
        # Verificar status bloqueadores
        blocking_statuses = ["out_for_delivery", "pending", "in_transit"]
        blocked_deliveries = [
            d for d in deliveries 
            if d.status in blocking_statuses
        ]
        
        if blocked_deliveries:
            tracking_codes = [d.tracking_code for d in blocked_deliveries]
            return False, (
                f"Não é possível deletar: {len(blocked_deliveries)} entrega(s) "
                f"em trânsito ou pendente. "
                f"Tracking codes: {', '.join(tracking_codes)}"
            )
        
        return True, (
            f"Validação OK. {len(deliveries)} entrega(s) encontrada(s), "
            f"todas finalizadas"
        )
        
    except Exception as e:
        return False, f"Erro na validação: {str(e)}"
    finally:
        db.close()
```

**execute_handler**:
```python
async def execute_handler(account_id: str, request_id: str) -> tuple[bool, str]:
    """
    Executa a exclusão de todas as entregas do customer_id.
    """
    db = next(get_db())
    
    try:
        stmt = select(Delivery).where(Delivery.customer_id == account_id)
        result = db.execute(stmt)
        deliveries = result.scalars().all()
        
        if not deliveries:
            return True, f"Nenhuma entrega para deletar (customer_id: {account_id})"
        
        count = len(deliveries)
        for delivery in deliveries:
            db.delete(delivery)
        
        db.commit()
        
        return True, f"Deleção concluída: {count} entrega(s) removida(s)"
        
    except Exception as e:
        db.rollback()
        return False, f"Erro na deleção: {str(e)}"
    finally:
        db.close()
```

---

### 7.4 Configuração de Offset

**Parâmetro Critical: `auto_offset_reset`**

```python
auto_offset_reset: str = "latest"  # ou "earliest"
```

**Implicações**:

| Valor | Comportamento | Caso de Uso |
|-------|--------------|-------------|
| `earliest` | Consome desde o início do tópico | Reprocessamento, recuperação de desastres |
| `latest` | Consome apenas mensagens novas | **Produção** (evita duplicatas) |

**Justificativa para `latest`**:
- ✅ Evita processamento duplicado ao reiniciar serviços
- ✅ Consumidores entram no grupo já sincronizados
- ✅ Mensagens antigas já foram processadas por outras instâncias
- ❌ Pode perder mensagens se o serviço estiver offline durante publicação

**Quando usar `earliest`**:
- Ambiente de desenvolvimento/teste
- Reprocessamento intencional
- Serviço novo entrando no ecossistema

---

*[Continua na Parte 3 com Fluxogramas e Diagramas...]*
