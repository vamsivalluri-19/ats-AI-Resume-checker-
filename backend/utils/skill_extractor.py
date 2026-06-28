import json
import os
import re

def extract_skills(text):
    text = (text or "").lower()

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    skills_path = os.path.join(base_dir, 'data', 'skills.json')

    try:
        with open(skills_path, 'r', encoding='utf-8') as file:
            skills_data = json.load(file)
    except Exception:
        return []

    found_skills = []
    for skill in skills_data.get('skills', []):
        skill_lower = skill.lower()
        if not skill_lower:
            continue

        # Build dynamic word boundaries
        pattern = ""
        if skill_lower[0].isalnum():
            pattern += r'\b'
        pattern += re.escape(skill_lower)
        if skill_lower[-1].isalnum():
            pattern += r'\b'

        if re.search(pattern, text):
            found_skills.append(skill)

    return found_skills