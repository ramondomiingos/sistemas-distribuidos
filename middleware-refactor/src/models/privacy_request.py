# src/models/privacy_request.py
from sqlalchemy import Column, String, DateTime, Enum as SQLAlchemyEnum, func
from sqlalchemy.orm import relationship
from src.db.base import Base
from enum import Enum
import uuid

class OperationsExecution(str, Enum):
    DELETE = "DELETE"


class PrivacyRequest(Base):
    __tablename__ = "privacy_requests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String, nullable=False)
    operation = Column(SQLAlchemyEnum(OperationsExecution))
    status = Column(String, nullable=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # RELACIONAMENTO CORRETO
    services = relationship("PrivacyRequestService", back_populates="privacy_request")