from fastapi import FastAPI

from typing import List, Optional
import uuid
from io import routers



# Inicializa o FastAPI
app = FastAPI()
app.include_router(routers.router, prefix="/api/v1", tags=["privacy_request"])
