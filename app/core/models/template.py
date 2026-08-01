from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class TemplateVitals(BaseModel):
    bp_sys: Optional[int] = None
    bp_dia: Optional[int] = None
    heart_rate: Optional[int] = None
    spo2: Optional[int] = None
    temperature: Optional[float] = None

class Template(BaseModel):
    id: str
    source: str                      # имя файла
    created_at: datetime
    diagnosis: str
    icd10: Optional[str] = None
    severity: str = "medium"         # critical / high / medium / low
    
    complaints: List[str] = []
    anamnesis: Optional[str] = None
    vitals: TemplateVitals = TemplateVitals()
    protocol: str = ""
    treatment: Optional[str] = None
    
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    sex: Optional[str] = None       # male / female / any
    
    raw_text: Optional[str] = None   # оригинальный текст для отладки

class TemplateMatch(BaseModel):
    template_id: str
    score: int
    diagnosis: str
    complaints: List[str]
    protocol: str
    similarity: int  # процент совпадения
    severity: str