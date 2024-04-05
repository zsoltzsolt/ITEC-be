from fastapi import APIRouter
from fastapi import Depends
from auth.auth import get_payload
from routers.schemas import UserProfile
from sqlalchemy.orm.session import Session
from database.database import get_db
from database.models import DbUser

router = APIRouter(
    prefix = "/user-profile",
    tags = ["User"]
)

@router.get("/me")
async def get_profile(db: Session = Depends(get_db), payload = Depends(get_payload)) -> UserProfile:
    token = payload.get("sub")
    user = db.query(DbUser).filter(DbUser.keyclockId == token).first()
    if(user is None):
        user = DbUser(
            username = payload.get("preferred_username"),
            keyclockId=payload.get("sub")
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return UserProfile(uid=user.uid, username=user.username, keyclockId=user.keyclockId)