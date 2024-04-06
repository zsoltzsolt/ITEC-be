from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from routers.schemas import Application
from database.database import get_db
from database.models import DbApplication, DbEndpoint
from typing import List
import asyncio
import time 
import requests
import socket

router = APIRouter(
    prefix="/application",
    tags=["Application"]
)



async def monitor_endpoints(app_id: int, db: Session):
    while True:
        await asyncio.sleep(5) 
        app = db.query(DbApplication).filter(DbApplication.uid == app_id).first()
        if app:
            for endpoint in app.endpoints:
                start_time = time.time()
                response = requests.get(app.baseUrl + endpoint.relativeUrl)
                if response.status_code == 200:
                    response_time = time.time() - start_time
                    print(f"App: {app.name}, Endpoint: {endpoint.relativeUrl}, Response Time: {response_time}")
                else:
                    print(f"App: {app.name}, Endpoint: {endpoint.relativeUrl}, Error: {response.status_code}")
            print()  
        else:
            print(f"App does not exist")
            break   


@router.get("/all")
async def get_all_applications(db: Session = Depends(get_db)) -> List[Application]:
    applications = db.query(DbApplication)
    return applications


@router.post("/")
async def add_application(item: Application, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> Application:
    existing_app = db.query(DbApplication).filter(DbApplication.name == item.name).first()
    if existing_app:
        raise HTTPException(status_code=400, detail="An application with the same name already exists")

    app = DbApplication(
        name=item.name,
        status="UP",
        baseUrl=item.baseUrl,
        ip = get_endpoint_ip(item.baseUrl),
        userId = 1
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
    
    db.refresh(app)
    
    background_tasks.add_task(monitor_endpoints, app_id=app.uid, db=db)
    
    return app
