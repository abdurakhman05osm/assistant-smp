import json
import os
from typing import List, Dict, Optional
from app.core.knowledge.loader import load_all_diseases, load_diseases_by_category, get_all_categories

class KnowledgeBase:
    def __init__(self):
        self.diseases = []
        self._load_data()
    
    def _load_data(self):
        self.diseases = load_all_diseases()
    
    def get_all_diseases(self) -> List[Dict]:
        return self.diseases
    
    def get_diseases_by_category(self, category: str) -> List[Dict]:
        return load_diseases_by_category(category)
    
    def get_all_categories(self) -> List[str]:
        return get_all_categories()
    
    def get_disease_by_id(self, disease_id: str) -> Optional[Dict]:
        for d in self.diseases:
            if d.get('id') == disease_id:
                return d
        return None
    
    def search_by_symptoms(self, symptoms: List[str], category: Optional[str] = None) -> List[Dict]:
        """Поиск по симптомам с возможностью фильтрации по категории"""
        if category:
            diseases = load_diseases_by_category(category)
        else:
            diseases = self.diseases
            
        results = []
        for disease in diseases:
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