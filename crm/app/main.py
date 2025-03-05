from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class UserInfo(Base):
    __tablename__ = "user_info"
    id = Column(Integer, primary_key=True, index=True)
    birth_day = Column(Date)
    account_id = Column(String, unique=True, index=True)
    religion = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI()

class UserInfoCreate(BaseModel):
    birth_day: str
    account_id: str
    religion: str

@app.post("/info-users/")
def create_user_info(user_info: UserInfoCreate):
    db = SessionLocal()
    db_user_info = UserInfo(**user_info.dict())
    db.add(db_user_info)
    db.commit()
    db.refresh(db_user_info)
    return db_user_info

@app.get("/info-users/{account_id}")
def read_user_info(account_id: str):
    db = SessionLocal()
    user_info = db.query(UserInfo).filter(UserInfo.account_id == account_id).first()
    if user_info is None:
        raise HTTPException(status_code=404, detail="User info not found")
    return user_info

@app.get("/info-users/")
def list_user_info():
    db = SessionLocal()
    user_info = db.query(UserInfo).all()
    return user_info