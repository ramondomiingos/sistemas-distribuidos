# src/kafka/producer.py
import json
import logging
from typing import Optional, Dict, Any
from aiokafka import AIOKafkaProducer
from .config import KAFKA_BROKER

logger = logging.getLogger(__name__)

class KafkaProducer:
    _instance: Optional['KafkaProducer'] = None

    @classmethod
    def get_instance(cls) -> 'KafkaProducer':
        """Retorna a instância única do produtor"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Inicializa o produtor"""
        if self._instance is not None:
            raise RuntimeError("Use get_instance() instead")
        self._producer: Optional[AIOKafkaProducer] = None
        self._running = False

    async def start(self):
        """Inicia o produtor"""
        if self._running:
            logger.warning("Kafka producer is already running")
            return

        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                enable_idempotence=True,
                acks='all',
                compression_type='gzip',
                max_batch_size=16384,
                linger_ms=100
            )
            await self._producer.start()
            self._running = True
            logger.info("Kafka producer started successfully")
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {str(e)}")
            await self.stop()
            raise

    async def stop(self):
        """Para o produtor"""
        if self._producer:
            try:
                await self._producer.stop()
                self._producer = None
                self._running = False
                logger.info("Kafka producer stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping Kafka producer: {str(e)}")
                raise

    async def publish_message(
        self,
        topic: str,
        value: Dict[str, Any],
        key: Optional[str] = None
    ) -> bool:
        """
        Publica uma mensagem em um tópico

        Args:
            topic: Nome do tópico
            value: Mensagem a ser publicada
            key: Chave da mensagem (opcional)

        Returns:
            bool: True se publicado com sucesso
        """
        if not self._running or not self._producer:
            logger.error("Kafka producer is not running")
            return False

        try:
            # Converte para JSON e depois para bytes
            value_bytes = json.dumps(value).encode('utf-8')
            key_bytes = key.encode('utf-8') if key else None

            # Envia e aguarda confirmação
            await self._producer.send_and_wait(
                topic=topic,
                value=value_bytes,
                key=key_bytes
            )

            logger.info(f"Message published successfully to topic {topic}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish message to topic {topic}: {str(e)}")
            return False

    async def publish_batch(
        self,
        topic: str,
        messages: list[Dict[str, Any]],
        key_field: Optional[str] = None
    ) -> bool:
        """
        Publica várias mensagens em batch

        Args:
            topic: Nome do tópico
            messages: Lista de mensagens
            key_field: Campo a ser usado como chave (opcional)

        Returns:
            bool: True se todas as mensagens foram publicadas
        """
        if not self._running or not self._producer:
            logger.error("Kafka producer is not running")
            return False

        try:
            for message in messages:
                # Prepara a mensagem
                value_bytes = json.dumps(message).encode('utf-8')
                key = str(message.get(key_field)).encode('utf-8') if key_field else None

                # Envia (sem aguardar confirmação individual)
                await self._producer.send(
                    topic=topic,
                    value=value_bytes,
                    key=key
                )

            # Aguarda todas as mensagens serem enviadas
            await self._producer.flush()

            logger.info(f"Batch of {len(messages)} messages published to topic {topic}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish batch to topic {topic}: {str(e)}")
            return False

    @property
    def is_running(self) -> bool:
        """Retorna o status do produtor"""
        return self._running

# Instância global do produtor
kafka_producer = KafkaProducer.get_instance()

# Funções auxiliares
async def publish_message(
    topic: str,
    value: Dict[str, Any],
    key: Optional[str] = None
) -> bool:
    """Função auxiliar para publicar uma mensagem"""
    return await kafka_producer.publish_message(topic, value, key)

async def publish_messages(
    topic: str,
    messages: list[Dict[str, Any]],
    key_field: Optional[str] = None
) -> bool:
    """Função auxiliar para publicar múltiplas mensagens"""
    return await kafka_producer.publish_batch(topic, messages, key_field)