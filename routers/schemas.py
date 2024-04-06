from pydantic import BaseModel
from typing import List

class Bug(BaseModel):
    uid: int = None
    description: str
    timestamp: str = None
    application_id: int = None
    
    class Config:
        from_attributes = True
    
class Endpoint(BaseModel):
    uid: int = None
    relativeUrl: str
    status: str = ""
    application_id: int = None
    
    class Config:
        from_attributes = True 
        
class IpInfo(BaseModel):
    uid: int
    address: str
    location: str
    timezone: str  
    applicationId: int
    
    class Config:
        from_attributes = True

class Application(BaseModel):
    uid: int = None
    name: str
    status: str = None
    baseUrl: str
    ipInfo: IpInfo = None
    refreshInterval:str = ""
    timeToKeep:str = ""
    userId: int = None
    bugs: List[Bug] = []
    endpoints: List[Endpoint] = [] 
    

    class Config:
        from_attributes = True

class UserProfile(BaseModel):
    uid: int = None
    username: str = None
    keyclockId: str = None
    addedApplications: List[Application] = []  
    developedApplications: List[Application] = []

    class Config:
        from_attributes = True
      
class EndpointLog(BaseModel):
    uid: int = None
    responseTime: float = None
    status: str = None
    endpointId: int = None
    
    class Config:
        from_attributes = True



