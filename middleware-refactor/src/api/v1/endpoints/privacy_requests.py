# src/api/v1/endpoints/privacy_requests.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from src.db.base import get_db
from src.kafka.producer import publish_message, kafka_producer
from src.models.privacy_request import OperationsExecution
from src.models.privacy_request_service import OperationsExecution as OperationsExecutionServices
from src.schemas.privacy_request import (
    PrivacyRequestCreate,
    PrivacyRequest,
    PrivacyRequestUpdate
)
from src.services.privacy_request import PrivacyRequestService
from src.monitoring.metrics import track_request_time
from src.kafka.topics import  PRIVACY_VALIDATE_TOPIC
from src.services.kafka_service import kafka_service
router = APIRouter()

@router.post("/", response_model=PrivacyRequest)
@track_request_time
async def create_privacy_request(
    privacy_request: PrivacyRequestCreate,
    db: Session = Depends(get_db)
):
    """Create a new privacy request"""
    privacy_response =  PrivacyRequestService(db).create(privacy_request)
    json_body = {
        "request_id": privacy_response.id,
        "account_id": privacy_request.account_id,
        "operation": OperationsExecutionServices.PREPARE_DELETE.value,

    }

    await kafka_service.publish_message(topic=PRIVACY_VALIDATE_TOPIC,message=json_body, key=privacy_response.id)
    return privacy_response

@router.get("/", response_model=List[PrivacyRequest])
@track_request_time
async def list_privacy_requests(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    operation: Optional[OperationsExecution] = None,
    db: Session = Depends(get_db)
):
    """List all privacy requests with optional filters"""
    return PrivacyRequestService(db).get_multi(
        skip=skip,
        limit=limit,
        status=status,
        operation=operation
    )

@router.get("/{request_id}", response_model=PrivacyRequest)
@track_request_time
async def get_privacy_request(
    request_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific privacy request by ID"""
    request = PrivacyRequestService(db).get(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Privacy request not found")
    return request

@router.get("/account/{account_id}", response_model=List[PrivacyRequest])
@track_request_time
async def get_account_privacy_requests(
    account_id: str,
    db: Session = Depends(get_db)
):
    """Get all privacy requests for a specific account"""
    return PrivacyRequestService(db).get_by_account(account_id)

@router.put("/{request_id}", response_model=PrivacyRequest)
@track_request_time
async def update_privacy_request(
    request_id: str,
    privacy_request: PrivacyRequestUpdate,
    db: Session = Depends(get_db)
):
    """Update a privacy request"""
    request = PrivacyRequestService(db).update(request_id, privacy_request)
    if not request:
        raise HTTPException(status_code=404, detail="Privacy request not found")
    return request

@router.delete("/{request_id}")
@track_request_time
async def delete_privacy_request(
    request_id: str,
    db: Session = Depends(get_db)
):
    """Delete a privacy request"""
    success = PrivacyRequestService(db).delete(request_id)
    if not success:
        raise HTTPException(status_code=404, detail="Privacy request not found")
    return {"message": "Privacy request deleted successfully"}