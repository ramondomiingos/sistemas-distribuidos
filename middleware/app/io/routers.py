# Rotas da API
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
import uuid
from app.database import PrivacyRequest, Service, SessionLocal
from app.schemas import PrivacyRequestCreate, PrivacyRequestResponse, ServiceCreate, ServiceResponse, StatusRequest
from fastapi import APIRouter, HTTPException

import json


router = APIRouter()


@router.post("/services/", response_model=ServiceResponse)
def create_service(service: ServiceCreate):
    db = SessionLocal()
    service_id = str(uuid.uuid4())
    db_service = Service(id=service_id, service_name=service.service_name)
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service

@router.get("/services/", response_model=List[ServiceResponse])
def list_services():
    db = SessionLocal()
    services = db.query(Service).all()
    return services

@router.delete("/services/{service_id}")
def delete_service(service_id: str):
    db = SessionLocal()
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    db.delete(service)
    db.commit()
    return {"message": "Service deleted"}

@router.post("/privacy_request/", response_model=PrivacyRequestResponse)
async def create_privacy_request(request: Request,body: PrivacyRequestCreate):
    db = SessionLocal()
    request_id = str(uuid.uuid4())
    try:
        db_request = PrivacyRequest(
            id=request_id,
            account_id=body.account_id,
            operation=body.operation,
            status=StatusRequest.CREATED
        )

        producer = request.app.state.producer
        json_body = {
            "id": request_id,
            "account_id": body.account_id,
            "operation": body.operation,
            "status": StatusRequest.CREATED.value
        }
        await producer.send_and_wait('privacy-validate-topic', json.dumps(json_body).encode())
        print(f"[Producer] Enviado: {json_body} para o tópico privacy-validate-topic")
        
        db.add(db_request)
        db.commit()
        db.refresh(db_request)
        return db_request
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating privacy request: {str(e)}")
    
@router.get("/privacy_request/", response_model=List[PrivacyRequestResponse])
def list_privacy_requests():
    db = SessionLocal()
    requests = db.query(PrivacyRequest).all()
    return requests

@router.get("/privacy_request/{request_id}", response_model=PrivacyRequestResponse)
def get_privacy_request(request_id: str):
    db = SessionLocal()
    request = db.query(PrivacyRequest).filter(PrivacyRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Privacy request not found")
    return request


