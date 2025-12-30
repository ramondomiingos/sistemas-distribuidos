# src/models/privacy_request_service.py
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from src.db.base import Base
from enum import Enum
import uuid


class OperationsExecution(str, Enum):
    PREPARE_DELETE = "PREPARE_DELETE"
    PERFORM_DELETE = "PERFORM_DELETE"


class PrivacyRequestService(Base):
    __tablename__ = "privacy_requests_services"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    privacy_request_id = Column(String, ForeignKey("privacy_requests.id"))
    service_id = Column(String, ForeignKey("services.id"))
    service_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    operation = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # RELACIONAMENTO CORRETO
    privacy_request = relationship("PrivacyRequest", back_populates="services")
    service = relationship("Service", back_populates="privacy_requests")