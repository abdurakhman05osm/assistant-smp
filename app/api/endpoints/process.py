from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user
from app.core.models.patient import PatientData, VitalSigns
from app.core.engines.parser_engine import ParserEngine
from app.core.engines.medical_engine import MedicalEngine
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import json
import os
import re
from datetime import datetime

router = APIRouter(prefix="/api", tags=["process"])

# ===== МОДЕЛИ =====
class ParseRequest(BaseModel):
    text: str

class ParseResponse(BaseModel):
    patient: PatientData
    raw_text: str
    extracted_fields: List[str]
    analysis: Optional[Dict[str, Any]] = None

class AddDataRequest(BaseModel):
    text: str
    question: str
    answer: str
    patient: PatientData

class AddDataResponse(BaseModel):
    patient: PatientData
    analysis: Dict[str, Any]
    extracted_fields: List[str]

class SaveCallRequest(BaseModel):
    patient: PatientData
    analysis: Dict[str, Any]
    final_diagnosis: Optional[str] = None
    fio: Optional[str] = None
    birth_date: Optional[str] = None
    address: Optional[str] = None
    has_ecg: bool = False
    has_passport: bool = False
    has_oms: bool = False
    has_signature: bool = False

class SaveCallResponse(BaseModel):
    success: bool
    call_id: str
    file_path: str

# ===== ПАРСИНГ =====
@router.post("/parse", response_model=ParseResponse)
async def parse_text(
    request: ParseRequest,
    current_user = Depends(get_current_user)
):
    """Извлечение данных из текста и анализ"""
    try:
        patient_data = ParserEngine.parse(request.text)
        analysis = MedicalEngine.diagnose(patient_data)
        extracted = [key for key, val in patient_data.status.items() if val == 'EXTRACTED']
        
        return ParseResponse(
            patient=patient_data,
            raw_text=request.text,
            extracted_fields=extracted,
            analysis=analysis
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== ДОБАВЛЕНИЕ ДАННЫХ =====
@router.post("/add_data", response_model=AddDataResponse)
async def add_data(
    request: AddDataRequest,
    current_user = Depends(get_current_user)
):
    """Добавление ответа на уточняющий вопрос с пересчётом"""
    try:
        patient = request.patient
        answer = request.answer.strip()
        question = request.question.strip()
        
        patient = _process_answer(patient, question, answer)
        analysis = MedicalEngine.diagnose(patient)
        extracted = [key for key, val in patient.status.items() if val in ['EXTRACTED', 'VERIFIED']]
        
        return AddDataResponse(
            patient=patient,
            analysis=analysis,
            extracted_fields=extracted
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== СОХРАНЕНИЕ ВЫЗОВА =====
@router.post("/save_call", response_model=SaveCallResponse)
async def save_call(
    request: SaveCallRequest,
    current_user = Depends(get_current_user)
):
    """Сохранение вызова в историю с ФИО, датой рождения и документами"""
    try:
        call_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        HISTORY_DIR = "history"
        os.makedirs(HISTORY_DIR, exist_ok=True)
        
        diagnosis = "Не определен"
        protocol = ""
        if request.analysis and request.analysis.get('possible_diagnoses'):
            top = request.analysis['possible_diagnoses'][0]
            diagnosis = top.get('name', 'Не определен')
            protocol = top.get('protocol', '')
        
        call_data = {
            "call_id": call_id,
            "timestamp": timestamp,
            "fio": request.fio or "Не указано",
            "birth_date": request.birth_date or "",
            "address": request.address or "",
            "diagnosis": diagnosis,
            "protocol": protocol,
            "complaints": request.patient.complaints or [],
            "anamnesis": request.patient.medical_history or "",
            "final_diagnosis": request.final_diagnosis or "",
            "has_ecg": request.has_ecg,
            "has_passport": request.has_passport,
            "has_oms": request.has_oms,
            "has_signature": request.has_signature,
            "patient": request.patient.dict(),
            "analysis": request.analysis
        }
        
        filename = f"{timestamp}_{call_id}.json"
        filepath = os.path.join(HISTORY_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(call_data, f, ensure_ascii=False, indent=2)
        
        return SaveCallResponse(
            success=True,
            call_id=call_id,
            file_path=filepath
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def _process_answer(patient: PatientData, question: str, answer: str) -> PatientData:
    """Обработка ответа на вопрос и обновление данных пациента"""
    question_lower = question.lower()
    answer_lower = answer.lower()
    
    # Проверяем, является ли ответ числом
    is_number = False
    numeric_value = None
    try:
        temp_answer = re.sub(r'[^\d.]', '', answer)
        if temp_answer:
            numeric_value = float(temp_answer)
            is_number = True
    except:
        pass
    
    # Если ответ - число, обновляем витальные показатели
    if is_number and numeric_value is not None:
        if 'давление' in question_lower or 'ад' in question_lower:
            if '/' in answer:
                parts = answer.split('/')
                if len(parts) == 2:
                    try:
                        patient.vitals.bp_sys = int(parts[0].strip())
                        patient.vitals.bp_dia = int(parts[1].strip())
                        patient.status['bp'] = 'VERIFIED'
                        patient.extracted_data['bp'] = {
                            'value': f"{patient.vitals.bp_sys}/{patient.vitals.bp_dia}",
                            'icon': '🫀',
                            'label': 'Артериальное давление'
                        }
                    except:
                        pass
        elif 'пульс' in question_lower or 'чсс' in question_lower:
            hr_value = int(numeric_value)
            if hr_value > 250:
                hr_value = 250
            patient.vitals.heart_rate = hr_value
            patient.status['hr'] = 'VERIFIED'
            patient.extracted_data['hr'] = {
                'value': patient.vitals.heart_rate,
                'icon': '❤️',
                'label': 'ЧСС (пульс)'
            }
        elif 'сатурация' in question_lower or 'spo2' in question_lower:
            patient.vitals.spo2 = int(numeric_value)
            patient.status['spo2'] = 'VERIFIED'
            patient.extracted_data['spo2'] = {
                'value': f"{patient.vitals.spo2}%",
                'icon': '🫁',
                'label': 'Сатурация (SpO₂)'
            }
        elif 'температура' in question_lower or 't' in question_lower:
            patient.vitals.temperature = numeric_value
            patient.status['temperature'] = 'VERIFIED'
            patient.extracted_data['temperature'] = {
                'value': f"{patient.vitals.temperature}°C",
                'icon': '🌡️',
                'label': 'Температура'
            }
        elif 'глюкоза' in question_lower:
            if answer_lower not in ['нет', 'не знаю']:
                glucose_value = f"Глюкоза: {numeric_value} ммоль/л"
                if patient.medical_history:
                    history_parts = patient.medical_history.split('; ')
                    new_parts = [p for p in history_parts if not p.startswith('Глюкоза:')]
                    new_parts.append(glucose_value)
                    patient.medical_history = '; '.join(new_parts)
                else:
                    patient.medical_history = glucose_value
    
    # Текстовые ответы (всегда добавляем в анамнез, а не в жалобы!)
    else:
        answer_text = f"{question}: {answer}"
        
        # Ключевые слова для анамнеза
        anamnesis_keywords = ['диабет', 'антикоагулянт', 'варфарин', 'ксарелто', 'аспирин', 'препарат', 
                              'аллергия', 'давление', 'сердечный', 'гипертония', 'ишемия', 'инфаркт', 'инсульт',
                              'беременность', 'операция', 'травма', 'хронический', 'заболевание', 'лекарство',
                              'принимает', 'была ли', 'есть ли', 'были ли', 'принимал']
        
        # Все ответы на вопросы идут в анамнез
        is_anamnesis = any(kw in question_lower for kw in anamnesis_keywords) or answer_lower in ['да', 'нет', 'не знаю']
        
        if is_anamnesis:
            if patient.medical_history:
                patient.medical_history += f"; {answer_text}"
            else:
                patient.medical_history = answer_text
        else:
            # Только если это точно не вопрос - добавляем в жалобы
            if answer not in patient.complaints:
                patient.complaints.append(answer)
    
    return patient