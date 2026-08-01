import re
from typing import Dict, Any
from app.core.models.patient import PatientData, VitalSigns

class ParserEngine:
    @staticmethod
    def parse(text: str) -> PatientData:
        patient = PatientData()
        vitals = VitalSigns()
        status_map = {}
        extracted_data = {}

        # 1. Извлечение возраста
        age_match = re.search(r'(\d{1,3})\s*(?:лет|год|года|years?)', text, re.IGNORECASE)
        if age_match:
            patient.age = int(age_match.group(1))
            status_map['age'] = 'EXTRACTED'
            extracted_data['age'] = {'value': f"{patient.age} лет", 'icon': '📅', 'label': 'Возраст'}
        else:
            status_map['age'] = 'UNKNOWN'

        # 2. Извлечение пола
        sex_match = re.search(r'\b(муж|мужчина|male|жен|женщина|female)\b', text, re.IGNORECASE)
        if sex_match:
            sex = sex_match.group(1).lower()
            if sex in ['муж', 'мужчина', 'male']:
                patient.sex = 'male'
                extracted_data['sex'] = {'value': 'Мужской', 'icon': '👨', 'label': 'Пол'}
            else:
                patient.sex = 'female'
                extracted_data['sex'] = {'value': 'Женский', 'icon': '👩', 'label': 'Пол'}
            status_map['sex'] = 'EXTRACTED'
        else:
            status_map['sex'] = 'UNKNOWN'

        # 3. Извлечение АД
        bp_patterns = [
            r'(\d{2,3})\s*/\s*(\d{2,3})',
            r'(\d{2,3})\s*на\s*(\d{2,3})',
            r'(\d{2,3})\s*-\s*(\d{2,3})',
            r'АД\s*[:]?\s*(\d{2,3})\s*[/]\s*(\d{2,3})',
            r'давление\s*[:]?\s*(\d{2,3})\s*[/]\s*(\d{2,3})',
        ]
        
        bp_found = False
        for pattern in bp_patterns:
            bp_match = re.search(pattern, text, re.IGNORECASE)
            if bp_match:
                vitals.bp_sys = int(bp_match.group(1))
                vitals.bp_dia = int(bp_match.group(2))
                status_map['bp'] = 'EXTRACTED'
                extracted_data['bp'] = {
                    'value': f"{vitals.bp_sys}/{vitals.bp_dia}", 
                    'icon': '🫀', 
                    'label': 'Артериальное давление'
                }
                bp_found = True
                break
        
        if not bp_found:
            status_map['bp'] = 'UNKNOWN'

        # 4. Извлечение ЧСС (с ограничением 250)
        hr_patterns = [
            r'(?:пульс|ЧСС|heart rate)\s*[:]?\s*(\d{2,3})',
            r'пульс\s+(\d{2,3})',
            r'ЧСС\s+(\d{2,3})',
            r'ЧСС\s*[:]?\s*(\d{2,3})',
        ]
        
        hr_found = False
        for pattern in hr_patterns:
            hr_match = re.search(pattern, text, re.IGNORECASE)
            if hr_match:
                hr_value = int(hr_match.group(1))
                if hr_value > 250:
                    hr_value = 250
                vitals.heart_rate = hr_value
                status_map['hr'] = 'EXTRACTED'
                extracted_data['hr'] = {
                    'value': vitals.heart_rate, 
                    'icon': '❤️', 
                    'label': 'ЧСС (пульс)'
                }
                hr_found = True
                break
        
        if not hr_found:
            status_map['hr'] = 'UNKNOWN'

        # 5. Извлечение сатурации
        spo2_patterns = [
            r'(?:SpO2|сатурация|saturation)\s*[:]?\s*(\d{2,3})',
            r'SpO2\s*[:]?\s*(\d{2,3})',
            r'сатурация\s*[:]?\s*(\d{2,3})',
        ]
        spo2_found = False
        for pattern in spo2_patterns:
            spo2_match = re.search(pattern, text, re.IGNORECASE)
            if spo2_match:
                vitals.spo2 = int(spo2_match.group(1))
                status_map['spo2'] = 'EXTRACTED'
                extracted_data['spo2'] = {
                    'value': f"{vitals.spo2}%", 
                    'icon': '🫁', 
                    'label': 'Сатурация (SpO₂)'
                }
                spo2_found = True
                break
        
        if not spo2_found:
            status_map['spo2'] = 'UNKNOWN'

        # 6. Извлечение температуры
        temp_match = re.search(r'(?:температура|t)\s*[:]?\s*(\d{2,3}\.?\d*)', text, re.IGNORECASE)
        if temp_match:
            vitals.temperature = float(temp_match.group(1))
            status_map['temperature'] = 'EXTRACTED'
            extracted_data['temperature'] = {
                'value': f"{vitals.temperature}°C", 
                'icon': '🌡️', 
                'label': 'Температура'
            }
        else:
            status_map['temperature'] = 'UNKNOWN'

        # 7. РАЗДЕЛЕНИЕ ЖАЛОБ И АНАМНЕЗА
        anamnesis_keywords = [
            'сахарный диабет', 'диабет', 'гипертония', 'ишемия', 'инфаркт', 'инсульт',
            'принимает', 'аллергия', 'операция', 'травма', 'беременность',
            'хронический', 'заболевание', 'лекарство', 'препарат', 'антикоагулянт',
            'варфарин', 'ксарелто', 'аспирин', 'инсулин', 'сердечный', 'давление'
        ]
        
        raw_text = text
        raw_text = re.sub(r'\b(муж|мужчина|жен|женщина|male|female)\b', '', raw_text, flags=re.IGNORECASE)
        
        remove_patterns = [
            r'\d{1,3}\s*(?:лет|год|года)',
            r'АД\s*[:]?\s*\d{2,3}\s*[/]\s*\d{2,3}',
            r'давление\s*[:]?\s*\d{2,3}\s*[/]\s*\d{2,3}',
            r'(?:пульс|ЧСС)\s*[:]?\s*\d{2,3}',
            r'(?:SpO2|сатурация)\s*[:]?\s*\d{2,3}',
            r'(?:температура|t)\s*[:]?\s*\d{2,3}\.?\d*',
            r'❓\s*[^,.]*',
            r'•\s*[^,.]*',
            r'[:;]\s*\d+',
            r'\d{2,3}\s*%',
            r'\d{2,3}\s*°C',
        ]
        
        cleaned_text = raw_text
        for pattern in remove_patterns:
            cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)
        
        cleaned_text = re.sub(r'[;:•❓]', ',', cleaned_text)
        cleaned_text = re.sub(r',\s*,', ',', cleaned_text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        cleaned_text = re.sub(r'^[,.\s]+', '', cleaned_text)
        cleaned_text = re.sub(r'[,.\s]+$', '', cleaned_text)
        
        complaints = []
        anamnesis = []
        
        if cleaned_text:
            parts = [p.strip() for p in cleaned_text.split(',') if p.strip() and len(p.strip()) > 2]
            
            for part in parts:
                part_lower = part.lower()
                is_anamnesis = any(keyword in part_lower for keyword in anamnesis_keywords)
                
                if is_anamnesis:
                    anamnesis.append(part)
                else:
                    complaints.append(part)
        
        patient.complaints = complaints if complaints else ["Жалобы не указаны"]
        patient.medical_history = '; '.join(anamnesis) if anamnesis else None

        patient.vitals = vitals
        patient.status = status_map
        patient.extracted_data = extracted_data
        return patient