# src/services/kafka_service.py
import json
import logging
import asyncio
from typing import Dict, Any, Callable, Coroutine, Optional
import aiokafka

from src.controller.privacy_request_service import create_register_response
from src.kafka.config import KAFKA_BROKER, KAFKA_GROUP_ID
from src.kafka.topics import (
    PRIVACY_VALIDATE_TOPIC,
    PRIVACY_VALIDATE_RESPONSE_TOPIC,
    PRIVACY_EXECUTE_TOPIC,
    PRIVACY_EXECUTE_RESPONSE_TOPIC,
    ALL_TOPICS
)
from src.models.privacy_request_service import PrivacyRequestService
from src.schemas.privacy_request_service import PrivacyRequestServiceCreate

logger = logging.getLogger(__name__)

class KafkaService:
    _instance: Optional['KafkaService'] = None

    @classmethod
    def get_instance(cls) -> 'KafkaService':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if self._instance is not None:
            raise RuntimeError("Use get_instance() instead")
        self.producer = None
        self.consumers = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.consumer_tasks = []
        self._running = False

    async def start(self):
        """Inicializa o produtor e consumidores Kafka"""
        if self._running:
            logger.warning("Kafka service is already running")
            return

        try:
            # Inicializa o produtor
            self.producer = aiokafka.AIOKafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                enable_idempotence=True,  # Garante entrega única
                acks='all'  # Aguarda confirmação de todos os brokers
            )
            await self.producer.start()

            # Inicializa os consumidores para os tópicos de resposta
            response_topics = [
                PRIVACY_VALIDATE_RESPONSE_TOPIC,
                PRIVACY_EXECUTE_RESPONSE_TOPIC
            ]

            for topic in response_topics:
                consumer = aiokafka.AIOKafkaConsumer(
                    topic,
                    bootstrap_servers=KAFKA_BROKER,
                    group_id=f"{KAFKA_GROUP_ID}-{topic}",
                    auto_offset_reset="earliest",
                    enable_auto_commit=False  # Desabilita commit automático
                )
                await consumer.start()
                self.consumers[topic] = consumer

            self._running = True
            logger.info("Kafka service started successfully")
        except Exception as e:
            logger.error(f"Failed to start Kafka service: {str(e)}")
            await self.stop()
            raise

    async def stop(self):
        """Para todos os produtores e consumidores"""
        self._running = False
        try:
            # Cancela todas as tasks de consumo
            for task in self.consumer_tasks:
                if not task.done():
                    task.cancel()

            # Aguarda o cancelamento
            if self.consumer_tasks:
                await asyncio.gather(*self.consumer_tasks, return_exceptions=True)

            # Para o produtor
            if self.producer:
                await self.producer.stop()

            # Para os consumidores
            for consumer in self.consumers.values():
                await consumer.stop()

            # Limpa as referências
            self.producer = None
            self.consumers = {}
            self.consumer_tasks = []

            logger.info("Kafka service stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping Kafka service: {str(e)}")
            raise

    async def publish_message(self, topic: str, message: Dict[str, Any], key: str = None) -> bool:
        """
        Publica uma mensagem em um tópico
        Returns:
            bool: True se a mensagem foi publicada com sucesso, False caso contrário
        """
        if not self._running:
            logger.error("Kafka service is not running")
            return False

        try:
            value = json.dumps(message).encode('utf-8')
            key_bytes = key.encode('utf-8') if key else None
            await self.producer.send_and_wait(topic, value=value, key=key_bytes)
            logger.info(f"Message published to topic {topic}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish message to topic {topic}: {str(e)}")
            return False

    async def register_handler(self, topic: str, handler: Callable[[Dict[str, Any]], Coroutine]):
        """Registra um handler para processar mensagens de um tópico específico"""
        self.message_handlers[topic] = handler
        logger.info(f"Handler registered for topic {topic}")

    async def _consume_messages(self, topic: str):
        """Consome mensagens de um tópico específico"""
        consumer = self.consumers.get(topic)
        if not consumer:
            logger.error(f"No consumer found for topic {topic}")
            return

        handler = self.message_handlers.get(topic)
        if not handler:
            logger.error(f"No handler registered for topic {topic}")
            return

        try:
            while self._running:
                try:
                    async for msg in consumer:
                        try:
                            value = json.loads(msg.value.decode('utf-8'))
                            await handler(value)
                            await consumer.commit()
                            logger.debug(f"Message processed from topic {topic}")
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to decode message from topic {topic}: {e}")
                        except Exception as e:
                            logger.error(f"Error processing message from topic {topic}: {e}")
                except asyncio.CancelledError:
                    logger.info(f"Consumer task cancelled for topic {topic}")
                    break
                except Exception as e:
                    logger.error(f"Error consuming from topic {topic}: {e}")
                    if self._running:
                        await asyncio.sleep(1)  # Espera antes de tentar novamente
        finally:
            logger.info(f"Consumer task finished for topic {topic}")

    async def start_consuming(self):
        """Inicia o consumo de mensagens dos tópicos registrados"""
        if not self._running:
            logger.error("Kafka service is not running")
            return

        # Cancela tasks existentes
        for task in self.consumer_tasks:
            if not task.done():
                task.cancel()

        self.consumer_tasks = []

        # Cria nova task para cada tópico
        for topic in self.consumers.keys():
            task = asyncio.create_task(self._consume_messages(topic))
            self.consumer_tasks.append(task)

    async def validate_privacy_request(self, request_data: Dict[str, Any]) -> bool:
        """
        Envia uma requisição de validação de privacidade
        Returns:
            bool: True se a mensagem foi enviada com sucesso, False caso contrário
        """
        return await self.publish_message(PRIVACY_VALIDATE_TOPIC, request_data)

    async def execute_privacy_request(self, request_data: Dict[str, Any]) -> bool:
        """
        Envia uma requisição de execução de privacidade
        Returns:
            bool: True se a mensagem foi enviada com sucesso, False caso contrário
        """
        return await self.publish_message(PRIVACY_EXECUTE_TOPIC, request_data)

# Handlers padrão para os tópicos de resposta
async def handle_validate_response(message: Dict[str, Any]):
    """Handler para processar respostas de validação"""
    try:
        request_id = message.get('request_id')
        result = message.get('result')
        logger.info(f"Received validation response for request {request_id} with result {result}")

        await create_register_response(message)
    except Exception as e:
        logger.error(f"Error processing validation response: {str(e)}")

async def handle_execute_response(message: Dict[str, Any]):
    """Handler para processar respostas de execução"""
    try:
        request_id = message.get('request_id')
        status = message.get('status')
        logger.info(f"Received execution response for request {request_id} with status {status}")
        # Implemente sua lógica de processamento aqui
    except Exception as e:
        logger.error(f"Error processing execution response: {str(e)}")

# Instância global do serviço
kafka_service = KafkaService.get_instance()

async def initialize_kafka_service():
    """Inicializa o serviço Kafka com todos os handlers"""
    await kafka_service.start()

    # Registra os handlers para os tópicos de resposta
    await kafka_service.register_handler(
        PRIVACY_VALIDATE_RESPONSE_TOPIC,
        handle_validate_response
    )
    await kafka_service.register_handler(
        PRIVACY_EXECUTE_RESPONSE_TOPIC,
        handle_execute_response
    )

    # Inicia o consumo de mensagens
    await kafka_service.start_consuming()