# src/models/service.py
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.orm import relationship
from src.db.base import Base
import uuid

class Service(Base):
    __tablename__ = "services"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    service_name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # RELACIONAMENTO CORRETO
    privacy_requests = relationship("PrivacyRequestService", back_populates="service")