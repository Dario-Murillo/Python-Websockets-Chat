# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import users, rooms, websockets

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
                   "http://[::1]:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(rooms.router)
app.include_router(websockets.router)
