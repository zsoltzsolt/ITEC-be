from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from database.database import Base
from datetime import datetime

class DbApplication(Base):
    __tablename__ = "application"
    uid = Column(Integer, index=True, primary_key=True)
    name = Column(String, unique=True)
    status = Column(String)
    baseUrl = Column(String)
    refreshInterval = Column(String)
    timeToKeep = Column(String)
    
    ipInfo = relationship("DbIpInfo", back_populates="application", uselist=False, cascade="all, delete")
    
    userId = Column(Integer, ForeignKey('user.uid', ondelete='CASCADE'))
    owner = relationship("DbUser", back_populates="addedApplications", overlaps="user", cascade="all, delete")
    user = relationship("DbUser", back_populates="developedApplications", overlaps="addedApplications", cascade="all, delete")
    
    bugs = relationship("DbBug", back_populates="application", cascade="all, delete")
    
    endpoints = relationship("DbEndpoint", back_populates="application", cascade="all, delete")
    
    
class DbIpInfo(Base):
    __tablename__ = "ipInfo"
    uid = Column(Integer, primary_key=True, index=True)
    address = Column(String)
    location = Column(String)
    timezone = Column(String)
    
    applicationId = Column(Integer, ForeignKey('application.uid', ondelete='CASCADE'))
    application = relationship("DbApplication", back_populates="ipInfo", cascade="all, delete", uselist=False)
    
    
class DbEndpointLog(Base):
    __tablename__ = "endpointLog"
    uid = Column(Integer, primary_key=True, index=True)
    responseTime = Column(Float)
    status = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    endpointId = Column(Integer, ForeignKey('endpoint.uid', ondelete='CASCADE'))
    endpoint = relationship("DbEndpoint", back_populates="log", cascade="all, delete")


class DbUser(Base):
    __tablename__ = "user"
    uid = Column(Integer, primary_key=True, index=True)
    keyclockId = Column(String)
    username = Column(String)
    
    addedApplications = relationship("DbApplication", back_populates="owner", cascade="all, delete", overlaps="developedApplications")
    
    developedApplications = relationship("DbApplication", back_populates="user", cascade="all, delete", overlaps="owner")


class DbBug(Base):
    __tablename__ = "bug"
    uid = Column(Integer, index=True, primary_key=True)
    description = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    applicationId = Column(Integer, ForeignKey('application.uid', ondelete='CASCADE'))
    application = relationship("DbApplication", back_populates="bugs", cascade="all, delete")


class DbEndpoint(Base):
    __tablename__ = "endpoint"
    uid = Column(Integer, index=True, primary_key=True)
    relativeUrl = Column(String)
    status = Column(String)
    
    log = relationship("DbEndpointLog", back_populates="endpoint", cascade="all, delete")
    
    applicationId = Column(Integer, ForeignKey('application.uid', ondelete='CASCADE'))
    application = relationship("DbApplication", back_populates="endpoints", cascade="all, delete")
