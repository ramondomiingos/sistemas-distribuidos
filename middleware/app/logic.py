
from typing import Optional
import uuid
from .database import PrivacyResquestServices, Service, SessionLocal
import logging
logger = logging.getLogger("middleware-service")
# logger.setLevel(logging.INFO)  

async def save_response_validate_response(
    request_id: str,
    operation: str,
    status: str,
    error_message: Optional[str] = None,
    service_name: Optional[str] = None,
):
    """
    Salva a resposta do validate_response no banco de dados.
    """
    db = SessionLocal()
    service_id = db.filter(Service, Service.service_name == service_name).first()
    if not service_id:
        logger.error(f"Service not found: {service_name}")
        # Tratar erro
    db_response = PrivacyResquestServices(
        id=str(uuid.uuid4()),
        privacy_request_id=request_id,
        service_id=service_id,
        service_name=service_name,
        status=status,
        operation=operation,
        description=error_message
    )
    db.add(db_response)
    db.commit()
    db.refresh(db_response)
    logger.info(f"Validate response saved: {db_response.request_id}")  

def should_publish_execute(request_id: str):
    """
    Verifica se deve publicar a mensagem no tópico de execução.
    Requisitos para publicação:
    - Todos os microsserviços existentes na tabela de serviços devem ter retornado o PREPARE com o status "APPROVED".
        lista1 = ["accounts", "payments", "crm", "delivery"]
        lista2 = ["accounts", "payments", "crm"]
        lista_services = set(lista1)
        services_response = set(lista2)
        elementos= lista_services.difference(services_response) | services_response.difference(lista_services)
          if len(elementos) != 0
            return false
          if a
    """
    db = SessionLocal()
    service_list = db.filter(Service).all()
    services_response = db.query(PrivacyResquestServices).filter(PrivacyResquestServices.privacy_request_id == request_id).all()
    lista_services = set(service_list)
    services_response = set(services_response)


    return True