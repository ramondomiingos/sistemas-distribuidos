from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Privacy Service"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5437/middlewaredb")
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    # OpenTelemetry settings
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"

    model_config = SettingsConfigDict(case_sensitive=True)

settings = Settings()