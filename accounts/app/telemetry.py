from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from prometheus_client import start_http_server, Counter

import logging
import os

# Configurações
otlp_endpoint = os.environ.get("OTLP_ENDPOINT", "http://otel:4317")
prometheus_port = int(os.environ.get("PROMETHEUS_PORT", "8001"))

# Prometheus metric
request_counter = Counter(
    "request_count",
    "Contagem de requisições recebidas",
    ["method", "endpoint"]
)

def configure_otel(app):
    # --- TRACING (Tempo) ---
    trace.set_tracer_provider(
        TracerProvider(
            resource=Resource.create({SERVICE_NAME: "accounts-service"})
        )
    )
    tracer_provider = trace.get_tracer_provider()
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True))
    )
    FastAPIInstrumentor.instrument_app(app)

    # --- LOGGING (Loki) ---
    logger_provider = LoggerProvider(
        resource=Resource.create({SERVICE_NAME: "accounts-service"})
    )
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter(endpoint=otlp_endpoint, insecure=True))
    )
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)
    LoggingInstrumentor().instrument(set_logging_format=True)
    logging.basicConfig(level=logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)
    
    # --- MÉTRICAS (Prometheus via prometheus_client) ---
    start_http_server(prometheus_port)

    @app.middleware("http")
    async def prometheus_middleware(request, call_next):
        request_counter.labels(method=request.method, endpoint=request.url.path).inc()
        return await call_next(request)
