import os
import asyncpg
from datetime import datetime
from typing import Optional, List, Dict, Any

DATABASE_URL = os.environ.get("DATABASE_URL")

async def get_db():
    conn = await asyncpg.connect(DATABASE_URL)
    return conn

async def init_db():
    conn = await get_db()
    try:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TEXT
            )
        ''')
    finally:
        await conn.close()

async def get_user_by_username(username: str):
    conn = await get_db()
    try:
        row = await conn.fetchrow("SELECT * FROM users WHERE username = $1", username)
        return dict(row) if row else None
    finally:
        await conn.close()

async def get_user_by_phone(phone: str):
    conn = await get_db()
    try:
        row = await conn.fetchrow("SELECT * FROM users WHERE phone = $1", phone)
        return dict(row) if row else None
    finally:
        await conn.close()

async def get_user_by_login(login: str):
    if login.startswith('+'):
        return await get_user_by_phone(login)
    else:
        return await get_user_by_username(login)

async def create_user(user_id: str, username: str, phone: str, hashed_password: str, role: str = 'user'):
    conn = await get_db()
    try:
        await conn.execute('''
            INSERT INTO users (id, username, phone, hashed_password, role, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        ''', user_id, username, phone, hashed_password, role, datetime.now().isoformat())
    finally:
        await conn.close()

async def update_user_role(username: str, new_role: str):
    conn = await get_db()
    try:
        await conn.execute("UPDATE users SET role = $1 WHERE username = $2", new_role, username)
    finally:
        await conn.close()

async def get_all_users():
    conn = await get_db()
    try:
        rows = await conn.fetch("SELECT id, username, phone, role, created_at FROM users")
        return [dict(row) for row in rows]
    finally:
        await conn.close()