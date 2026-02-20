from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
async def register():
    # Will accept username/password, hash the password, store user in DB
    pass

@router.post("/login")
async def login():
    # Will verify credentials and return a JWT token
    pass

@router.post("/logout")
async def logout():
    # Will invalidate the token
    pass