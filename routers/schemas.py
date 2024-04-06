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

class Application(BaseModel):
    uid: int = None
    name: str
    status: str = None
    baseUrl: str
    ipInfo: IpInfo = None
    userId: int = None
    bugs: List[Bug] = []
    endpoints: List[Endpoint] = [] 
    

    class Config:
        from_attributes = True

class UserProfile(BaseModel):
    uid: int = None
    username: str = None
    keyclockId: str = None
    applications: List[Application] = []  
    developed_applications: List[Application] = []

    class Config:
        from_attributes = True
      
class DbEndpointLog(BaseModel):
    uid: int = None
    responseTime: float = None
    status: float = None
    endpointId: int = None



