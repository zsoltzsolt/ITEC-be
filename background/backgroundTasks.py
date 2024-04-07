from fastapi import FastAPI, BackgroundTasks, APIRouter
from sqlalchemy.orm import Session
from database.models import DbApplication
from routers.application import monitor_endpoints, time_to_seconds

router = APIRouter(
    prefix="",  
    tags=["Background"]
)
# Start tasks on startup
@router.on_event("startup")
async def startup_event(background_tasks: BackgroundTasks, db: Session = None):
    if db is None:
        raise ValueError("Database session is not provided")

    async def startup_task():
        applications = db.query(DbApplication).all()
        for app in applications:
            background_tasks.add_task(
                monitor_endpoints,
                app_id=app.uid,
                refresh_interval=time_to_seconds(app.refreshInterval),
                time_to_keep=time_to_seconds(app.timeToKeep),
                db=db
            )

    background_tasks.add_task(startup_task)
