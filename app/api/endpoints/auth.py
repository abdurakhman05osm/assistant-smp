from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings
from app.core.models.user import User, UserCreate, UserLogin, UserResponse
from app.database import get_user_by_username, create_user, init_db, update_user_role, get_all_users
from app.api.deps import get_current_admin
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Инициализация БД при первом импорте
init_db()

def get_user_by_username(username: str):
    return get_user_by_username(username)

@router.post("/register")
async def register(user_data: UserCreate):
    if get_user_by_username(user_data.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    user_id = str(uuid.uuid4())[:8]
    hashed = pwd_context.hash(user_data.password)
    
    create_user(user_id, user_data.username, user_data.email, hashed, role="user")
    
    return UserResponse(
        id=user_id,
        username=user_data.username,
        email=user_data.email,
        role="user"
    )

@router.post("/login")
async def login(user_data: UserLogin):
    user = get_user_by_username(user_data.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not pwd_context.verify(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    expires = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode(
        {
            "sub": user.id,
            "username": user.username,
            "role": user.role,
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
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role
        )
    }

@router.post("/create-admin")
async def create_admin():
    existing_admin = get_user_by_username("admin")
    if existing_admin:
        raise HTTPException(status_code=400, detail="Admin already exists")
    
    user_id = str(uuid.uuid4())[:8]
    hashed = pwd_context.hash("admin123")
    create_user(user_id, "admin", "admin@system.ru", hashed, role="admin")
    
    return {"message": "Admin user created successfully"}

@router.get("/users")
async def list_users(current_user = Depends(get_current_admin)):
    users = get_all_users()
    return {"users": [dict(user) for user in users]}

@router.put("/users/{username}/role")
async def set_user_role(
    username: str,
    new_role: str,
    current_user = Depends(get_current_admin)
):
    if new_role not in ["admin", "moderator", "user"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_user_role(username, new_role)
    return {"message": f"User {username} role updated to {new_role}"}