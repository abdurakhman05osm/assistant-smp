import re
from typing import List, Dict, Any, Optional
from app.core.models.patient import PatientData
from app.core.models.diagnosis import DiagnosisResult
from app.core.knowledge.disease_kb import kb

class MedicalEngine:
    @staticmethod
    def diagnose(patient_data: PatientData) -> Dict[str, Any]:
        result = {
            'possible_diagnoses': [],
            'red_flags': [],
            'missing_data': [],
            'questions': [],
            'new_questions': []
        }
        
        result['red_flags'] = MedicalEngine._check_red_flags(patient_data)
        symptoms = MedicalEngine._extract_symptoms(patient_data)
        
        if symptoms:
            # Используем kb с поддержкой категорий
            all_diseases = kb.get_all_diseases()
            scored_diseases = []
            
            for disease in all_diseases:
                score = MedicalEngine._calculate_score(disease, symptoms, patient_data)
                scored_diseases.append({
                    'disease': disease,
                    **score,
                    'probability': max(score['probability'], 5.0)
                })
            
            scored_diseases.sort(
                key=lambda x: (
                    MedicalEngine._severity_priority(x['disease'].get('severity', 'medium')),
                    x['probability']
                ),
                reverse=True
            )
            
            # Фильтруем > 30%
            filtered = [d for d in scored_diseases if d['probability'] > 30]
            
            if len(filtered) >= 3:
                top_diagnoses = filtered[:3]
            else:
                top_diagnoses = scored_diseases[:3]
            
            for item in top_diagnoses:
                disease = item['disease']
                
                protocol_text = disease.get('protocol', 'Протокол не указан')
                protocol_text = protocol_text.replace('. ', '.\n')
                protocol_text = re.sub(r'\n+', '\n', protocol_text).strip()
                
                icd10_code = disease.get('icd10', None)
                red_flags = disease.get('red_flags', [])
                questions = disease.get('questions', [])
                hospitalization = disease.get('hospitalization', False)
                
                result['possible_diagnoses'].append(DiagnosisResult(
                    id=disease.get('id', 'unknown'),
                    name=disease.get('name', 'Неизвестно'),
                    probability=item['probability'],
                    matched_symptoms=item['matched'],
                    total_symptoms=item['total'],
                    protocol=protocol_text,
                    missing_data=MedicalEngine._get_missing_data(disease, patient_data),
                    severity=disease.get('severity', 'medium'),
                    matched_symptom_list=item.get('matched_symptoms_list', []),
                    missing_symptom_list=item.get('missing_symptoms_list', []),
                    unknown_symptom_list=item.get('unknown_symptoms_list', []),
                    icd10=icd10_code,
                    red_flags=red_flags,
                    questions=questions,
                    hospitalization=hospitalization
                ))
        
        result['questions'] = MedicalEngine._generate_intelligent_questions(
            patient_data, 
            result['possible_diagnoses'],
            result['red_flags']
        )
        
        result['new_questions'] = MedicalEngine._generate_follow_up_questions(
            patient_data,
            result['possible_diagnoses']
        )
        
        return result
    
    @staticmethod
    def _extract_symptoms(patient_data: PatientData) -> List[str]:
        symptoms = []
        stop_words = ['вопрос', 'ответ', 'добавить', 'уточнить', 'пожалуйста', 'спасибо']
        
        for complaint in patient_data.complaints:
            parts = complaint.replace('.', ',').replace(';', ',').split(',')
            for part in parts:
                part = part.strip().lower()
                if len(part) > 2 and not any(stop in part for stop in stop_words):
                    part = re.sub(r'\d+', '', part)
                    part = re.sub(r'[^а-яa-z\s]', '', part)
                    part = part.strip()
                    if len(part) > 2:
                        symptoms.append(part)
        
        return list(set(symptoms))
    
    @staticmethod
    def _calculate_score(disease: Dict, symptoms: List[str], patient_data: PatientData) -> Dict[str, Any]:
        disease_symptoms = disease.get('symptoms', [])
        matched = 0
        matched_list = []
        missing_list = []
        unknown_list = []
        total = len(disease_symptoms)
        
        for ds in disease_symptoms:
            ds_lower = ds.lower()
            found = False
            for symptom in symptoms:
                if symptom in ds_lower or ds_lower in symptom:
                    found = True
                    break
            
            if found:
                matched += 1
                matched_list.append(ds)
            else:
                partial_found = False
                for symptom in symptoms:
                    if len(symptom) > 3 and (symptom in ds_lower or ds_lower in symptom):
                        partial_found = True
                        break
                
                if partial_found:
                    unknown_list.append(ds)
                else:
                    missing_list.append(ds)
        
        if total > 0:
            base_prob = (matched / total) * 70 + 15
        else:
            base_prob = 10
        
        # Учёт возраста
        if patient_data.age:
            risk_factors = disease.get('risk_factors', [])
            if any('возраст' in rf for rf in risk_factors):
                if patient_data.age > 65:
                    base_prob += 15
                elif patient_data.age > 50:
                    base_prob += 8
                elif patient_data.age < 30:
                    base_prob -= 10
        
        # Учёт пола
        if patient_data.sex == 'male' and disease.get('id') == 'insult':
            base_prob += 5
        if patient_data.sex == 'female' and disease.get('id') == 'hypertensive_crisis':
            base_prob += 5
        
        # Учёт витальных
        vitals = patient_data.vitals
        if vitals:
            if disease.get('id') == 'oks' and vitals.bp_sys and vitals.bp_sys > 140:
                base_prob += 10
            if disease.get('id') == 'hypertensive_crisis' and vitals.bp_sys and vitals.bp_sys > 180:
                base_prob += 20
            if disease.get('id') == 'insult' and vitals.spo2 and vitals.spo2 < 90:
                base_prob += 15
        
        # Учёт анамнеза
        if patient_data.medical_history:
            history_lower = patient_data.medical_history.lower()
            disease_id = disease.get('id')
            
            if disease_id == 'oks' and ('ибс' in history_lower or 'ишемическая' in history_lower):
                base_prob += 20
            if disease_id == 'hypertensive_crisis' and ('гб' in history_lower or 'гипертони' in history_lower):
                base_prob += 15
            if disease_id == 'diabetic_coma' and ('сд' in history_lower or 'диабет' in history_lower):
                base_prob += 20
            if disease_id == 'insult' and ('гб' in history_lower or 'гипертони' in history_lower):
                base_prob += 15
            if disease_id == 'oks' and ('сд' in history_lower or 'диабет' in history_lower):
                base_prob += 15
        
        base_prob = min(max(base_prob, 5), 95)
        
        return {
            'total_score': matched,
            'matched': matched,
            'total': total,
            'probability': round(base_prob, 1),
            'matched_symptoms_list': matched_list,
            'missing_symptoms_list': missing_list,
            'unknown_symptoms_list': unknown_list
        }
    
    @staticmethod
    def _severity_priority(severity: str) -> int:
        priorities = {
            'critical': 100,
            'high': 80,
            'medium': 50,
            'low': 20
        }
        return priorities.get(severity, 50)
    
    @staticmethod
    def _check_red_flags(patient_data: PatientData) -> List[str]:
        flags = []
        vitals = patient_data.vitals
        complaints_text = ' '.join(patient_data.complaints).lower()
        
        if vitals and vitals.spo2 and vitals.spo2 < 90:
            flags.append(f"🚨 Критическая гипоксемия: SpO₂ {vitals.spo2}% (норма > 95%)")
        
        if vitals and vitals.bp_sys:
            if vitals.bp_sys < 90:
                flags.append(f"🚨 Тяжёлая гипотензия: САД {vitals.bp_sys} мм рт.ст. (риск шока)")
            elif vitals.bp_sys > 220:
                flags.append(f"🚨 Гипертонический криз: САД {vitals.bp_sys} мм рт.ст. (риск инсульта/инфаркта)")
        
        if vitals and vitals.heart_rate:
            if vitals.heart_rate < 40:
                flags.append(f"🚨 Опасная брадикардия: ЧСС {vitals.heart_rate} (риск остановки сердца)")
            elif vitals.heart_rate > 150:
                flags.append(f"🚨 Тахиаритмия: ЧСС {vitals.heart_rate} (риск фибрилляции)")
        
        neuro_keywords = ['асимметрия', 'слабость в руке', 'нарушение речи', 'перекос лица', 'обвисла']
        if any(word in complaints_text for word in neuro_keywords):
            flags.append("🚨 Неврологический дефицит — требуется срочное исключение инсульта (время — мозг!)")
        
        cardiac_keywords = ['боль за грудиной', 'давит за грудиной', 'жжение за грудиной', 'холодный пот']
        if any(word in complaints_text for word in cardiac_keywords):
            flags.append("🚨 Кардиальная симптоматика — требуется исключение острого коронарного синдрома")
        
        if 'отек' in complaints_text and ('лиц' in complaints_text or 'горл' in complaints_text):
            flags.append("🚨 Признаки отёка гортани — риск анафилаксии и асфиксии!")
        
        return flags
    
    @staticmethod
    def _get_missing_data(disease: Dict, patient_data: PatientData) -> List[str]:
        missing = []
        vitals = patient_data.vitals
        
        if not vitals or vitals.bp_sys is None:
            missing.append("Артериальное давление")
        if not vitals or vitals.heart_rate is None:
            missing.append("ЧСС (пульс)")
        if not vitals or vitals.spo2 is None:
            missing.append("Сатурация (SpO₂)")
        if not vitals or vitals.temperature is None:
            missing.append("Температура")
        
        disease_id = disease.get('id')
        if disease_id == 'oks':
            missing.append("ЭКГ в 12 отведениях (срочно!)")
            missing.append("Время начала боли (для тромболизиса)")
        elif disease_id == 'insult':
            missing.append("Время начала симптомов (окно для тромболизиса)")
            missing.append("Уровень глюкозы")
            missing.append("Оценка по шкале FAST/NIHSS")
        elif disease_id == 'hypertensive_crisis':
            missing.append("Приём гипотензивных препаратов (какие, когда)")
        elif disease_id == 'anaphylaxis':
            missing.append("Аллергологический анамнез")
            missing.append("Приём новых препаратов/продуктов в последние 2 часа")
        
        return missing
    
    @staticmethod
    def _generate_intelligent_questions(patient_data: PatientData, diagnoses: List[DiagnosisResult], red_flags: List[str]) -> List[str]:
        questions = []
        vitals = patient_data.vitals
        
        if red_flags:
            for flag in red_flags:
                if "SpO₂" in flag and (not vitals or vitals.spo2 is None):
                    questions.append("Какая сатурация (SpO₂)?")
                if "гипотензия" in flag and (not vitals or vitals.bp_sys is None):
                    questions.append("Какое артериальное давление?")
        
        if not vitals or vitals.bp_sys is None:
            questions.append("Какое артериальное давление? (например: 120/80)")
        if not vitals or vitals.heart_rate is None:
            questions.append("Какой пульс? (ударов в минуту)")
        if not vitals or vitals.spo2 is None:
            questions.append("Какая сатурация? (SpO₂ в %)")
        if not vitals or vitals.temperature is None:
            questions.append("Есть ли температура? (в градусах)")
        
        # Добавляем вопросы из базы знаний
        if diagnoses:
            top = diagnoses[0] if diagnoses else None
            if top and hasattr(top, 'questions') and top.questions:
                questions.extend(top.questions[:3])
            elif top and top.id:
                disease = kb.get_disease_by_id(top.id)
                if disease and disease.get('questions'):
                    questions.extend(disease.get('questions', [])[:3])
        
        if not questions:
            questions = [
                "Уточните характер боли (давящая, колющая, жгучая)",
                "Когда начались симптомы?",
                "Есть ли хронические заболевания? (гипертония, диабет, ишемия)"
            ]
        
        seen = set()
        unique_questions = []
        for q in questions:
            if q not in seen:
                seen.add(q)
                unique_questions.append(q)
        
        return unique_questions[:6]
    
    @staticmethod
    def _generate_follow_up_questions(patient_data: PatientData, diagnoses: List[DiagnosisResult]) -> List[str]:
        new_questions = []
        vitals = patient_data.vitals
        
        if diagnoses:
            top = diagnoses[0] if diagnoses else None
            if top:
                if top.id == 'oks' and vitals and vitals.heart_rate and vitals.heart_rate > 100:
                    new_questions.append("Есть ли одышка в покое?")
                    new_questions.append("Были ли обмороки?")
                
                if top.id == 'insult':
                    if not any('глюкоза' in q for q in patient_data.complaints):
                        new_questions.append("Какой уровень глюкозы? (норма 5.6 ммоль/л)")
                    if vitals and vitals.bp_sys and vitals.bp_sys > 180:
                        new_questions.append("Принимает ли антикоагулянты? (варфарин, ксарелто)")
                
                if top.id == 'hypertensive_crisis':
                    if vitals and vitals.bp_sys and vitals.bp_sys > 200:
                        new_questions.append("Есть ли нарушение зрения? (мушки, пятна)")
                        new_questions.append("Есть ли тошнота или рвота?")
        
        return new_questions[:3]