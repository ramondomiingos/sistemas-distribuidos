
from sqlalchemy import create_engine, Column, String
# from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base


from sqlalchemy.orm import sessionmaker
from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func
import os

# Configurações do banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5437/middlewaredb")

# Conexão com o banco de dados
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Modelo do banco de dados
class Service(Base):
    __tablename__ = "services"
    id = Column(String, primary_key=True, index=True)
    service_name = Column(String, index=True)
    description = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), 
                      server_default=func.now(), 
                      nullable=False)
    
    updated_at = Column(DateTime(timezone=True), 
                       server_default=func.now(), 
                       onupdate=func.now(),
                       nullable=False)


class PrivacyRequest(Base):
    __tablename__ = "privacy_requests"
    id = Column(String, primary_key=True, index=True)
    account_id = Column(String, index=True)
    operation = Column(String, index=True)
    status = Column(String, index=True)
    description = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), 
                      server_default=func.now(), 
                      nullable=False)
    
    updated_at = Column(DateTime(timezone=True), 
                       server_default=func.now(), 
                       onupdate=func.now(),
                       nullable=False)

class PrivacyResquestServices(Base):
    __tablename__ = "privacy_requests_services"
    id = Column(String, primary_key=True, index=True)
    privacy_request_id = Column(String)
    service_id = Column(String)
    service_name = Column(String)
    status = Column(String)
    operation = Column(String)
    description = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), 
                      server_default=func.now(), 
                      nullable=False)
    
    updated_at = Column(DateTime(timezone=True), 
                       server_default=func.now(), 
                       onupdate=func.now(),
                       nullable=False)



# Cria as tabelas no banco de dados
Base.metadata.create_all(bind=engine)