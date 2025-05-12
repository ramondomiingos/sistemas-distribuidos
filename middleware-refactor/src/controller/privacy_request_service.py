from fastapi.params import Depends
import logging

from src.kafka.producer import publish_message
from src.schemas.privacy_request_service import PrivacyRequestServiceCreate
# from src.services.kafka_service import KafkaService
from src.services.privacy_request_service import PrivacyRequestServiceService
from src.db.base import get_db
from sqlalchemy.orm import Session
from src.services.service import ServiceService
# from src.services.kafka_service import kafka_service
from src.kafka.topics import  PRIVACY_EXECUTE_TOPIC
logger = logging.getLogger(__name__)
async def create_register_response(
        message,
       ):

    logger.info(f"start controller with {message}, type {type(message)}")
    db = next(get_db())
    # db = get_db()
    service = ServiceService(db).get_by_name(message.get("service_name"))

    request_id= message.get("request_id")
    privacy_request_service = PrivacyRequestServiceCreate(
        service_name=service.service_name,
        service_id=service.id,
        privacy_request_id=request_id,
        status= 'OK' if message.get("result") else 'ERROR',
        operation =message.get("operation"),
        description=message.get("reason")
    )

    PrivacyRequestServiceService(db).create(privacy_request_service)
    if should_publish_execute(request_id):
        logger.info("should_publish_execute")
        json_body= {
            "request_id": request_id,
            "account_id": message.get("account_id"),
            "action": "PERFORM_DELETE"
        }
        # await publish_message(topic=PRIVACY_EXECUTE_TOPIC,value=json_body, key=request_id)
        from src.services.kafka_service import kafka_service
        await kafka_service.publish_message(topic=PRIVACY_EXECUTE_TOPIC,
                                       message=json_body, key=request_id)

        logger.info(f"published at {PRIVACY_EXECUTE_TOPIC} {json_body}")

    else:
        logger.info(f"finish controller with {message}, awaiting other responses")

def should_publish_execute(request_id: str):
    db = next(get_db())
    service_list =  ServiceService(db).get_multi()
    responses = PrivacyRequestServiceService(db).get_by_privacy_request(request_id)
    return len(service_list) != len(responses)