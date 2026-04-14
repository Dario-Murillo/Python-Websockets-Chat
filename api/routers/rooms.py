from fastapi import APIRouter

router = APIRouter(prefix="/rooms", tags=["rooms"])

@router.get("/")
async def get_rooms():
    return []

@router.post("/")
async def create_room(name: str):
    pass

@router.get("/{room_id}")
async def get_room(room_id: str):
    return None

@router.delete("/{room_id}")
async def delete_room(room_id: str):
    return None