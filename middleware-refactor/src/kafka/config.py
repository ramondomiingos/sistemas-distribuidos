import os

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "middleware-group")