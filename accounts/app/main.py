
from math import e
from .telemetry import configure_otel
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
import asyncio
from aiokafka.structs import ConsumerRecord
from aiokafka import AIOKafkaProducer
import os
import logging
import json
from .pacote_privacy import KafkaConsumerWrapper
from prometheus_fastapi_instrumentator import Instrumentator


DATABASE_URL = os.getenv("DATABASE_URL")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BROKER", "localhost:9092")
PRIVACY_VALIDATE_TOPIC = "privacy-validate-topic"
PRIVACY_VALIDATE_RESPONSE_TOPIC = "privacy-validate-response-topic"
PRIVACY_EXECUTE_TOPIC = "privacy-execute-topic"
PRIVACY_EXECUTE_RESPONSE_TOPIC = "privacy-execute-response-topic"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    account_id = Column(String, unique=True, index=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title='accounts-service')
configure_otel(app)


logger = logging.getLogger("accounts")
logger.setLevel(logging.INFO)  # Garante nível INFO


root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Reduz o nível de log do Kafka
kafka_logger = logging.getLogger("aiokafka")
kafka_logger.setLevel(logging.WARNING)  


class UserCreate(BaseModel):
    name: str
    email: str
    account_id: str



@app.post("/users/")
def create_user(user: UserCreate):
    db = SessionLocal()
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"User created: {db_user.account_id}")  # Log the user creation
    return db_user

@app.get("/users/{account_id}")
def read_user(account_id: str):
    db = SessionLocal()
    user = db.query(User).filter(User.account_id == account_id).first()
    if user is None:
        logger.warning(f"User not found: {account_id}") # Log user not found
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User found {user.id},{ user.account_id}, {user.email}, {user.name} ")  # Log the user found
    return user

@app.get("/users/")
def list_users():
    db = SessionLocal()
    users = db.query(User).all()
    logger.info(f"Users listed. Count: {len(users)}")
    return users

kafka_wrapper: Optional[KafkaConsumerWrapper] = None

async def validate_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    txt = json.loads(msg.value.decode())
    logger.info(f"[Validate Handler] Processando: {txt}")
    # Sua lgica aqui
    db = SessionLocal()
    user =  db.query(User).filter(User.account_id == txt["account_id"]).first()
    if user is None:
        logger.warning(f"[Validate Handler] Usuário não encontrado: {txt['account_id']}")
        return True, "Usuário não encontrado" 
    logger.info(f"user find: {user}")
    return True, "Validação OK"

async def execute_handler(msg: ConsumerRecord, producer: AIOKafkaProducer):
    txt = json.loads(msg.value.decode())
    logger.info(f"[Execute Handler] Processando: {txt}")
    # Sua lógica de execução aqui
    db = SessionLocal()
    try:
        delete_query =  db.query(User).filter(User.account_id == txt["account_id"]).first()
        if delete_query is None:
            logger.info(f"[Execute Handler] Usuário não encontrado: {txt['account_id']}")
            return True, "Usuário não encontrado"
        db.delete(delete_query)
        db.commit()
       
        logger.info(f"Delete user with account_id: {txt['account_id']}")
        return True, "Execução concluída"
    except Exception as e:
        logger.error(f"[Execute Handler] Erro ao executar: {e}")
        return False, f"Erro ao executar {e}"
    

@app.on_event("startup")
async def startup_event():
    global kafka_wrapper
    consumers_config = {
        "validator": {
            "topics": [PRIVACY_VALIDATE_TOPIC],
            "group_id": "accounts-validate-group",
            "handler": validate_handler,
            "response_topic": PRIVACY_VALIDATE_RESPONSE_TOPIC,
        },
        "executor": {
            "topics": [PRIVACY_EXECUTE_TOPIC],
            "group_id": "accounts-execute-group",
            "handler": execute_handler,
            "response_topic": PRIVACY_EXECUTE_RESPONSE_TOPIC,
        },
    }
    kafka_wrapper = KafkaConsumerWrapper(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        consumers_config=consumers_config,
        client_id_prefix="account",
    )
    await kafka_wrapper.start()
    app.state.kafka_wrapper = kafka_wrapper 

@app.on_event("shutdown")
async def shutdown_event():
    if kafka_wrapper:
        await kafka_wrapper.stop()
