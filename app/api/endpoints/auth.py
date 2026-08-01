from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings
from app.core.models.user import User, UserCreate, UserLogin, UserResponse
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Временное хранилище пользователей (потом заменим на БД)
_users_db = {}

def get_user_by_username(username: str):
    for u in _users_db.values():
        if u.username == username:
            return u
    return None

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    if get_user_by_username(user_data.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    user_id = str(uuid.uuid4())[:8]
    hashed = pwd_context.hash(user_data.password)
    
    user = User(
        id=user_id,
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed,
        role="user"
    )
    _users_db[user_id] = user
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role
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