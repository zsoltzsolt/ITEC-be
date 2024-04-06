from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from routers.schemas import Application
from database.database import get_db
from database.models import DbApplication, DbEndpoint, DbIpInfo, DbUser, DbEndpointLog
from typing import List
import asyncio
import time 
import requests
import socket
from auth.auth import get_payload
from datetime import datetime

router = APIRouter(
    prefix="/application",
    tags=["Application"]
)

def get_endpoint_ip(url: str) -> str:
    try:
        print(f"{url}")
        ip_address = socket.gethostbyname(url)
        return ip_address
    except socket.gaierror:
        return "IP not found"


async def monitor_endpoints(app_id: int, refresh_interval: int, time_to_keep:int, db: Session):
    while True:
        try:
            print(f"REFRESH {refresh_interval}")
            await asyncio.sleep(refresh_interval)
            app = db.query(DbApplication).filter(DbApplication.uid == app_id).first()
            if app:
                for endpoint in app.endpoints:
                    relativeUrl = endpoint.relativeUrl
                    if relativeUrl[0] == '/':
                        relativeUrl = relativeUrl[1:]
                    path = "https://" + app.baseUrl + "/" + relativeUrl
                    print(path)
                    response_time=.001
                    start = time.time()
                    start_time = datetime.utcnow() 
                    try:
                        response = requests.get(path)
                        response.raise_for_status()  
                        response_time = time.time() - start
                        print(f"App: {app.name}, Endpoint: {endpoint.relativeUrl}, Response Time: {response_time}")
                    except requests.RequestException as e:
                        response_time = time.time() - start
                        print(f"App: {app.name}, Endpoint: {endpoint.relativeUrl}, Error: {e}, Response Time: {response_time}")
                    log = DbEndpointLog(
                        responseTime=response_time,
                        status=f"{response.status_code}",
                        endpointId=endpoint.uid,
                        timestamp=start_time
                    )
                    db.add(log)
                    db.commit()
            else:
                print(f"App does not exist")
                break
        except Exception as e:
            print(f"An error occurred: {e}")
            continue 
        
def time_to_seconds(time_str: str) -> int:
    parts = time_str.split()
    if len(parts) != 2:
        raise ValueError("Invalid time format. Expected format: 'X sec' or 'Y min'")
    value, unit = int(parts[0]), parts[1].lower()
    if unit == 'sec':
        return value
    elif unit == 'min':
        return value * 60
    elif unit == 'days':
        return value * 60 * 60 * 24
    else:
        raise ValueError("Invalid time unit. Expected 'sec' or 'min'")


@router.get("/all")
async def get_all_applications(db: Session = Depends(get_db)) -> List[Application]:
    applications = db.query(DbApplication)
    return applications


@router.post("/")
async def add_application(item: Application, background_tasks: BackgroundTasks, db: Session = Depends(get_db), payload = Depends(get_payload)) -> Application:
    existing_app = db.query(DbApplication).filter(DbApplication.name == item.name).first()
    user = db.query(DbUser).filter(DbUser.keyclockId == payload.get("sub")).first()
    if existing_app:
        raise HTTPException(status_code=400, detail="An application with the same name already exists")

    app = DbApplication(
        name=item.name,
        status="UP",
        baseUrl=item.baseUrl,
        refreshInterval = item.refreshInterval,
        timeToKeep = item.timeToKeep,
        userId = user.uid
    )
    
    db.add(app)
    db.commit()
    
    for endpoint_data in item.endpoints:
        endpoint = DbEndpoint(
            relativeUrl=endpoint_data.relativeUrl,
            status=endpoint_data.status,
            application_id=app.uid
        )
        db.add(endpoint)
    db.commit()
    
    info = DbIpInfo(
        address=get_endpoint_ip(app.baseUrl),
        location="Romania",
        timezone="Bucharest",
        applicationId=app.uid
    )
    db.add(info)
    db.commit()
    
    db.refresh(app)
    
    background_tasks.add_task(monitor_endpoints, app_id=app.uid, refresh_interval=time_to_seconds(app.refreshInterval), time_to_keep=time_to_seconds(app.timeToKeep), db=db)
    
    return app
