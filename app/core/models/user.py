from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    id: str
    username: str
    phone: str  # +7XXXXXXXXXX
    hashed_password: str
    role: str = "user"  # admin / moderator / user

class UserCreate(BaseModel):
    username: str
    phone: str
    password: str

class UserLogin(BaseModel):
    login: str  # может быть username или phone
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    phone: str
    role: str