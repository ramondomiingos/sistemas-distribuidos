from fastapi import FastAPI, BackgroundTasks

from typing import List, Optional
import uuid
import json
from .schemas import OperationsExecution
from .io.routers import router 
import os
import logging
from .telemetry import configure_otel
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.admin import NewTopic,AIOKafkaAdminClient

import os
import asyncio

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BROKER", "localhost:9092")


# Inicializa o FastAPI
app = FastAPI()
app.include_router(router, prefix="/api/v1", tags=["privacy_request"])
configure_otel(app)


logger = logging.getLogger("middleware-service")
logger.setLevel(logging.INFO)  # Garante nível INFO


root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Reduz o nível de log do Kafka
kafka_logger = logging.getLogger("aiokafka")
kafka_logger.setLevel(logging.WARNING)  

producer = None
consumer_task = None

# Função para garantir que o tópico exista
async def ensure_topic():
    admin = AIOKafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await admin.start()
    try:
        existing_topics = await admin.list_topics()
        for TOPIC_NAME in ["privacy-validate-topic", "privacy-validate-response-topic", "privacy-execute-topic", "privacy-execute-response-topic"]:
            if TOPIC_NAME not in existing_topics:
                topic = NewTopic(name=TOPIC_NAME, num_partitions=1, replication_factor=1)
                await admin.create_topics([topic])
    finally:
        await admin.close()


# Consumer Kafka (roda em segundo plano)
async def consumeValidateTopic():
    consumer = AIOKafkaConsumer(
        'privacy-validate-response-topic',
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="middleware-group"
    )
    await consumer.start()
    try:
        async for msg in consumer:
            txt = json.loads(msg.value.decode())
            request_id = txt.get("request_id")
            account_id = txt.get("account_id")
            logger.info(f"[Validate Response Consumer] Recebido: {txt} do tópico {msg.topic}")
            producer = app.state.producer
            json_body = {
            "request_id": request_id,
            "account_id": account_id,
            "operation": OperationsExecution.PERFORM_DELETE.value
            }

            headers = [["operation", OperationsExecution.PERFORM_DELETE.value], ["x-request-id",  request_id]]
            [(k, v.encode()) for k, v in headers]
            
            await producer.send_and_wait('privacy-execute-topic', json.dumps(json_body).encode(), headers= [(k, v.encode()) for k, v in headers])
            logger.info(f"[Producer] Enviado: {json_body} para o tópico privacy-execute-topic")
    except Exception as e:
        logger.error(f"[Validate Response Consumer] Erro ao processar mensagem: {e}")   
    finally:
        logger.info(f"[Validate Response Consumer] Parando o consumidor privacy-validate-response-topic")
        await consumer.stop()

async def consumeExecuteTopic():
    consumer = AIOKafkaConsumer(
        'privacy-execute-response-topic',
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="middleware-group"
    )
    await consumer.start()
    try:
        async for msg in consumer:
            logger.info(f"[Execute Response Consumer] Recebido: {msg.value.decode()} do tópico {msg.topic}")
           
    finally:
        logger.info(f"[Validate Response Consumer] Parando o consumidor privacy-execute-response-topic")

        await consumer.stop()

@app.on_event("startup")
async def startup_event():
    await ensure_topic()

    # Inicializa o producer e armazena no app.state
    app.state.producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await app.state.producer.start()

    # Inicia o consumidor em background
    app.state.consumer_task =asyncio.gather(
        consumeValidateTopic(),
        consumeExecuteTopic())

@app.on_event("shutdown")
async def shutdown_event():
    await app.state.producer.stop()
    app.state.consumer_task.cancel()
    try:
        await app.state.consumer_task
    except asyncio.CancelledError:
        pass