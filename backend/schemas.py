# schemas.py
from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str

    model_config = {"from_attributes": True}  # allows converting SQLAlchemy models directly

class MessageResponse(BaseModel):
    id: int
    text: str
    user_id: int
    room_id: int
