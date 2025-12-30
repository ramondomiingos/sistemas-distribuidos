from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PrivacyRequestServiceBase(BaseModel):
    privacy_request_id: str
    service_id: str
    service_name: str
    status: str
    operation: str
    description: Optional[str] = None

class PrivacyRequestServiceCreate(PrivacyRequestServiceBase):
    pass

class PrivacyRequestServiceUpdate(BaseModel):
    status: Optional[str] = None
    description: Optional[str] = None

class PrivacyRequestService(PrivacyRequestServiceBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True