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

router = APIRouter(
    prefix="/application",
    tags=["Application"]
)

from datetime import datetime, timedelta

def calculate_downtime_minutes(app: Application) -> float:
    total_downtime = 0.0
    
    for endpoint in app.endpoints:
        for log in endpoint.log:
            if log.status != '200':
                downtime_start = log.timestamp
                downtime_end = downtime_start
                
                for subsequent_log in endpoint.log:
                    if subsequent_log.timestamp > downtime_end:
                        if subsequent_log.status == '200':
                            break
                        else:
                            downtime_end = subsequent_log.timestamp
                
                if downtime_end > downtime_start:
                    downtime_duration = (downtime_end - downtime_start).total_seconds() / 60.0
                    total_downtime += downtime_duration
    
    return total_downtime


    


def time_to_seconds(time_str: str) -> int:
    parts = time_str.split()
    if len(parts) != 2:
        raise ValueError("Invalid time format. Expected format: 'X sec' or 'Y min'")
    value, unit = int(parts[0]), parts[1].lower()
    if unit == 'sec':
        return value
    elif unit == 'min':
        return value * 60
    elif unit == 'hours':
        return value * 60 * 60
    elif unit == 'days':
        return value * 60 * 60 * 24
    elif unit == 'day':
        return value * 60 * 60 * 24
    else:
        raise ValueError("Invalid time unit. Expected 'sec' or 'min'")

@router.websocket("/{id}")
async def websocket_endpoint(id: int, websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    while True:
        try:
            last_app: Application = db.query(DbApplication).filter(DbApplication.uid == id).order_by(DbApplication.uid.desc()).first()
            db.refresh(last_app)
            refreshInterval = last_app.refreshInterval
            await asyncio.sleep(0.95 * time_to_seconds(refreshInterval))
        
            if last_app:
                app_data = {
                    "uid": last_app.uid,
                    "name": last_app.name,
                    "status": last_app.status,
                    "baseUrl": last_app.baseUrl,
                    "downTime": calculate_downtime_minutes(last_app),
                    "ipInfo": {
                        "uid": last_app.ipInfo.uid,
                        "address": last_app.ipInfo.address,
                        "location": last_app.ipInfo.location,
                        "timezone": last_app.ipInfo.timezone,
                        "applicationId": last_app.ipInfo.applicationId
                    },
                    "refreshInterval": f"{refreshInterval}",
                    "timeToKeep": f"{last_app.timeToKeep}",
                    "userId": last_app.userId,
                    "bugs": [{"bug_id": bug.uid, "description": bug.description} for bug in last_app.bugs],
                    "endpoints": []
                }
            
                for endpoint in last_app.endpoints:
                    endpoint_data = {
                        "uid": endpoint.uid,
                        "relativeUrl": endpoint.relativeUrl,
                        "status": "",
                        "applicationId": endpoint.applicationId,
                        "log": []
                    }
                
                    latest_log = db.query(DbEndpointLog).filter(DbEndpointLog.endpointId == endpoint.uid).order_by(DbEndpointLog.timestamp.desc()).first()
                
                    if latest_log:
                        log_data = {
                            "uid": latest_log.uid,
                            "responseTime": latest_log.responseTime,
                            "status": latest_log.status,
                            "endpointId": latest_log.endpointId,
                            "timestamp": latest_log.timestamp.isoformat()
                        }
                        endpoint_data["log"].append(log_data)
                
                    app_data["endpoints"].append(endpoint_data)
            
                app_json = json.dumps(app_data)
            

                await websocket.send_text(app_json)
            else:
                await websocket.send_text("Application not found")
                
        except Exception as e:
            continue
            


def get_endpoint_ip(url: str) -> str:
    try:
        print(f"{url}")
        ip_address = socket.gethostbyname(url)
        return ip_address
    except socket.gaierror:
        return "IP not found"

def determine_stability(endpointId: int, db: Session):
    endpoint = db.query(DbEndpoint).options(joinedload(DbEndpoint.log)).filter(DbEndpoint.uid == endpointId).first()
    if endpoint:
        log_statuses = [log.status for log in endpoint.log[-10:]] 
        print(log_statuses)
        if all(status in ['200', '302'] for status in log_statuses):
            return "Stable"
        elif all(status not in ['200', '302'] for status in log_statuses):
            return "Down"
        else:
            return "Unstable"
    else:
        return "Endpoint not found"


# Function to monitor endpoints and update their status
async def monitor_endpoints(app_id: int, refresh_interval: int, time_to_keep: int, db: Session):
    while True:
        try:
            await asyncio.sleep(refresh_interval)
            app = db.query(DbApplication).filter(DbApplication.uid == app_id).first()
            if app:
                current_time = datetime.utcnow()
                endpoint_statuses = []
                
                for endpoint in app.endpoints:
                    status = 200  # Default status
                    relativeUrl = endpoint.relativeUrl
                    if relativeUrl[0] == '/':
                        relativeUrl = relativeUrl[1:]
                    path = "https://" + app.baseUrl + "/" + relativeUrl
                    response_time = .001
                    start_time = current_time
                    try:
                        response = requests.get(path)
                        response.raise_for_status()
                        response_time = response.elapsed.total_seconds()
                        status = response.status_code
                    except requests.RequestException as e:
                        # If there's an exception, consider the status as 500
                        response_time = 0
                        status = 500  
                    
                    # Update endpoint log
                    log = DbEndpointLog(
                        responseTime=response_time,
                        status=status,
                        endpointId=endpoint.uid,
                        timestamp=start_time
                    )
                    db.add(log)
                    
                    # Append status to the list of endpoint statuses
                    endpoint_statuses.append(status)
                    
                    # Determine stability of the endpoint
                    endpoint.status = determine_stability(endpoint.uid, db)
                
                # Update application status based on the collective statuses of endpoints
                app.status = "Stable" if all(endpoint.status == "Stable" for endpoint in app.endpoints) else "Unstable" if any(endpoint.status in ["Unstable", "Down"] for endpoint in app.endpoints) else "Down"
                if app.bugs:
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
            # If an error occurs, set application status to "Down"
            if app:
                app.status = "Down"
                db.add(app)
                db.commit()
                db.refresh(app)
            continue




async def monitor_and_start(app_id: int, refresh_interval: int, time_to_keep: int, db: Session):
    await monitor_endpoints(app_id, refresh_interval, time_to_keep, db)

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


@router.get("/search")
def search_application(query: str, db: Session = Depends(get_db)):
    string = f"%{query}%"  
    apps = db.query(DbApplication).filter(or_(func.lower(DbApplication.baseUrl).like(string.lower()), func.lower(DbApplication.name).like(string.upper()))).all()
    return apps


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


def pydantic_to_db_endpoint(endpoint: Endpoint) -> DbEndpoint:
    db_endpoint = DbEndpoint(
        uid=endpoint.uid,
        relativeUrl=endpoint.relativeUrl,
        status=endpoint.status,
        applicationId=endpoint.applicationId
    )

    # Convert Pydantic logs to SQLAlchemy logs
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



@router.delete("/{id}")
def delete_application(id: int, db: Session = Depends(get_db)):
    print(f"{id}")
    db.query(DbApplication).filter(DbApplication.uid == id).delete()
    db.commit()
    return {"message": "deleted"}