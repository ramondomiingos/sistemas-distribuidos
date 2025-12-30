from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from src.models.privacy_request import OperationsExecution

class PrivacyRequestBase(BaseModel):
    account_id: str
    operation: OperationsExecution
    status: Optional[str] = None
    description: Optional[str] = None

class PrivacyRequestCreate(PrivacyRequestBase):
    pass

class PrivacyRequestUpdate(PrivacyRequestBase):
    pass

class PrivacyRequest(PrivacyRequestBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True