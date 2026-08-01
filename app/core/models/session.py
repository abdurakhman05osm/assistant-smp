from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.core.models.patient import PatientData

class SessionState(BaseModel):
    session_id: str
    user_id: str
    created_at: str
    updated_at: str
    patient: PatientData = PatientData()
    step: str = "intake"  # intake / questions / diagnosis / documentation
    history: list = []
    template_matches: list = []
    selected_template_id: Optional[str] = None