from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os
from enum import Enum

class OperationRequest(str, Enum):
    DELETE = "DELETE"

class StatusRequest(str, Enum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    APPROVED = "APPROVED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    EXECUTION_FAILED = "EXECUTION_FAILED"

class ServiceCreate(BaseModel):
    service_name: str
    description: Optional[str] = None

class ServiceResponse(BaseModel):
    id: str
    service_name: str
    description: Optional[str] = None

class PrivacyRequestCreate(BaseModel):
    account_id: str
    operation: OperationRequest
    status: Optional[str] = None
    description: Optional[str] = None

class OperationsExecution(str, Enum):
    PREPARE_DELETE = "PREPARE_DELETE"
    PERFORM_DELETE = "PERFORM_DELETE"

class PrivacyRequestResponse(BaseModel):
    id: str
    account_id: str
    operation: OperationRequest
    status: str
    description: Optional[str] = None