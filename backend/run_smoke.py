import sys
import types
import json
import os

# Inject a lightweight fake bert_matcher to avoid heavy model downloads during smoke runs
fake = types.ModuleType('backend.utils.bert_matcher')
def calculate_similarity(resume_text, job_description):
    return 0.0
fake.calculate_similarity = calculate_similarity
sys.modules['backend.utils.bert_matcher'] = fake

from backend.app import app

def run_smoke():
    client = app.test_client()
    sample_path = os.path.join(os.path.dirname(__file__), 'uploads', 'sample.txt')
    if not os.path.exists(sample_path):
        # try workspace uploads folder fallback
        sample_path = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'sample.txt')

    with open(sample_path, 'rb') as f:
        data = {
            'resume': (f, os.path.basename(sample_path)),
            'job_description': 'Looking for a Python developer with SQL and machine learning experience'
        }
        resp = client.post('/analyze', data=data, content_type='multipart/form-data')
        try:
            print(json.dumps(resp.get_json(), indent=2))
        except Exception:
            print(resp.data)

if __name__ == '__main__':
    run_smoke()
