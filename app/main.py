from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import uuid
from passlib.context import CryptContext

from app.core.config import settings
from app.api.endpoints import auth, templates, process, history
from app.database import init_db, get_user_by_username, create_user

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статика
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключаем роутеры
app.include_router(auth.router)
app.include_router(templates.router)
app.include_router(process.router)
app.include_router(history.router)

@app.on_event("startup")
def startup():
    """Создаём админа при первом запуске"""
    init_db()
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    if not get_user_by_username("admin"):
        user_id = str(uuid.uuid4())[:8]
        hashed = pwd_context.hash("admin123")
        create_user(user_id, "admin", "admin@system.ru", hashed, role="admin")
        print("✅ Admin user created: admin / admin123")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    if os.path.exists("static/index.html"):
        with open("static/index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Assistant SMP</h1><p>Static files not found.</p>"

@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.VERSION}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)