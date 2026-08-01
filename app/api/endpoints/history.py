import os
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from app.api.deps import get_current_user
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/history", tags=["history"])

HISTORY_DIR = "history"
os.makedirs(HISTORY_DIR, exist_ok=True)

class CallRecord(BaseModel):
    call_id: str
    timestamp: str
    fio: str
    birth_date: Optional[str] = None
    address: Optional[str] = None
    diagnosis: str
    complaints: List[str] = []
    anamnesis: Optional[str] = None
    protocol: Optional[str] = None
    has_ecg: bool = False
    has_passport: bool = False
    has_oms: bool = False
    has_signature: bool = False

class CallDetailResponse(BaseModel):
    call_id: str
    timestamp: str
    fio: str
    birth_date: Optional[str] = None
    address: Optional[str] = None
    diagnosis: str
    complaints: List[str] = []
    anamnesis: Optional[str] = None
    protocol: Optional[str] = None
    has_ecg: bool = False
    has_passport: bool = False
    has_oms: bool = False
    has_signature: bool = False
    patient_data: dict
    analysis: dict
    final_diagnosis: Optional[str] = None

@router.get("/")
async def get_history(current_user = Depends(get_current_user)):
    """Получить список всех вызовов"""
    calls = []
    try:
        for filename in os.listdir(HISTORY_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(HISTORY_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    calls.append({
                        "call_id": data.get('call_id', ''),
                        "timestamp": data.get('timestamp', ''),
                        "fio": data.get('fio', 'Не указано'),
                        "birth_date": data.get('birth_date', ''),
                        "diagnosis": data.get('diagnosis', 'Не определен'),
                        "has_ecg": data.get('has_ecg', False),
                        "has_passport": data.get('has_passport', False),
                        "has_oms": data.get('has_oms', False),
                        "has_signature": data.get('has_signature', False)
                    })
        calls.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return {"calls": calls}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{call_id}")
async def get_call_detail(call_id: str, current_user = Depends(get_current_user)):
    """Получить полную информацию о вызове по ID"""
    try:
        for filename in os.listdir(HISTORY_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(HISTORY_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('call_id') == call_id:
                        return {
                            "call_id": data.get('call_id'),
                            "timestamp": data.get('timestamp'),
                            "fio": data.get('fio', 'Не указано'),
                            "birth_date": data.get('birth_date', ''),
                            "address": data.get('address', ''),
                            "diagnosis": data.get('diagnosis', 'Не определен'),
                            "complaints": data.get('complaints', []),
                            "anamnesis": data.get('anamnesis', ''),
                            "protocol": data.get('protocol', ''),
                            "has_ecg": data.get('has_ecg', False),
                            "has_passport": data.get('has_passport', False),
                            "has_oms": data.get('has_oms', False),
                            "has_signature": data.get('has_signature', False),
                            "patient_data": data.get('patient', {}),
                            "analysis": data.get('analysis', {}),
                            "final_diagnosis": data.get('final_diagnosis', '')
                        }
        raise HTTPException(status_code=404, detail="Call not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{call_id}")
async def delete_call(call_id: str, current_user = Depends(get_current_user)):
    """Удалить вызов по ID"""
    try:
        for filename in os.listdir(HISTORY_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(HISTORY_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('call_id') == call_id:
                        os.remove(filepath)
                        return {"message": "Call deleted successfully"}
        raise HTTPException(status_code=404, detail="Call not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))