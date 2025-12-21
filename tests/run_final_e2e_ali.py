import base64
import json
import requests
from pathlib import Path

IMG_PATH = Path('data/images/ali/1765734988.jpg')
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
print('detect status', resp.status_code)
try:
    print(json.dumps(resp.json(), indent=2))
except Exception:
    print(resp.text)

print('\nPosting to /signup...')
payload = {
    'display_name': 'ALI E2E Test',
    'username': 'ali_e2e_' + base64.b16encode(b'ali').decode()[:8],
    'consent_terms': True,
    'image': data_url,
}
resp2 = requests.post(SERVER + '/signup', json=payload, timeout=120)
print('signup status', resp2.status_code)
try:
    print(json.dumps(resp2.json(), indent=2))
    user_id = resp2.json().get('user_id')
except Exception:
    print(resp2.text)
    user_id = None

if user_id:
    print('\nQuerying admin embeddings for user:', user_id)
    r = requests.get(SERVER + '/api/admin/embeddings', params={'user_id': user_id}, timeout=30)
    print('admin embeddings status', r.status_code)
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)

print('\nAttempting face login (long timeout)')
resp3 = requests.post(SERVER + '/api/login_face', json={'face_image': data_url, 'threshold': 0.6, 'limit': 1}, timeout=180)
print('login status', resp3.status_code)
try:
    print(json.dumps(resp3.json(), indent=2))
except Exception:
    print(resp3.text)
