# src/services/privacy_request.py
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import HTTPException
from src.models.privacy_request import PrivacyRequest, OperationsExecution
from src.schemas.privacy_request import PrivacyRequestCreate, PrivacyRequestUpdate

class PrivacyRequestService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, obj_in: PrivacyRequestCreate) -> PrivacyRequest:
        """Create a new privacy request"""
        db_obj = PrivacyRequest(
            account_id=obj_in.account_id,
            operation=obj_in.operation,
            status=obj_in.status or "PENDING",
            description=obj_in.description
        )
        self.db.add(db_obj)
        try:
            self.db.commit()
            self.db.refresh(db_obj)
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        return db_obj

    def get(self, request_id: str) -> Optional[PrivacyRequest]:
        """Get a privacy request by ID"""
        return self.db.query(PrivacyRequest).filter(PrivacyRequest.id == request_id).first()

    def get_by_account(self, account_id: str) -> List[PrivacyRequest]:
        """Get all privacy requests for an account"""
        return self.db.query(PrivacyRequest)\
            .filter(PrivacyRequest.account_id == account_id)\
            .order_by(PrivacyRequest.created_at.desc())\
            .all()

    def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        operation: Optional[OperationsExecution] = None
    ) -> List[PrivacyRequest]:
        """Get multiple privacy requests with filters"""
        query = self.db.query(PrivacyRequest)

        if status:
            query = query.filter(PrivacyRequest.status == status)
        if operation:
            query = query.filter(PrivacyRequest.operation == operation)

        return query\
            .order_by(PrivacyRequest.created_at.desc())\
            .offset(skip)\
            .limit(limit)\
            .all()

    def update(
        self,
        request_id: str,
        obj_in: PrivacyRequestUpdate
    ) -> Optional[PrivacyRequest]:
        """Update a privacy request"""
        db_obj = self.get(request_id)
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

    def delete(self, request_id: str) -> bool:
        """Delete a privacy request"""
        db_obj = self.get(request_id)
        if not db_obj:
            return False

        try:
            self.db.delete(db_obj)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        return True

    def get_by_status(self, status: str) -> List[PrivacyRequest]:
        """Get all privacy requests with a specific status"""
        return self.db.query(PrivacyRequest)\
            .filter(PrivacyRequest.status == status)\
            .order_by(PrivacyRequest.created_at.desc())\
            .all()

    def get_by_operation(self, operation: OperationsExecution) -> List[PrivacyRequest]:
        """Get all privacy requests with a specific operation"""
        return self.db.query(PrivacyRequest)\
            .filter(PrivacyRequest.operation == operation)\
            .order_by(PrivacyRequest.created_at.desc())\
            .all()