# from fastapi import FastAPI
# from src.api.v1.endpoints import services, privacy_requests, privacy_request_services
# from src.core.config import settings
# from src.core.telemetry import configure_otel
#
# import logging
# from src.services.kafka_service import initialize_kafka_service, kafka_service
# # import asyncio
# from contextlib import asynccontextmanager
#
#
# logger = logging.getLogger("middleware-service")
# logger.setLevel(logging.INFO)  # Garante nível INFO
#
#
# root_logger = logging.getLogger()
# root_logger.setLevel(logging.INFO)
#
# # Reduz o nível de log do Kafka
# kafka_logger = logging.getLogger("aiokafka")
# kafka_logger.setLevel(logging.WARNING)
#
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Startup
#     configure_otel(app)
#     await kafka_service.start()
#     await initialize_kafka_service()
#
#     yield
#     # Shutdown
#     await kafka_service.stop()
#     # await kafka_producer.stop()
#     # ... outros recursos ...
# app = FastAPI(
#     title=settings.PROJECT_NAME,
#     description="Privacy Service API",
#     version="1.0.0",
#     lifespan=lifespan
# )
#
# # setup_telemetry(app)
# # Initialize FastAPI instrumentation
# # FastAPIInstrumentor.instrument_app(app)
#
# # Include routers
# app.include_router(
#     services.router,
#     prefix="/api/v1/services",
#     tags=["services"]
# )
#
# app.include_router(
#     privacy_requests.router,
#     prefix="/api/v1/privacy-requests",
#     tags=["privacy-requests"]
# )
#
# app.include_router(
#     privacy_request_services.router,
#     prefix="/api/v1/privacy-request-services",
#     tags=["privacy-request-services"]
# )
#
# # Health check endpoint
# @app.get("/health")
# async def health_check():
#     return {"status": "healthy"}
#
# # @app.on_event("startup")
# # async def startup_event():
# #     # Inicializa o serviço Kafka
# #     asyncio.create_task(initialize_kafka_service())
# #
# # @app.on_event("shutdown")
# # async def shutdown_event():
# #     # Para o serviço Kafka
# #     await kafka_service.stop()
#
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
#
from fastapi import FastAPI
from src.api.v1.endpoints import services, privacy_requests, privacy_request_services
from src.core.config import settings
from src.core.telemetry import configure_otel

import logging
from src.services.kafka_service import initialize_kafka_service, kafka_service
from contextlib import asynccontextmanager

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("middleware-service")

# Reduz o nível de log do Kafka
logging.getLogger("aiokafka").setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    logger.info("Starting application lifecycle...")
    try:
        # Startup


        logger.info("Starting Kafka service...")
        await kafka_service.start()

        logger.info("Kafka service started")

        logger.info("Initializing Kafka service...")
        await initialize_kafka_service()
        logger.info("Kafka service initialized")

        logger.info("Application startup complete")
        yield

    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down application...")
        try:
            await kafka_service.stop()
            logger.info("Kafka service stopped")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

def create_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI"""
    logger.info("Creating FastAPI application...")

    # Cria a aplicação
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Privacy Service API",
        version="1.0.0",
        lifespan=lifespan
    )
    logger.info("Configuring OpenTelemetry...")
    configure_otel(app)
    logger.info("OpenTelemetry configured")

    # Inclui as rotas
    logger.info("Including routes...")
    app.include_router(
        services.router,
        prefix="/api/v1/services",
        tags=["services"]
    )

    app.include_router(
        privacy_requests.router,
        prefix="/api/v1/privacy-requests",
        tags=["privacy-requests"]
    )

    app.include_router(
        privacy_request_services.router,
        prefix="/api/v1/privacy-request-services",
        tags=["privacy-request-services"]
    )

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    logger.info("FastAPI application created successfully")
    return app

# Cria a aplicação
app = create_app()

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server...")

    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    )

    server = uvicorn.Server(config)
    try:
        server.run()
    except Exception as e:
        logger.error(f"Failed to start server: {e}")