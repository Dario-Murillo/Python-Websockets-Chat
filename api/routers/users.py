from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from auth import create_access_token, hash_password, verify_password, get_current_user
from datetime import timedelta
from config import settings
from schemas import UserCreate, UserResponse, Token
from database import get_db
import models

router = APIRouter(prefix="/users", tags=["auth"])

# Create a new user accept username/password, hash the password, store user in DB
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User).where(models.User.username == user.username)
    )
    
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Username taken"
        )
    
    new_user = models.User(
        username = user.username,
        hashed_password = hash_password(user.password)
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

# Verify credentials and return a JWT token
@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], 
    db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(
        select(models.User).where(models.User.username == form_data.username)
    )
    
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    )
    
    return Token(access_token=access_token, token_type="bearer")

# Gets the current active user to validate
@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[models.User, Depends(get_current_user)]
):
    return current_user