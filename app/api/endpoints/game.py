from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user, get_current_moderator, get_current_admin
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import uuid

router = APIRouter(prefix="/game", tags=["game"])

GAME_FILE = "game_cases.json"

class GameCase(BaseModel):
    id: str
    title: str
    description: str
    options: List[str]
    correct: int
    protocol: str
    mode: str = "diagnostic"

class GameCaseCreate(BaseModel):
    title: str
    description: str
    options: List[str]
    correct: int
    protocol: str
    mode: str = "diagnostic"

def load_cases():
    if os.path.exists(GAME_FILE):
        with open(GAME_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("cases", [])
    return []

def save_cases(cases):
    with open(GAME_FILE, "w", encoding="utf-8") as f:
        json.dump({"cases": cases}, f, ensure_ascii=False, indent=2)

@router.get("/cases")
async def get_cases(mode: Optional[str] = None, current_user = Depends(get_current_user)):
    cases = load_cases()
    if mode:
        cases = [c for c in cases if c.get("mode") == mode]
    return {"cases": cases}

@router.post("/cases")
async def add_case(
    case: GameCaseCreate,
    current_user = Depends(get_current_moderator)
):
    cases = load_cases()
    new_case = {
        "id": str(uuid.uuid4())[:8],
        "title": case.title,
        "description": case.description,
        "options": case.options,
        "correct": case.correct,
        "protocol": case.protocol,
        "mode": case.mode
    }
    cases.append(new_case)
    save_cases(cases)
    return {"message": "Case added successfully", "case": new_case}

@router.delete("/cases/{case_id}")
async def delete_case(
    case_id: str,
    current_user = Depends(get_current_admin)
):
    cases = load_cases()
    new_cases = [c for c in cases if c.get("id") != case_id]
    if len(new_cases) == len(cases):
        raise HTTPException(status_code=404, detail="Case not found")
    save_cases(new_cases)
    return {"message": "Case deleted successfully"}