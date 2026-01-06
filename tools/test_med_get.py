import runpy
import json

globals = runpy.run_path('c:\\Users\\uses\\Downloads\\face recognition\\webapp_new.py', run_name='webapp_module')
app = globals.get('app')
if not app:
    print('NO APP')
    raise SystemExit(1)

client = app.test_client()
user_id = '2c8e853a-017e-4ccd-80d2-52d136b86571'
resp = client.get(f'/api/users/{user_id}/medications')
print('status', resp.status_code)
try:
    print(json.dumps(resp.get_json(), indent=2))
except Exception:
    print('raw', resp.data)
