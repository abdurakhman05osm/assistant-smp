from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class VitalSigns(BaseModel):
    bp_sys: Optional[int] = None
    bp_dia: Optional[int] = None
    heart_rate: Optional[int] = None
    spo2: Optional[int] = None
    temperature: Optional[float] = None

class PatientData(BaseModel):
    age: Optional[int] = None
    sex: Optional[str] = None
    complaints: List[str] = []
    medical_history: Optional[str] = None
    medications: Optional[str] = None
    vitals: VitalSigns = Field(default_factory=VitalSigns)
    status: Dict[str, str] = Field(default_factory=dict)
    extracted_data: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    call_id: Optional[str] = None
    timestamp: Optional[str] = None
    final_diagnosis: Optional[str] = None