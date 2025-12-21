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

# Provide user_id from previous minimal signup run
user_id = None
# Try to read from last minimal signup output file
try:
    with open('tests/last_user_id.txt','r') as fh:
        user_id = fh.read().strip()
except Exception:
    pass

if not user_id:
    user_id = input('user_id: ').strip()

print('Attaching to user', user_id)
resp = requests.post(SERVER + '/api/attach_image', json={'user_id': user_id, 'face_image': data_url}, timeout=120)
print('status', resp.status_code)
try:
    print(json.dumps(resp.json(), indent=2))
except Exception:
    print(resp.text)
