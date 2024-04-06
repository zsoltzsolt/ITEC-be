from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import models
from database.database import engine
from fastapi import Depends
from auth.auth import get_user_info
from routers import application, user

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins = ["*"],
    allow_methods = ["*"],
    allow_headers = ["*"]
)

app.include_router(user.router)
app.include_router(application.router)

@app.get("/")
def route():
    return {"message": "works"}

@app.get("/secure")
async def root(user = Depends(get_user_info)):
    return {"message": "hey"}

models.Base.metadata.create_all(engine)