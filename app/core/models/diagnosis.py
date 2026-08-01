from typing import Optional, List
from pydantic import BaseModel

class DiagnosisResult(BaseModel):
    id: str
    name: str
    probability: float
    matched_symptoms: int
    total_symptoms: int
    protocol: str
    missing_data: List[str] = []
    severity: str = "medium"
    matched_symptom_list: List[str] = []
    missing_symptom_list: List[str] = []
    unknown_symptom_list: List[str] = []
    icd10: Optional[str] = None