from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
import asyncio
from typing import List, Optional, Callable, Awaitable, Dict, Union
from aiokafka.structs import ConsumerRecord
import logging
import json

logger = logging.getLogger(__name__)

class KafkaConsumerWrapper:
    def __init__(
        self,
        bootstrap_servers: Union[str, List[str]],
        consumers_config: Dict[str, Dict],
        client_id_prefix: Optional[str] = None,
        auto_offset_reset: str = "latest",
        enable_auto_commit: bool = True,
        auto_commit_interval_ms: int = 5000,
        fetch_min_bytes: int = 1,
        fetch_max_wait_ms: int = 100,
        max_partition_fetch_bytes: int = 1048576,
        security_protocol: Optional[str] = None,
        ssl_context: Optional[object] = None,
        sasl_mechanism: Optional[str] = None,
        sasl_plain_username: Optional[str] = None,
        sasl_plain_password: Optional[str] = None,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.consumers_config = consumers_config
        self.client_id_prefix = client_id_prefix
        self.auto_offset_reset = auto_offset_reset
        self.enable_auto_commit = enable_auto_commit
        self.auto_commit_interval_ms = auto_commit_interval_ms
        self.fetch_min_bytes = fetch_min_bytes
        self.fetch_max_wait_ms = fetch_max_wait_ms
        self.max_partition_fetch_bytes = max_partition_fetch_bytes
        self.security_protocol = security_protocol if  security_protocol else 'PLAINTEXT'
        self.ssl_context = ssl_context
        self.sasl_mechanism = sasl_mechanism
        self.sasl_plain_username = sasl_plain_username
        self.sasl_plain_password = sasl_plain_password
        self._consumers: Dict[str, AIOKafkaConsumer] = {}
        self._consumer_tasks: Dict[str, asyncio.Task] = {}
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self):
        self._producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
        await self._producer.start()

        for consumer_name, config in self.consumers_config.items():
            topics = config.get("topics")
            handler = config.get("handler")
            response_topic = config.get("response_topic")

            if not topics or not handler or not response_topic:
                logger.error(f"Configuração incompleta para o consumidor '{consumer_name}'. Requer 'topics', 'handler' e 'response_topic'.")
                continue

            client_id = f"{self.client_id_prefix}-{consumer_name}" if self.client_id_prefix else consumer_name

            consumer = AIOKafkaConsumer(
                *topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=config.get("group_id"),
                client_id=client_id,
                auto_offset_reset=self.auto_offset_reset,
                enable_auto_commit=self.enable_auto_commit,
                auto_commit_interval_ms=self.auto_commit_interval_ms,
                fetch_min_bytes=self.fetch_min_bytes,
                fetch_max_wait_ms=self.fetch_max_wait_ms,
                max_partition_fetch_bytes=self.max_partition_fetch_bytes,
                security_protocol=self.security_protocol,
                ssl_context=self.ssl_context,
                sasl_mechanism=self.sasl_mechanism,
                sasl_plain_username=self.sasl_plain_username,
                sasl_plain_password=self.sasl_plain_password,
            )
            await consumer.start()
            self._consumers[consumer_name] = consumer
            self._consumer_tasks[consumer_name] = asyncio.create_task(self._consume_loop(consumer_name, consumer, handler, response_topic))

    async def _consume_loop(self, consumer_name: str, consumer: AIOKafkaConsumer, handler: Callable[[ConsumerRecord, AIOKafkaProducer], Awaitable[None]], response_topic: str):
        try:
            async for msg in consumer:
                logger.info(f"[Consumer {consumer_name}] Recebido: {msg.value.decode()} do tópico {msg.topic} na partição {msg.partition} com offset {msg.offset}")
                if handler:
                    try:
                        result, reason = await handler(msg, self._producer)
                        response_payload = {"result": result, "reason": reason ,"service_name": self.client_id_prefix }
                        response_payload.update(json.loads(msg.value.decode()))
                        await self._producer.send(response_topic, json.dumps(response_payload).encode('utf-8'))
                        logger.info(f"[Consumer {consumer_name}] Publicado resposta: {response_payload} no tópico {response_topic}")
                    except Exception as e:
                        logger.error(f"[Consumer {consumer_name}] Erro ao processar mensagem: {e}", exc_info=True)
                        # Lógica para lidar com erros no processamento da mensagem (ex: publicar em um tópico de erro)
        finally:
            await self.stop()

    async def stop(self):
        for task in self._consumer_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        for consumer in self._consumers.values():
            await consumer.stop()
        if self._producer:
            await self._producer.stop()