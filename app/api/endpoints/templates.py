import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.api.deps import get_current_user
from app.core.knowledge.template_loader import TemplateLoader
from app.core.models.template import Template, TemplateMatch

router = APIRouter(prefix="/templates", tags=["templates"])

TEMPLATES_DIR = "templates"
RAW_DIR = os.path.join(TEMPLATES_DIR, "raw")
PARSED_DIR = os.path.join(TEMPLATES_DIR, "parsed")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PARSED_DIR, exist_ok=True)

# Временное хранилище загруженных шаблонов
_loaded_templates = {}

# ===== МОДЕЛИ ДЛЯ РУЧНОГО ДОБАВЛЕНИЯ =====
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

# ===== ЗАГРУЗКА ФАЙЛОВ =====
@router.post("/upload")
async def upload_template(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """Загрузка шаблона из файла (PDF, DOCX, TXT)"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.txt', '.docx', '.pdf']:
        raise HTTPException(status_code=400, detail="Unsupported file format. Use TXT, DOCX, or PDF.")
    
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
        "message": "Template uploaded and parsed successfully"
    }

# ===== РУЧНОЕ ДОБАВЛЕНИЕ =====
@router.post("/manual", response_model=ManualTemplateResponse)
async def add_template_manual(
    request: ManualTemplateRequest,
    current_user = Depends(get_current_user)
):
    """Добавление шаблона вручную (без файла)"""
    if not request.diagnosis:
        raise HTTPException(status_code=400, detail="Diagnosis is required")
    if not request.complaints:
        raise HTTPException(status_code=400, detail="At least one complaint is required")
    
    template_id = str(uuid.uuid4())[:8]
    
    # Создаём объект шаблона
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
        vitals=TemplateVitals(),  # пустые витальные
        raw_text=f"Ручное добавление: {request.diagnosis}"
    )
    
    # Сохраняем в память
    _loaded_templates[template_id] = template
    
    # Сохраняем в файл
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

# ===== СПИСОК ШАБЛОНОВ =====
@router.get("/list")
async def list_templates(current_user = Depends(get_current_user)):
    """Список всех загруженных шаблонов"""
    templates = []
    for template in _loaded_templates.values():
        templates.append({
            "id": template.id,
            "source": template.source,
            "diagnosis": template.diagnosis,
            "mkb": template.icd10,
            "severity": template.severity,
            "created_at": template.created_at.isoformat(),
            "complaints_count": len(template.complaints)
        })
    return {"templates": templates}

# ===== ПОЛУЧЕНИЕ ШАБЛОНА ПО ID =====
@router.get("/{template_id}")
async def get_template(template_id: str, current_user = Depends(get_current_user)):
    """Получение шаблона по ID"""
    template = _loaded_templates.get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

# ===== УДАЛЕНИЕ ШАБЛОНА =====
@router.delete("/{template_id}")
async def delete_template(template_id: str, current_user = Depends(get_current_user)):
    """Удаление шаблона по ID"""
    if template_id not in _loaded_templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    del _loaded_templates[template_id]
    
    # Удаляем файл, если он есть
    parsed_path = os.path.join(PARSED_DIR, f"{template_id}.json")
    if os.path.exists(parsed_path):
        os.remove(parsed_path)
    
    return {"message": "Template deleted successfully"}

# ===== ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ДРУГИХ МОДУЛЕЙ =====
def get_all_templates():
    """Возвращает все загруженные шаблоны"""
    return list(_loaded_templates.values())