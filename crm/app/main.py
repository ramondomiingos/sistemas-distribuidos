from .telemetry import configure_otel
from typing import Optional
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
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

class UserInfo(Base):
    __tablename__ = "user_info"
    id = Column(Integer, primary_key=True, index=True)
    birth_day = Column(Date)
    account_id = Column(String, unique=True, index=True)
    religion = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI(title='crm-service')
configure_otel(app)

logger = logging.getLogger("crm")
logger.setLevel(logging.INFO)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Reduz o nível de log do Kafka
kafka_logger = logging.getLogger("aiokafka")
kafka_logger.setLevel(logging.WARNING)

class UserInfoCreate(BaseModel):
    birth_day: str
    account_id: str
    religion: str

@app.post("/info-users/")
def create_user_info(user_info: UserInfoCreate):
    db = SessionLocal()
    db_user_info = UserInfo(**user_info.dict())
    db.add(db_user_info)
    db.commit()
    db.refresh(db_user_info)
    logger.info(f"User info created: {db_user_info.account_id}")
    return db_user_info

@app.get("/info-users/{account_id}")
def read_user_info(account_id: str):
    db = SessionLocal()
    user_info = db.query(UserInfo).filter(UserInfo.account_id == account_id).first()
    if user_info is None:
        logger.warning(f"User info not found: {account_id}")
        raise HTTPException(status_code=404, detail="User info not found")
    logger.info(f"User info found: {user_info.account_id}")
    return user_info

@app.get("/info-users/")
def list_user_info():
    db = SessionLocal()
    user_info = db.query(UserInfo).all()
    logger.info(f"User info listed. Count: {len(user_info)}")
    return user_info

kafka_wrapper: Optional[KafkaConsumerWrapper] = None

async def validate_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    """
    Valida se é possível deletar dados sensíveis do CRM.
    CRM geralmente pode deletar dados sem restrições (dados sensíveis devem ser removíveis).
    """
    txt = json.loads(msg.value.decode())
    logger.info(f"[Validate Handler] Processando validação para account_id: {txt.get('account_id')}")
    
    db = SessionLocal()
    try:
        # Busca informações do usuário
        user_info = db.query(UserInfo).filter(UserInfo.account_id == txt["account_id"]).first()
        
        if not user_info:
            logger.info(f"[Validate Handler] Nenhuma informação CRM encontrada para account_id: {txt['account_id']}")
            return True, "Nenhuma informação CRM encontrada"
        
        logger.info(f"[Validate Handler] Validação OK. Informação CRM pode ser deletada.")
        return True, "Validação OK. Dados sensíveis podem ser removidos."
        
    except Exception as e:
        logger.error(f"[Validate Handler] Erro ao validar: {e}")
        return False, f"Erro ao validar: {e}"
    finally:
        db.close()

async def execute_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    """
    Executa a deleção de dados sensíveis do CRM.
    """
    txt = json.loads(msg.value.decode())
    logger.info(f"[Execute Handler] Processando execução para account_id: {txt.get('account_id')}")
    
    db = SessionLocal()
    try:
        # Busca e deleta informações do usuário
        user_info = db.query(UserInfo).filter(UserInfo.account_id == txt["account_id"]).first()
        
        if not user_info:
            logger.info(f"[Execute Handler] Nenhuma informação CRM encontrada para deletar: {txt['account_id']}")
            return True, "Nenhuma informação CRM para deletar"
        
        db.delete(user_info)
        db.commit()
        
        logger.info(f"[Execute Handler] Informações CRM deletadas para account_id: {txt['account_id']}")
        return True, "Informações CRM deletadas com sucesso"
        
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
            "group_id": "crm-validate-group",
            "handler": validate_handler,
            "response_topic": PRIVACY_VALIDATE_RESPONSE_TOPIC,
        },
        "executor": {
            "topics": [PRIVACY_EXECUTE_TOPIC],
            "group_id": "crm-execute-group",
            "handler": execute_handler,
            "response_topic": PRIVACY_EXECUTE_RESPONSE_TOPIC,
        },
    }
    kafka_wrapper = KafkaConsumerWrapper(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        consumers_config=consumers_config,
        client_id_prefix="crm",
    )
    await kafka_wrapper.start()
    app.state.kafka_wrapper = kafka_wrapper
    logger.info("[Startup] Kafka wrapper inicializado para CRM")

@app.on_event("shutdown")
async def shutdown_event():
    if kafka_wrapper:
        await kafka_wrapper.stop()
        logger.info("[Shutdown] Kafka wrapper encerrado")
