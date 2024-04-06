from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database.database import Base
from datetime import datetime

class DbApplication(Base):
    __tablename__ = "application"
    uid = Column(Integer, index=True, primary_key=True)
    name = Column(String, unique=True)
    status = Column(String)
    baseUrl = Column(String)
    ip = Column(String)
    
    userId = Column(Integer, ForeignKey('user.uid'))
    owner = relationship("DbUser", back_populates="applications", overlaps="user")
    user = relationship("DbUser", back_populates="developed_applications", overlaps="applications")
    
    bugs = relationship("DbBug", back_populates="application", cascade="all, delete")
    
    endpoints = relationship("DbEndpoint", back_populates="application",  cascade="all, delete")


class DbUser(Base):
    __tablename__ = "user"
    uid = Column(Integer, primary_key=True, index=True)
    keyclockId = Column(String)
    username = Column(String)
    
    applications = relationship("DbApplication", back_populates="owner", cascade="all, delete", overlaps="developed_applications")
    
    developed_applications = relationship("DbApplication", back_populates="user", cascade="all, delete", overlaps="owner")






class DbBug(Base):
    __tablename__ = "bug"
    uid = Column(Integer, index=True, primary_key=True)
    categoryId = Column(Integer)
    description = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    application_id = Column(Integer, ForeignKey('application.uid'))
    application = relationship("DbApplication", back_populates="bugs")
   
class DbEndpoint(Base):
    __tablename__ = "endpoint"
    uid = Column(Integer, index=True, primary_key=True)
    relativeUrl = Column(String)
    status = Column(String)
    
    application_id = Column(Integer, ForeignKey('application.uid'))
    application = relationship("DbApplication", back_populates="endpoints")