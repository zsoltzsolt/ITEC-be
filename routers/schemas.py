from pydantic import BaseModel
from typing import List

class UserProfile(BaseModel):
    uid: int = None
    username: str = None
    keyclockId: str = None
    application_id: int = None  
    applications: List['Application'] = []  
    developed_applications: List['Application'] = []

    class Config:
        from_attributes = True

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
    status: str = None
    application_id: int = None
    
    class Config:
        from_attributes = True 

class Application(BaseModel):
    uid: int = None
    name: str
    status: str = None
    baseUrl: str
    endpoints: List[Endpoint] = [] 
    owner: UserProfile = None
    bugs: List[Bug] = []

    class Config:
        from_attributes = True
