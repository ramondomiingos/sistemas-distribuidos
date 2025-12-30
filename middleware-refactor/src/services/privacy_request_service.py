# src/services/privacy_request_service.py
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from src.models.privacy_request_service import PrivacyRequestService
from src.schemas.privacy_request_service import PrivacyRequestServiceCreate, PrivacyRequestServiceUpdate
from fastapi import HTTPException

class PrivacyRequestServiceService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, obj_in: PrivacyRequestServiceCreate) -> PrivacyRequestService:
        db_obj = PrivacyRequestService(
            privacy_request_id=obj_in.privacy_request_id,
            service_id=obj_in.service_id,
            service_name=obj_in.service_name,
            status=obj_in.status,
            operation=obj_in.operation,
            description=obj_in.description,
        )
        self.db.add(db_obj)
        try:
            self.db.commit()
            self.db.refresh(db_obj)
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        return db_obj

    def get(self, id: str) -> Optional[PrivacyRequestService]:
        return self.db.query(PrivacyRequestService).filter(PrivacyRequestService.id == id).first()

    def get_by_privacy_request_and_operation(self, privacy_request_id: str, operation) -> List[PrivacyRequestService]:
        return self.db.query(PrivacyRequestService)\
            .filter(PrivacyRequestService.privacy_request_id == privacy_request_id) \
            .filter(PrivacyRequestService.operation == operation) \
            .all()

    def get_by_service(self, service_id: str) -> List[PrivacyRequestService]:
        return self.db.query(PrivacyRequestService)\
            .filter(PrivacyRequestService.service_id == service_id)\
            .all()

    def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[PrivacyRequestService]:
        query = self.db.query(PrivacyRequestService)
        if status:
            query = query.filter(PrivacyRequestService.status == status)
        return query.offset(skip).limit(limit).all()

    def update(
        self,
        id: str,
        obj_in: PrivacyRequestServiceUpdate
    ) -> Optional[PrivacyRequestService]:
        db_obj = self.get(id)
        if not db_obj:
            return None

        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        try:
            self.db.commit()
            self.db.refresh(db_obj)
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        return db_obj

    def delete(self, id: str) -> bool:
        db_obj = self.get(id)
        if not db_obj:
            return False

        try:
            self.db.delete(db_obj)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        return True