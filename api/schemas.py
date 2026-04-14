# schemas.py
from pydantic import BaseModel, Field, ConfigDict

class UserBase(BaseModel):
    id: int
    username: str = Field(min_length=1, max_length=50)

class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=8, max_length=20)

class UserResponse(UserBase):

    model_config = ConfigDict(from_attributes=True)     # allows converting SQLAlchemy models directly

class Token(BaseModel):
    access_token: str
    token_type: str
    
class MessageResponse(BaseModel):
    id: int
    text: str
    user_id: int
    room_id: int
