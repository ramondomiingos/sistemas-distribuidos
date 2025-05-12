
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True)
    status = Column(String)
    amount = Column(Float)
    currency = Column(String)
    payment_method = Column(String)
    transaction_id = Column(String)
    payment_date = Column(DateTime)
    account_id = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI(title='payment-service')

class OrderCreate(BaseModel):
    order_id: str
    status: str
    amount: float
    currency: str
    payment_method: str
    transaction_id: str
    payment_date: datetime
    account_id: str

@app.post("/orders/")
def create_order(order: OrderCreate):
    db = SessionLocal()
    db_order = Order(**order.dict())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

@app.get("/orders/{order_id}")
def read_order(order_id: str):
    db = SessionLocal()
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
    
@app.get("/orders/")
def list_orders():
    db = SessionLocal()
    orders = db.query(Order).all()
    return orders
# @app.on_event("startup")
# async def startup():
#     Instrumentator().instrument(app, metric_namespace='myproject', metric_subsystem='myservice').expose(app)
