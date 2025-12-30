# src/api/v1/endpoints/services.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.db.base import get_db
from src.schemas.service import ServiceCreate, Service, ServiceUpdate
from src.services.service import ServiceService
from src.monitoring.metrics import track_request_time

router = APIRouter()

@router.post("/", response_model=Service)
@track_request_time
async def create_service(
    service: ServiceCreate,
    db: Session = Depends(get_db)
):
    return ServiceService(db).create(service)

@router.get("/", response_model=List[Service])
@track_request_time
async def list_services(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    return ServiceService(db).get_multi(skip=skip, limit=limit)

@router.get("/{service_id}", response_model=Service)
@track_request_time
async def get_service(
    service_id: str,
    db: Session = Depends(get_db)
):
    service = ServiceService(db).get(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service

@router.put("/{service_id}", response_model=Service)
@track_request_time
async def update_service(
    service_id: str,
    service_update: ServiceUpdate,
    db: Session = Depends(get_db)
):
    service = ServiceService(db).update(service_id, service_update)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service

@router.delete("/{service_id}")
@track_request_time
async def delete_service(
    service_id: str,
    db: Session = Depends(get_db)
):
    service = ServiceService(db).delete(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return {"message": "Service deleted successfully"}