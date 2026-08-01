from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    hashed_password: str
    role: str = "user"  # user / admin

class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    role: str