import json
import os
from backend.app import app

def run_test():
    client = app.test_client()

    sample_path = os.path.join(os.path.dirname(__file__), 'uploads', 'sample.txt')
    with open(sample_path, 'rb') as f:
        data = {
            'resume': (f, 'sample.txt'),
            'job_description': ''
        }

        response = client.post('/analyze', data=data, content_type='multipart/form-data')
        try:
            print(json.dumps(response.get_json(), indent=2))
        except Exception:
            print(response.data)

if __name__ == '__main__':
    run_test()
