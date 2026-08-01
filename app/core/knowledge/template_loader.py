import os
import uuid
import re
from datetime import datetime
from typing import Optional, List
from app.core.models.template import Template, TemplateVitals

# Поддержка разных форматов
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from docx import Document
except ImportError:
    Document = None

class TemplateLoader:
    @staticmethod
    def load_from_file(file_path: str, original_name: str) -> Optional[Template]:
        """Загружает шаблон из файла (TXT, DOCX, PDF)"""
        ext = os.path.splitext(file_path)[1].lower()
        
        text = None
        if ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        elif ext == '.docx' and Document:
            doc = Document(file_path)
            text = '\n'.join([p.text for p in doc.paragraphs])
        elif ext == '.pdf' and fitz:
            doc = fitz.open(file_path)
            text = '\n'.join([page.get_text() for page in doc])
        else:
            return None
        
        if not text:
            return None
        
        return TemplateLoader._parse_text(text, original_name)
    
    @staticmethod
    def _parse_text(text: str, source: str) -> Template:
        """Парсит текст и извлекает структурированные данные"""
        # Диагноз
        diagnosis = "Неизвестный"
        icd10 = None
        
        diag_patterns = [
            r'(?:Диагноз|Заключительный диагноз|Основной диагноз)\s*[:;]\s*(.+?)(?:\n|$)',
            r'(?:МКБ|ICD)\s*[:;]\s*([A-Za-z0-9\-\.]+)',
        ]
        
        for pattern in diag_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if 'МКБ' in pattern or 'ICD' in pattern:
                    icd10 = match.group(1).strip()
                else:
                    diagnosis = match.group(1).strip()
                break
        
        # Жалобы
        complaints = []
        complaint_patterns = [
            r'(?:Жалобы|Жалобы при поступлении)\s*[:;]\s*(.+?)(?:\n{2,}|$)',
            r'Жалобы\s*(.+?)(?:\n{2,}|$)',
        ]
        for pattern in complaint_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw = match.group(1).strip()
                # Разбиваем на отдельные жалобы
                parts = re.split(r'[,;.]\s*', raw)
                complaints = [p.strip() for p in parts if len(p.strip()) > 3]
                break
        
        # Если жалобы не найдены — берём первые 3 предложения как жалобы
        if not complaints:
            sentences = re.split(r'[.!?]\s+', text)
            complaints = [s.strip() for s in sentences[:3] if len(s.strip()) > 5]
        
        # Анамнез
        anamnesis = None
        anam_pattern = r'(?:Анамнез|Анамнез заболевания|Анамнез жизни)\s*[:;]\s*(.+?)(?:\n{2,}|$)'
        match = re.search(anam_pattern, text, re.IGNORECASE)
        if match:
            anamnesis = match.group(1).strip()
        
        # Протокол
        protocol = ""
        protocol_patterns = [
            r'(?:Протокол|Лечение|Мероприятия|Оказанная помощь)\s*[:;]\s*(.+?)(?:\n{2,}|$)',
            r'(?:Алгоритм|Действия)\s*[:;]\s*(.+?)(?:\n{2,}|$)',
        ]
        for pattern in protocol_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                protocol = match.group(1).strip()
                break
        
        # Витальные показатели
        vitals = TemplateVitals()
        
        # АД
        bp_match = re.search(r'(\d{2,3})\s*[/]\s*(\d{2,3})', text)
        if bp_match:
            vitals.bp_sys = int(bp_match.group(1))
            vitals.bp_dia = int(bp_match.group(2))
        
        # ЧСС
        hr_match = re.search(r'(?:ЧСС|пульс|HR)\s*[:;]?\s*(\d{2,3})', text, re.IGNORECASE)
        if hr_match:
            vitals.heart_rate = int(hr_match.group(1))
        
        # SpO2
        spo2_match = re.search(r'(?:SpO2|сатурация)\s*[:;]?\s*(\d{2,3})', text, re.IGNORECASE)
        if spo2_match:
            vitals.spo2 = int(spo2_match.group(1))
        
        # Температура
        temp_match = re.search(r'(?:температура|t)\s*[:;]?\s*(\d{2,3}\.?\d*)', text, re.IGNORECASE)
        if temp_match:
            vitals.temperature = float(temp_match.group(1))
        
        # Возраст и пол (если есть)
        age = None
        sex = None
        
        age_match = re.search(r'(\d{1,3})\s*(?:лет|год|года)', text)
        if age_match:
            age = int(age_match.group(1))
        
        sex_match = re.search(r'\b(муж|мужчина|male|жен|женщина|female)\b', text, re.IGNORECASE)
        if sex_match:
            s = sex_match.group(1).lower()
            if s in ['муж', 'мужчина', 'male']:
                sex = 'male'
            else:
                sex = 'female'
        
        # Определяем severity по ключевым словам
        severity = "medium"
        critical_keywords = ['критическое', 'жизнеугрожающее', 'неотложное', 'инфаркт', 'инсульт', 'шок']
        high_keywords = ['тяжёлый', 'высокий риск', 'экстренный']
        
        text_lower = text.lower()
        if any(kw in text_lower for kw in critical_keywords):
            severity = "critical"
        elif any(kw in text_lower for kw in high_keywords):
            severity = "high"
        
        return Template(
            id=str(uuid.uuid4())[:8],
            source=source,
            created_at=datetime.now(),
            diagnosis=diagnosis,
            icd10=icd10,
            severity=severity,
            complaints=complaints,
            anamnesis=anamnesis,
            vitals=vitals,
            protocol=protocol,
            age_min=age-5 if age else None,
            age_max=age+5 if age else None,
            sex=sex,
            raw_text=text[:2000]  # сохраняем только начало для отладки
        )