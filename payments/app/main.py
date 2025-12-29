
from .telemetry import configure_otel
from typing import Optional
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from datetime import datetime
import os
import logging
import json
from aiokafka.structs import ConsumerRecord
from aiokafka import AIOKafkaProducer
from .pacote_privacy import KafkaConsumerWrapper

DATABASE_URL = os.getenv("DATABASE_URL")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BROKER", "localhost:9092")
PRIVACY_VALIDATE_TOPIC = "privacy-validate-topic"
PRIVACY_VALIDATE_RESPONSE_TOPIC = "privacy-validate-response-topic"
PRIVACY_EXECUTE_TOPIC = "privacy-execute-topic"
PRIVACY_EXECUTE_RESPONSE_TOPIC = "privacy-execute-response-topic"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True)
    status = Column(String)
    amount = Column(Float)
    currency = Column(String)
    payment_method = Column(String)
    transaction_id = Column(String)
    payment_date = Column(DateTime)
    account_id = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI(title='payments-service')
configure_otel(app)

logger = logging.getLogger("payments")
logger.setLevel(logging.INFO)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Reduz o nível de log do Kafka
kafka_logger = logging.getLogger("aiokafka")
kafka_logger.setLevel(logging.WARNING)

class OrderCreate(BaseModel):
    order_id: str
    status: str
    amount: float
    currency: str
    payment_method: str
    transaction_id: str
    payment_date: datetime
    account_id: str

@app.post("/orders/")
def create_order(order: OrderCreate):
    db = SessionLocal()
    db_order = Order(**order.dict())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    logger.info(f"Order created: {db_order.order_id}")
    return db_order

@app.get("/orders/{order_id}")
def read_order(order_id: str):
    db = SessionLocal()
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if order is None:
        logger.warning(f"Order not found: {order_id}")
        raise HTTPException(status_code=404, detail="Order not found")
    logger.info(f"Order found: {order.order_id}")
    return order
    
@app.get("/orders/")
def list_orders():
    db = SessionLocal()
    orders = db.query(Order).all()
    logger.info(f"Orders listed. Count: {len(orders)}")
    return orders

kafka_wrapper: Optional[KafkaConsumerWrapper] = None

async def validate_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    """
    Valida se é possível deletar dados de pagamento.
    Regra de negócio: Não pode deletar se houver pagamentos pendentes.
    """
    txt = json.loads(msg.value.decode())
    logger.info(f"[Validate Handler] Processando validação para account_id: {txt.get('account_id')}")
    
    db = SessionLocal()
    try:
        # Busca todos os pedidos do usuário
        orders = db.query(Order).filter(Order.account_id == txt["account_id"]).all()
        
        if not orders:
            logger.info(f"[Validate Handler] Nenhum pedido encontrado para account_id: {txt['account_id']}")
            return True, "Nenhum pedido encontrado"
        
        # Verifica se há pedidos pendentes ou em processamento
        pending_orders = [o for o in orders if o.status in ["pending", "processing"]]
        
        if pending_orders:
            logger.warning(f"[Validate Handler] Existem {len(pending_orders)} pedidos pendentes. Exclusão negada.")
            return False, f"Existem {len(pending_orders)} pedidos pendentes. Não é possível deletar."
        
        logger.info(f"[Validate Handler] Validação OK. {len(orders)} pedidos podem ser deletados.")
        return True, f"Validação OK. {len(orders)} pedidos confirmados/cancelados."
        
    except Exception as e:
        logger.error(f"[Validate Handler] Erro ao validar: {e}")
        return False, f"Erro ao validar: {e}"
    finally:
        db.close()

async def execute_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    """
    Executa a deleção de dados de pagamento.
    """
    txt = json.loads(msg.value.decode())
    logger.info(f"[Execute Handler] Processando execução para account_id: {txt.get('account_id')}")
    
    db = SessionLocal()
    try:
        # Busca e deleta todos os pedidos do usuário
        orders = db.query(Order).filter(Order.account_id == txt["account_id"]).all()
        
        if not orders:
            logger.info(f"[Execute Handler] Nenhum pedido encontrado para deletar: {txt['account_id']}")
            return True, "Nenhum pedido para deletar"
        
        deleted_count = len(orders)
        for order in orders:
            db.delete(order)
        
        db.commit()
        logger.info(f"[Execute Handler] {deleted_count} pedidos deletados para account_id: {txt['account_id']}")
        return True, f"{deleted_count} pedidos deletados com sucesso"
        
    except Exception as e:
        db.rollback()
        logger.error(f"[Execute Handler] Erro ao executar deleção: {e}")
        return False, f"Erro ao executar: {e}"
    finally:
        db.close()

@app.on_event("startup")
async def startup_event():
    global kafka_wrapper
    consumers_config = {
        "validator": {
            "topics": [PRIVACY_VALIDATE_TOPIC],
            "group_id": "payment-validate-group",
            "handler": validate_handler,
            "response_topic": PRIVACY_VALIDATE_RESPONSE_TOPIC,
        },
        "executor": {
            "topics": [PRIVACY_EXECUTE_TOPIC],
            "group_id": "payment-execute-group",
            "handler": execute_handler,
            "response_topic": PRIVACY_EXECUTE_RESPONSE_TOPIC,
        },
    }
    kafka_wrapper = KafkaConsumerWrapper(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        consumers_config=consumers_config,
        client_id_prefix="payment",
    )
    await kafka_wrapper.start()
    app.state.kafka_wrapper = kafka_wrapper
    logger.info("[Startup] Kafka wrapper inicializado para Payments")

@app.on_event("shutdown")
async def shutdown_event():
    if kafka_wrapper:
        await kafka_wrapper.stop()
        logger.info("[Shutdown] Kafka wrapper encerrado")

