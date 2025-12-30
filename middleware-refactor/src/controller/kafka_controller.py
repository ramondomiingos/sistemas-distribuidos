from fastapi import APIRouter, BackgroundTasks
from src.kafka.producer import publish_message
from src.kafka.topics import PRIVACY_VALIDATE_TOPIC, PRIVACY_EXECUTE_TOPIC
from src.kafka.consumer import consume_topic
from src.kafka.topics import PRIVACY_VALIDATE_RESPONSE_TOPIC, PRIVACY_EXECUTE_RESPONSE_TOPIC
import asyncio

async def process_validate_response(msg):
    print(f"Received on {PRIVACY_VALIDATE_RESPONSE_TOPIC}: {msg}")

async def process_execute_response(msg):
    print(f"Received on {PRIVACY_EXECUTE_RESPONSE_TOPIC}: {msg}")

async def start_consumers():
    asyncio.create_task(consume_topic(PRIVACY_VALIDATE_RESPONSE_TOPIC, process_validate_response))
    asyncio.create_task(consume_topic(PRIVACY_EXECUTE_RESPONSE_TOPIC, process_execute_response))