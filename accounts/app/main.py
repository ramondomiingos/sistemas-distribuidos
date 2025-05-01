from .telemetry import configure_otel
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel

import os
import logging


DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    account_id = Column(String, unique=True, index=True)

Base.metadata.create_all(bind=engine)

app = FastAPI()
configure_otel(app)


logger = logging.getLogger("accounts")
logger.setLevel(logging.INFO)  # Garante nível INFO


root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

class UserCreate(BaseModel):
    name: str
    email: str
    account_id: str



@app.post("/users/")
def create_user(user: UserCreate):
    db = SessionLocal()
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"User created: {db_user.account_id}")  # Log the user creation
    return db_user

@app.get("/users/{account_id}")
def read_user(account_id: str):
    db = SessionLocal()
    user = db.query(User).filter(User.account_id == account_id).first()
    if user is None:
        logger.warning(f"User not found: {account_id}") # Log user not found
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User found {user.id},{ user.account_id}, {user.email}, {user.name} ")  # Log the user found
    return user

@app.get("/users/")
def list_users():
    db = SessionLocal()
    users = db.query(User).all()
    logger.info(f"Users listed. Count: {len(users)}")
    return users