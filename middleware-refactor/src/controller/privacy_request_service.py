import logging
from typing import Dict

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from src.models.privacy_request import OperationsExecution
from src.models.privacy_request_service import PrivacyRequestService as PrivacyRequestServiceModel
from src.schemas.privacy_request_service import PrivacyRequestServiceCreate
from src.services.privacy_request_service import PrivacyRequestServiceService
from src.db.base import get_db
from src.services.service import ServiceService
from src.kafka.topics import PRIVACY_EXECUTE_TOPIC

logger = logging.getLogger(__name__)

# Cache em memória — evita SELECT * FROM services em cada mensagem Kafka.
# Atualizado em refresh_service_cache(), chamado no startup e ao registrar serviços.
_n_services: int = 0
_service_map: Dict[str, str] = {}  # service_name → service_id


def refresh_service_cache():
    """Recarrega contagem e mapa name→id dos serviços registrados."""
    global _n_services, _service_map
    db = next(get_db())
    try:
        services = ServiceService(db).get_multi(limit=100)
        _n_services = len(services)
        _service_map = {s.service_name: s.id for s in services}
        logger.info(f"[cache] {_n_services} serviço(s) carregado(s): {list(_service_map.keys())}")
    finally:
        db.close()


def _count_responses(db: Session, request_id: str, operation: str) -> int:
    """Conta respostas já recebidas para request_id/operation sem carregar os objetos."""
    return db.query(func.count(PrivacyRequestServiceModel.id))\
        .filter(PrivacyRequestServiceModel.privacy_request_id == request_id)\
        .filter(PrivacyRequestServiceModel.operation == operation)\
        .scalar() or 0


def _try_transition(db: Session, request_id: str, from_status: str, to_status: str) -> bool:
    """Transição de status atômica via UPDATE condicional.

    Retorna True apenas para o processo/coroutine que vencer a corrida.
    Se dois workers processarem o último response do mesmo request_id
    simultaneamente, apenas um verá rowcount=1.
    """
    result = db.execute(
        text("UPDATE privacy_requests SET status=:to, updated_at=now() WHERE id=:id AND status=:from"),
        {"to": to_status, "id": request_id, "from": from_status},
    )
    db.commit()
    return result.rowcount == 1


def should_publish_execute(request_id: str, db: Session) -> bool:
    if _n_services == 0:
        return False
    if _n_services != _count_responses(db, request_id, 'PREPARE_DELETE'):
        return False
    # Somente quem fizer CREATED→EXECUTING publica o execute.
    return _try_transition(db, request_id, 'CREATED', 'EXECUTING')


def should_finished_request(request_id: str, db: Session) -> bool:
    if _n_services == 0:
        return False
    if _n_services != _count_responses(db, request_id, 'PERFORM_DELETE'):
        return False
    # Somente quem fizer EXECUTING→FINISHED finaliza a requisição.
    return _try_transition(db, request_id, 'EXECUTING', 'FINISHED')


async def create_register_validate_response(message):
    request_id = message.get("request_id")
    service_name = message.get("service_name")
    logger.debug(f"[validate-resp] request={request_id} service={service_name}")

    db = next(get_db())
    try:
        service_id = _service_map.get(service_name)
        if not service_id:
            # Fallback para DB caso o cache ainda não tenha sido populado
            svc = ServiceService(db).get_by_name(service_name)
            service_id = svc.id if svc else None

        privacy_request_service = PrivacyRequestServiceCreate(
            service_name=service_name,
            service_id=service_id,
            privacy_request_id=request_id,
            status='OK' if message.get("result") else 'ERROR',
            operation=message.get("operation"),
            description=message.get("reason")
        )
        PrivacyRequestServiceService(db).create(privacy_request_service)

        if should_publish_execute(request_id, db):
            json_body = {
                "request_id": request_id,
                "account_id": message.get("account_id"),
                "operation": "PERFORM_DELETE"
            }
            from src.services.kafka_service import kafka_service
            await kafka_service.publish_message(
                topic=PRIVACY_EXECUTE_TOPIC, message=json_body, key=request_id
            )
            logger.debug(f"[validate-resp] execute publicado request={request_id}")
    finally:
        db.close()


async def create_register_execute_response(message):
    request_id = message.get("request_id")
    service_name = message.get("service_name")
    logger.debug(f"[execute-resp] request={request_id} service={service_name}")

    db = next(get_db())
    try:
        service_id = _service_map.get(service_name)
        if not service_id:
            svc = ServiceService(db).get_by_name(service_name)
            service_id = svc.id if svc else None

        privacy_request_service = PrivacyRequestServiceCreate(
            service_name=service_name,
            service_id=service_id,
            privacy_request_id=request_id,
            status='OK' if message.get("result") else 'ERROR',
            operation=message.get("operation"),
            description=message.get("reason")
        )
        PrivacyRequestServiceService(db).create(privacy_request_service)

        if should_finished_request(request_id, db):
            # Status já atualizado para FINISHED atomicamente em should_finished_request
            logger.debug(f"[execute-resp] FINISHED request={request_id}")
    finally:
        db.close()