import json
import os
from typing import List, Dict, Optional

class KnowledgeBase:
    def __init__(self):
        self.diseases = []
        self._load_data()
    
    def _load_data(self):
        try:
            file_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'knowledge_base', 'diseases.json')
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.diseases = data.get('diseases', [])
        except Exception as e:
            print(f"Ошибка загрузки базы знаний: {e}")
            self.diseases = []
    
    def get_all_diseases(self) -> List[Dict]:
        return self.diseases
    
    def get_disease_by_id(self, disease_id: str) -> Optional[Dict]:
        for d in self.diseases:
            if d.get('id') == disease_id:
                return d
        return None
    
    def search_by_symptoms(self, symptoms: List[str]) -> List[Dict]:
        results = []
        for disease in self.diseases:
            disease_symptoms = disease.get('symptoms', [])
            matches = 0
            for symptom in symptoms:
                for ds in disease_symptoms:
                    if symptom.lower() in ds.lower() or ds.lower() in symptom.lower():
                        matches += 1
                        break
            if matches > 0:
                results.append({
                    'disease': disease,
                    'matches': matches,
                    'total_symptoms': len(disease_symptoms)
                })
        results.sort(key=lambda x: x['matches'], reverse=True)
        return results

kb = KnowledgeBase()