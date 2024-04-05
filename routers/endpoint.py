from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from routers.schemas import Application
from database.database import get_db
from database.models import DbApplication, DbEndpoint

router = APIRouter(
    prefix="/application",
    tags=["User"]
)

@router.post("/")
async def add_application(item: Application, db: Session = Depends(get_db)) -> Application:
    existing_app = db.query(DbApplication).filter(DbApplication.name == item.name).first()
    if existing_app:
        raise HTTPException(status_code=400, detail="An application with the same name already exists")

    app = DbApplication(
        name=item.name,
        status="UP",
        baseUrl=item.baseUrl
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
    
    return app
