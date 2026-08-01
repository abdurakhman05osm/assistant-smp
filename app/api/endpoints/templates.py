import os
import shutil
import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.api.deps import get_current_user, get_current_admin, get_current_moderator
from app.core.knowledge.template_loader import TemplateLoader
from app.core.models.template import Template, TemplateVitals

router = APIRouter(prefix="/templates", tags=["templates"])

TEMPLATES_DIR = "templates"
RAW_DIR = os.path.join(TEMPLATES_DIR, "raw")
PARSED_DIR = os.path.join(TEMPLATES_DIR, "parsed")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PARSED_DIR, exist_ok=True)

# Хранилище для шаблонов, добавленных вручную
_loaded_templates = {}

# Путь к базе знаний
DISEASES_JSON_PATH = "knowledge_base/diseases.json"

class ManualTemplateRequest(BaseModel):
    mkb: Optional[str] = None
    diagnosis: str
    complaints: List[str]
    anamnesis: Optional[str] = None
    protocol: str
    severity: str = "medium"

class ManualTemplateResponse(BaseModel):
    id: str
    diagnosis: str
    mkb: Optional[str] = None
    complaints_count: int
    message: str

def load_diseases_from_json():
    """Загружает диагнозы из diseases.json"""
    if os.path.exists(DISEASES_JSON_PATH):
        try:
            with open(DISEASES_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("diseases", [])
        except:
            return []
    return []

@router.post("/upload")
async def upload_template(
    file: UploadFile = File(...),
    current_user = Depends(get_current_moderator)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.txt', '.docx', '.pdf']:
        raise HTTPException(status_code=400, detail="Unsupported file format")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(RAW_DIR, safe_filename)
    
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    template = TemplateLoader.load_from_file(file_path, file.filename)
    if not template:
        raise HTTPException(status_code=400, detail="Failed to parse template")
    
    parsed_path = os.path.join(PARSED_DIR, f"{template.id}.json")
    with open(parsed_path, "w", encoding="utf-8") as f:
        f.write(template.model_dump_json(indent=2))
    
    _loaded_templates[template.id] = template
    
    return {
        "id": template.id,
        "diagnosis": template.diagnosis,
        "mkb": template.icd10,
        "complaints": template.complaints[:5],
        "protocol": template.protocol[:200] + "..." if len(template.protocol) > 200 else template.protocol,
        "source": file.filename,
        "created_at": template.created_at.isoformat(),
        "message": "Template uploaded successfully"
    }

@router.post("/manual", response_model=ManualTemplateResponse)
async def add_template_manual(
    request: ManualTemplateRequest,
    current_user = Depends(get_current_moderator)
):
    if not request.diagnosis:
        raise HTTPException(status_code=400, detail="Diagnosis is required")
    if not request.complaints:
        raise HTTPException(status_code=400, detail="At least one complaint is required")
    
    template_id = str(uuid.uuid4())[:8]
    
    template = Template(
        id=template_id,
        source="manual",
        created_at=datetime.now(),
        diagnosis=request.diagnosis,
        icd10=request.mkb,
        severity=request.severity,
        complaints=request.complaints,
        anamnesis=request.anamnesis,
        protocol=request.protocol,
        vitals=TemplateVitals(),
        raw_text=f"Manual: {request.diagnosis}"
    )
    
    _loaded_templates[template_id] = template
    
    parsed_path = os.path.join(PARSED_DIR, f"{template_id}.json")
    with open(parsed_path, "w", encoding="utf-8") as f:
        f.write(template.model_dump_json(indent=2))
    
    return ManualTemplateResponse(
        id=template_id,
        diagnosis=request.diagnosis,
        mkb=request.mkb,
        complaints_count=len(request.complaints),
        message="Template added successfully"
    )

@router.get("/list")
async def list_templates(current_user = Depends(get_current_user)):
    """Возвращает все диагнозы из diseases.json + добавленные вручную"""
    templates = []
    
    # 1. Добавляем диагнозы из diseases.json
    diseases = load_diseases_from_json()
    for disease in diseases:
        templates.append({
            "id": disease.get("id", "disease_" + str(uuid.uuid4())[:4]),
            "source": "diseases.json",
            "diagnosis": disease.get("name", "Неизвестно"),
            "mkb": disease.get("icd10", ""),
            "severity": disease.get("severity", "medium"),
            "created_at": datetime.now().isoformat(),
            "complaints_count": len(disease.get("symptoms", [])),
            "complaints_text": ", ".join(disease.get("symptoms", [])),
            "anamnesis_text": disease.get("anamnesis", ""),
            "protocol_text": disease.get("protocol", "")
        })
    
    # 2. Добавляем шаблоны, добавленные вручную
    for template in _loaded_templates.values():
        templates.append({
            "id": template.id,
            "source": template.source,
            "diagnosis": template.diagnosis,
            "mkb": template.icd10,
            "severity": template.severity,
            "created_at": template.created_at.isoformat(),
            "complaints_count": len(template.complaints),
            "complaints_text": ", ".join(template.complaints),
            "anamnesis_text": template.anamnesis or "",
            "protocol_text": template.protocol or ""
        })
    
    return {"templates": templates}

@router.get("/{template_id}")
async def get_template(template_id: str, current_user = Depends(get_current_user)):
    # Сначала ищем в diseases.json
    diseases = load_diseases_from_json()
    for disease in diseases:
        if disease.get("id") == template_id:
            return {
                "id": template_id,
                "diagnosis": disease.get("name"),
                "mkb": disease.get("icd10"),
                "severity": disease.get("severity"),
                "complaints": disease.get("symptoms", []),
                "anamnesis": disease.get("anamnesis", ""),
                "protocol": disease.get("protocol", "")
            }
    
    # Если не нашли — ищем вручную добавленные
    template = _loaded_templates.get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@router.put("/{template_id}")
async def update_template(
    template_id: str,
    request: ManualTemplateRequest,
    current_user = Depends(get_current_admin)
):
    if template_id not in _loaded_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = _loaded_templates[template_id]
    template.diagnosis = request.diagnosis
    template.icd10 = request.mkb
    template.complaints = request.complaints
    template.anamnesis = request.anamnesis
    template.protocol = request.protocol
    template.severity = request.severity
    
    parsed_path = os.path.join(PARSED_DIR, f"{template_id}.json")
    with open(parsed_path, "w", encoding="utf-8") as f:
        f.write(template.model_dump_json(indent=2))
    
    return {"message": "Template updated successfully"}

@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    current_user = Depends(get_current_admin)
):
    if template_id not in _loaded_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    del _loaded_templates[template_id]
    
    parsed_path = os.path.join(PARSED_DIR, f"{template_id}.json")
    if os.path.exists(parsed_path):
        os.remove(parsed_path)
    
    return {"message": "Template deleted successfully"}

def get_all_templates():
    """Возвращает все шаблоны для других модулей"""
    return list(_loaded_templates.values())