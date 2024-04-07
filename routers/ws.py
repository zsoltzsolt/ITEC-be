from fastapi import APIRouter, WebSocket, Depends
from routers.schemas import Application
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import DbApplication, DbEndpointLog
import asyncio
from routers.utils import time_to_seconds, calculate_downtime_minutes
import json


router = APIRouter(
    prefix="/application",
    tags=["Web Socket"]
)


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
                    "bugs": [{"bug_id": bug.uid, "description": bug.description, "timestamp": str(bug.timestamp)} for bug in last_app.bugs],
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