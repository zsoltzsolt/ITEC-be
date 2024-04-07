from fastapi import APIRouter
from sqlalchemy.orm import Session
from fastapi import Depends
from auth.auth import get_db
from routers.schemas import Bug
from database.models import DbBug

router = APIRouter(
    prefix="/bug",
    tags=["BUG"]
)

@router.post("/")
def add_bug(item: Bug, db: Session = Depends(get_db)):
    bug = DbBug(
        description = item.description,
        applicationId = item.applicationId
    )
    db.add(bug)
    db.commit()
    
@router.delete("/{id}")
def delete_bug(id: int, db: Session = Depends(get_db)):
    db.query(DbBug).filter(DbBug.uid == id).delete()
    db.commit()
    return {"message": "deleted"}