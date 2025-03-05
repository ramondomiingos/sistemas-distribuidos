from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Delivery(Base):
    __tablename__ = "deliveries"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True)
    status = Column(String)
    tracking_code = Column(String)
    estimated_delivery = Column(DateTime)
    carrier = Column(String)
    customer_id = Column(String)
    shipping_address = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI()

class DeliveryCreate(BaseModel):
    order_id: str
    status: str
    tracking_code: str
    estimated_delivery: datetime
    carrier: str
    customer_id: str
    shipping_address: str

@app.post("/delivery/")
def create_delivery(delivery: DeliveryCreate):
    db = SessionLocal()
    db_delivery = Delivery(**delivery.dict())
    db.add(db_delivery)
    db.commit()
    db.refresh(db_delivery)
    return db_delivery

@app.get("/delivery/{order_id}")
def read_delivery(order_id: str):
    db = SessionLocal()
    delivery = db.query(Delivery).filter(Delivery.order_id == order_id).first()
    if delivery is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return delivery

@app.get("/delivery/")
def list_deliveries():
    db = SessionLocal()
    deliveries = db.query(Delivery).all()
    return deliveries