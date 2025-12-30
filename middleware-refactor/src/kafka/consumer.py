import asyncio
import aiokafka
from .config import KAFKA_BROKER, KAFKA_GROUP_ID

async def get_kafka_consumer(topics):
    consumer = aiokafka.AIOKafkaConsumer(
        *topics,
        bootstrap_servers=KAFKA_BROKER,
        group_id=KAFKA_GROUP_ID,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    return consumer

async def consume_topic(topic, process_func):
    consumer = await get_kafka_consumer([topic])
    try:
        async for msg in consumer:
            await process_func(msg.value.decode("utf-8"))
    finally:
        await consumer.stop()