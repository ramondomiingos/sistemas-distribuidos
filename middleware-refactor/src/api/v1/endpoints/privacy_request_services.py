from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from src.db.base import get_db
from src.schemas.privacy_request_service import (
    PrivacyRequestServiceCreate,
    PrivacyRequestService,
    PrivacyRequestServiceUpdate
)
from src.services.privacy_request_service import PrivacyRequestServiceService
from src.monitoring.metrics import track_request_time

router = APIRouter()

@router.post("/", response_model=PrivacyRequestService)
@track_request_time
async def create_privacy_request_service(
    privacy_request_service: PrivacyRequestServiceCreate,
    db: Session = Depends(get_db)
):
    """Create a new privacy request service mapping"""
    return PrivacyRequestServiceService(db).create(privacy_request_service)

@router.get("/", response_model=List[PrivacyRequestService])
@track_request_time
async def list_privacy_request_services(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all privacy request services with optional status filter"""
    return PrivacyRequestServiceService(db).get_multi(
        skip=skip,
        limit=limit,
        status=status
    )

@router.get("/{id}", response_model=PrivacyRequestService)
@track_request_time
async def get_privacy_request_service(
    id: str,
    db: Session = Depends(get_db)
):
    """Get a specific privacy request service by ID"""
    service = PrivacyRequestServiceService(db).get(id)
    if not service:
        raise HTTPException(status_code=404, detail="Privacy request service not found")
    return service

@router.get("/privacy-request/{privacy_request_id}", response_model=List[PrivacyRequestService])
@track_request_time
async def get_services_by_privacy_request(
    privacy_request_id: str,
    db: Session = Depends(get_db)
):
    """Get all services associated with a privacy request"""
    return PrivacyRequestServiceService(db).get_by_privacy_request(privacy_request_id)

@router.get("/service/{service_id}", response_model=List[PrivacyRequestService])
@track_request_time
async def get_privacy_requests_by_service(
    service_id: str,
    db: Session = Depends(get_db)
):
    """Get all privacy requests associated with a service"""
    return PrivacyRequestServiceService(db).get_by_service(service_id)

@router.put("/{id}", response_model=PrivacyRequestService)
@track_request_time
async def update_privacy_request_service(
    id: str,
    privacy_request_service: PrivacyRequestServiceUpdate,
    db: Session = Depends(get_db)
):
    """Update a privacy request service"""
    service = PrivacyRequestServiceService(db).update(id, privacy_request_service)
    if not service:
        raise HTTPException(status_code=404, detail="Privacy request service not found")
    return service

@router.delete("/{id}")
@track_request_time
async def delete_privacy_request_service(
    id: str,
    db: Session = Depends(get_db)
):
    """Delete a privacy request service"""
    success = PrivacyRequestServiceService(db).delete(id)
    if not success:
        raise HTTPException(status_code=404, detail="Privacy request service not found")
    return {"message": "Privacy request service deleted successfully"}