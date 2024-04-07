from fastapi import FastAPI, Depends, BackgroundTasks, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from database.database import engine, get_db
from database.models import DbApplication 
from routers import application, user, bug
from auth.auth import get_user_info
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from routers.application import start_monitoring
import httpx
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(user.router)
app.include_router(application.router)
app.include_router(bug.router)

@app.get("/")
def route():
    return("hey")

@app.get("/secure")
async def root(user=Depends(get_user_info)):
    return {"message": f"Hello, {user['username']}!"}



DbApplication.metadata.create_all(engine)

