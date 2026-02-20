# main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from routers import auth, rooms, websockets

app = FastAPI()

# Serve everything in /static at the /static URL path
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(websockets.router)

@app.get("/")
async def get():
    return FileResponse("./static/index.html")

