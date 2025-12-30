
from .telemetry import configure_otel
from typing import Optional
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, DateTime
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

class Delivery(Base):
    __tablename__ = "deliveries"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True)
    status = Column(String)
    tracking_code = Column(String)
    estimated_delivery = Column(DateTime)
    carrier = Column(String)
    customer_id = Column(String)
    shipping_address = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI(title='delivery-service')
configure_otel(app)

logger = logging.getLogger("delivery")
logger.setLevel(logging.INFO)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Reduz o nível de log do Kafka
kafka_logger = logging.getLogger("aiokafka")
kafka_logger.setLevel(logging.WARNING)

class DeliveryCreate(BaseModel):
    order_id: str
    status: str
    tracking_code: str
    estimated_delivery: datetime
    carrier: str
    customer_id: str
    shipping_address: str

@app.post("/delivery/")
def create_delivery(delivery: DeliveryCreate):
    db = SessionLocal()
    db_delivery = Delivery(**delivery.dict())
    db.add(db_delivery)
    db.commit()
    db.refresh(db_delivery)
    logger.info(f"Delivery created: {db_delivery.order_id}")
    return db_delivery

@app.get("/delivery/{order_id}")
def read_delivery(order_id: str):
    db = SessionLocal()
    delivery = db.query(Delivery).filter(Delivery.order_id == order_id).first()
    if delivery is None:
        logger.warning(f"Delivery not found: {order_id}")
        raise HTTPException(status_code=404, detail="Delivery not found")
    logger.info(f"Delivery found: {delivery.order_id}")
    return delivery

@app.get("/delivery/")
def list_deliveries():
    db = SessionLocal()
    deliveries = db.query(Delivery).all()
    logger.info(f"Deliveries listed. Count: {len(deliveries)}")
    return deliveries

kafka_wrapper: Optional[KafkaConsumerWrapper] = None

async def validate_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    """
    Valida se é possível deletar dados de entrega.
    Regra de negócio: Não pode deletar se houver entregas em trânsito.
    """
    txt = json.loads(msg.value.decode())
    logger.info(f"[Validate Handler] Processando validação para customer_id: {txt.get('account_id')}")
    
    db = SessionLocal()
    try:
        # Busca todas as entregas do cliente
        deliveries = db.query(Delivery).filter(Delivery.customer_id == txt["account_id"]).all()
        
        if not deliveries:
            logger.info(f"[Validate Handler] Nenhuma entrega encontrada para customer_id: {txt['account_id']}")
            return True, "Nenhuma entrega encontrada"
        
        # Verifica se há entregas em trânsito
        in_transit = [d for d in deliveries if d.status in ["out_for_delivery", "pending", "in_transit"]]
        
        if in_transit:
            logger.warning(f"[Validate Handler] Existem {len(in_transit)} entregas em trânsito. Exclusão negada.")
            return False, f"Existem {len(in_transit)} entregas em trânsito. Não é possível deletar."
        
        logger.info(f"[Validate Handler] Validação OK. {len(deliveries)} entregas podem ser deletadas.")
        return True, f"Validação OK. {len(deliveries)} entregas finalizadas."
        
    except Exception as e:
        logger.error(f"[Validate Handler] Erro ao validar: {e}")
        return False, f"Erro ao validar: {e}"
    finally:
        db.close()

async def execute_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    """
    Executa a deleção de dados de entrega.
    """
    txt = json.loads(msg.value.decode())
    logger.info(f"[Execute Handler] Processando execução para customer_id: {txt.get('account_id')}")
    
    db = SessionLocal()
    try:
        # Busca e deleta todas as entregas do cliente
        deliveries = db.query(Delivery).filter(Delivery.customer_id == txt["account_id"]).all()
        
        if not deliveries:
            logger.info(f"[Execute Handler] Nenhuma entrega encontrada para deletar: {txt['account_id']}")
            return True, "Nenhuma entrega para deletar"
        
        deleted_count = len(deliveries)
        for delivery in deliveries:
            db.delete(delivery)
        
        db.commit()
        logger.info(f"[Execute Handler] {deleted_count} entregas deletadas para customer_id: {txt['account_id']}")
        return True, f"{deleted_count} entregas deletadas com sucesso"
        
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
            "group_id": "delivery-validate-group",
            "handler": validate_handler,
            "response_topic": PRIVACY_VALIDATE_RESPONSE_TOPIC,
        },
        "executor": {
            "topics": [PRIVACY_EXECUTE_TOPIC],
            "group_id": "delivery-execute-group",
            "handler": execute_handler,
            "response_topic": PRIVACY_EXECUTE_RESPONSE_TOPIC,
        },
    }
    kafka_wrapper = KafkaConsumerWrapper(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        consumers_config=consumers_config,
        client_id_prefix="delivery",
    )
    await kafka_wrapper.start()
    app.state.kafka_wrapper = kafka_wrapper
    logger.info("[Startup] Kafka wrapper inicializado para Delivery")

@app.on_event("shutdown")
async def shutdown_event():
    if kafka_wrapper:
        await kafka_wrapper.stop()
        logger.info("[Shutdown] Kafka wrapper encerrado")
