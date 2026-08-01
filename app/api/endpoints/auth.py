from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings
from app.core.models.user import User, UserCreate, UserLogin, UserResponse
from app.database import get_user_by_username, get_user_by_phone, get_user_by_login, create_user, update_user_role, get_all_users
from app.api.deps import get_current_admin
import uuid
import re

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def validate_phone(phone: str) -> bool:
    pattern = r'^\+7\d{10}$'
    return re.match(pattern, phone) is not None

@router.post("/register")
async def register(user_data: UserCreate):
    if await get_user_by_username(user_data.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    if not validate_phone(user_data.phone):
        raise HTTPException(status_code=400, detail="Invalid phone format. Use +7XXXXXXXXXX")
    
    if await get_user_by_phone(user_data.phone):
        raise HTTPException(status_code=400, detail="Phone already registered")
    
    user_id = str(uuid.uuid4())[:8]
    hashed = pwd_context.hash(user_data.password)
    
    await create_user(user_id, user_data.username, user_data.phone, hashed, role="user")
    
    return UserResponse(
        id=user_id,
        username=user_data.username,
        phone=user_data.phone,
        role="user"
    )

@router.post("/login")
async def login(user_data: UserLogin):
    user = await get_user_by_login(user_data.login)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not pwd_context.verify(user_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    expires = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode(
        {
            "sub": user["id"],
            "username": user["username"],
            "phone": user["phone"],
            "role": user["role"],
            "exp": expires
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": UserResponse(
            id=user["id"],
            username=user["username"],
            phone=user["phone"],
            role=user["role"]
        )
    }

@router.post("/create-admin")
async def create_admin():
    existing_admin = await get_user_by_username("admin")
    if existing_admin:
        raise HTTPException(status_code=400, detail="Admin already exists")
    
    user_id = str(uuid.uuid4())[:8]
    hashed = pwd_context.hash("admin123")
    await create_user(user_id, "admin", "+79998887766", hashed, role="admin")
    
    return {"message": "Admin user created successfully"}

@router.get("/users")
async def list_users(current_user = Depends(get_current_admin)):
    users = await get_all_users()
    return {"users": [dict(user) for user in users]}

@router.put("/users/{username}/role")
async def set_user_role(
    username: str,
    new_role: str,
    current_user = Depends(get_current_admin)
):
    if new_role not in ["admin", "moderator", "user"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    user = await get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await update_user_role(username, new_role)
    return {"message": f"User {username} role updated to {new_role}"}