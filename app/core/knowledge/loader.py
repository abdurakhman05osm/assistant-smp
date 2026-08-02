import os
import json
from typing import List, Dict, Optional

KNOWLEDGE_DIR = "knowledge"

def get_all_categories() -> List[str]:
    """Возвращает список всех категорий (имён файлов без расширения)."""
    categories = []
    if not os.path.exists(KNOWLEDGE_DIR):
        return categories
    for filename in os.listdir(KNOWLEDGE_DIR):
        if filename.endswith(".json"):
            categories.append(filename.replace(".json", ""))
    return categories

def load_diseases_by_category(category: str) -> List[Dict]:
    """Загружает диагнозы из конкретного файла категории."""
    filepath = os.path.join(KNOWLEDGE_DIR, f"{category}.json")
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("diseases", [])
    except Exception as e:
        print(f"Ошибка загрузки категории {category}: {e}")
        return []

def load_all_diseases() -> List[Dict]:
    """Загружает все диагнозы из всех файлов."""
    all_diseases = []
    for category in get_all_categories():
        all_diseases.extend(load_diseases_by_category(category))
    return all_diseases

def get_category_for_disease(disease_id: str) -> Optional[str]:
    """Определяет категорию по ID диагноза."""
    for category in get_all_categories():
        diseases = load_diseases_by_category(category)
        for d in diseases:
            if d.get("id") == disease_id:
                return category
    return None