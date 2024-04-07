from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, WebSocket
from sqlalchemy.orm import Session
from routers.schemas import Application, UserProfile, Endpoint
from database.database import get_db
from database.models import DbApplication, DbEndpoint, DbIpInfo, DbUser, DbEndpointLog
from typing import List
import asyncio
import time 
import requests
import socket
from auth.auth import get_payload
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import joinedload
import json
from routers.utils import get_endpoint_status_ratio, determine_stability, calculate_downtime_minutes, time_to_seconds
from datetime import datetime, timedelta

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



async def monitor_endpoints(app_id: int, refresh_interval: int, time_to_keep: int, db: Session):
    while True:
        try:
            await asyncio.sleep(refresh_interval)
            app = db.query(DbApplication).filter(DbApplication.uid == app_id).first()
            if app:
                endpoint_statuses = []
                
                for endpoint in app.endpoints:
                    status = 200  
                    relativeUrl = endpoint.relativeUrl
                    if relativeUrl[0] == '/':
                        relativeUrl = relativeUrl[1:]
                    path = "https://" + app.baseUrl + "/" + relativeUrl
                    response_time = .001
                    try:
                        response = requests.get(path)
                        response.raise_for_status()
                        response_time = response.elapsed.total_seconds()
                        status = response.status_code
                    except requests.RequestException as e:
                        response_time = 0
                        status = 500  
                    
                    log = DbEndpointLog(
                        responseTime=response_time,
                        status=status,
                        endpointId=endpoint.uid,
                    )
                    db.add(log)
                    
                    endpoint_statuses.append(status)
                    # Determine the stability of each endpoint 
                    endpoint.status = determine_stability(endpoint.uid, db)
                # The app is stable if 
                app.status = "Stable" if all(endpoint.status == "Stable" for endpoint in app.endpoints) else "Unstable" if any(endpoint.status in ["Unstable"] for endpoint in app.endpoints) else "Down"
                if app.bugs and app.status == "Unstable":
                    app.status = "Down"
                else:
                    app.status = "Unstable"
                db.add(app)
                db.commit()
                db.refresh(app)
                
                # Delete old logs
                oldest_allowed_time = current_time - timedelta(seconds=time_to_keep)
                db.query(DbEndpointLog).filter(
                    DbEndpointLog.timestamp < oldest_allowed_time,
                    DbEndpointLog.endpointId.in_([ep.uid for ep in app.endpoints])
                ).delete()
                db.commit()
            else:
                print(f"App does not exist")
                break
        except Exception as e:
            print(f"An error occurred: {e}")
            # If an error occurs, set application status to Down
            if app:
                app.status = "Down"
                db.add(app)
                db.commit()
                db.refresh(app)
            continue




async def monitor_and_start(app_id: int, refresh_interval: int, time_to_keep: int, db: Session):
    await monitor_endpoints(app_id, refresh_interval, time_to_keep, db)

# Endpoint to start monitoring all endpoints
@router.post("/start")
async def start_monitoring(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    applications = db.query(DbApplication).all()
    tasks = []
    for app in applications:
        print(f"{app.name} started")
        task = monitor_and_start(
            app_id=app.uid,
            refresh_interval=time_to_seconds(app.refreshInterval),
            time_to_keep=time_to_seconds(app.timeToKeep),
            db=db
        )
        tasks.append(task)
    await asyncio.gather(*tasks)
    return {"message": "Monitoring started for all applications."}

        


# Add application
@router.post("/")
async def add_application(item: Application, background_tasks: BackgroundTasks, db: Session = Depends(get_db), payload = Depends(get_payload)) -> Application:
    existing_app = db.query(DbApplication).filter(DbApplication.name == item.name).first()
    user = db.query(DbUser).filter(DbUser.keyclockId == payload.get("sub")).first()
    if existing_app:
        raise HTTPException(status_code=400, detail="An application with the same name already exists")

    app = DbApplication(
        name=item.name,
        status="Stable",
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
            applicationId=app.uid
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

# Fetch all applications
@router.get("/all")
async def get_all_applications(db: Session = Depends(get_db)) -> List[Application]:
    applications = db.query(DbApplication)
    return applications


# Search for a particular application
@router.get("/search")
def search_application(query: str, db: Session = Depends(get_db)):
    string = f"%{query}%"  
    apps = db.query(DbApplication).filter(or_(func.lower(DbApplication.baseUrl).like(string.lower()), func.lower(DbApplication.name).like(string.lower()))).all()
    return apps


# Fetch data of a particular application
@router.get("/{id}")
def get_application(id: int, db: Session = Depends(get_db)) -> Application:
    app = db.query(DbApplication).options(
        joinedload(DbApplication.endpoints).joinedload(DbEndpoint.log)
    ).filter(DbApplication.uid == id).first()
    
    if app:
        for endpoint in app.endpoints:
            endpoint.log.sort(key=lambda x: x.timestamp, reverse=True)
        return app
    raise HTTPException(status_code=400, detail="App with this id does not exist")

# Convert to SQLAlchemy format
def pydantic_to_db_endpoint(endpoint: Endpoint) -> DbEndpoint:
    db_endpoint = DbEndpoint(
        uid=endpoint.uid,
        relativeUrl=endpoint.relativeUrl,
        status=endpoint.status,
        applicationId=endpoint.applicationId
    )
    db_logs = []
    for log in endpoint.log:
        db_log = DbEndpointLog(
            uid=log.uid,
            responseTime=log.responseTime,
            status=log.status,
            endpointId=log.endpointId,
            timestamp=log.timestamp
        )
        db_logs.append(db_log)
    
    db_endpoint.log = db_logs

    return db_endpoint  


# Edit application
@router.put("/{id}")
def edit_application(id: int, item: Application, db: Session = Depends(get_db)) -> Application:
    app = db.query(DbApplication).options(joinedload(DbApplication.endpoints)).filter(DbApplication.uid == id).first()
    if app:
        app.name = item.name
        app.endpoints = [pydantic_to_db_endpoint(endpoint) for endpoint in item.endpoints]
        app.baseUrl = item.baseUrl
        app.refreshInterval = item.refreshInterval
        app.timeToKeep = item.timeToKeep
        db.commit()
        return app
    else:
        raise HTTPException(status_code=400, detail="App with this id does not exist")


# Delete application
@router.delete("/{id}")
def delete_application(id: int, db: Session = Depends(get_db)):
    print(f"{id}")
    db.query(DbApplication).filter(DbApplication.uid == id).delete()
    db.commit()
    return {"message": "deleted"}


# Get the status ratio of a particular endpoint
@router.get("/ratio/{id}")
def get_ratio(id: int, db: Session = Depends(get_db)):
    return get_endpoint_status_ratio(id, db)