# src/services/service.py
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import HTTPException
from src.models.service import Service
from src.schemas.service import ServiceCreate, ServiceUpdate

class ServiceService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, obj_in: ServiceCreate) -> Service:
        """Create a new service"""
        db_obj = Service(
            service_name=obj_in.service_name,
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

    def get(self, service_id: str) -> Optional[Service]:
        """Get a service by ID"""
        return self.db.query(Service).filter(Service.id == service_id).first()

    def get_by_name(self, name: str) -> Optional[Service]:
        """Get a service by name"""
        return self.db.query(Service).filter(Service.service_name == name).first()

    def get_multi(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Service]:
        """Get multiple services with pagination"""
        return self.db.query(Service)\
            .order_by(Service.created_at.desc())\
            .offset(skip)\
            .limit(limit)\
            .all()

    def update(
        self,
        service_id: str,
        obj_in: ServiceUpdate
    ) -> Optional[Service]:
        """Update a service"""
        db_obj = self.get(service_id)
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

    def delete(self, service_id: str) -> bool:
        """Delete a service"""
        db_obj = self.get(service_id)
        if not db_obj:
            return False

        try:
            self.db.delete(db_obj)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        return True

    def search(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Service]:
        """Search services by name or description"""
        return self.db.query(Service)\
            .filter(
                (Service.service_name.ilike(f"%{search_term}%")) |
                (Service.description.ilike(f"%{search_term}%"))
            )\
            .offset(skip)\
            .limit(limit)\
            .all()