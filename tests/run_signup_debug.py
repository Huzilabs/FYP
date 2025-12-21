import base64
import json
import requests
from pathlib import Path

IMG_PATH = Path('data/debug/upload_temp_1d3b99540feb4be796437b3e6a93abfb.jpg')
SERVER = 'http://127.0.0.1:5000'

if not IMG_PATH.exists():
    print('image not found:', IMG_PATH)
    raise SystemExit(1)

with open(IMG_PATH, 'rb') as f:
    data = f.read()

b64 = base64.b64encode(data).decode()
data_url = f'data:image/jpeg;base64,{b64}'

print('Posting to /api/detect_face...')
resp = requests.post(SERVER + '/api/detect_face', json={'face_image': data_url}, timeout=30)
print('status', resp.status_code)
try:
    print(resp.json())
except Exception:
    print(resp.text)

print('\nPosting to /signup...')
payload = {
    'display_name': 'Debug Test',
    'username': 'debug_test_' + base64.b16encode(b'debug').decode()[:8],
    'consent_terms': True,
    'image': data_url,
}
resp2 = requests.post(SERVER + '/signup', json=payload, timeout=60)
print('status', resp2.status_code)
try:
    print(json.dumps(resp2.json(), indent=2))
except Exception:
    print(resp2.text)
