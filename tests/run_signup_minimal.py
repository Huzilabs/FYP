import requests, json, time
SERVER='http://127.0.0.1:5000'
payload={'display_name':'QuickUser','username':'quick_test_'+str(int(time.time())),'consent_terms':True}
try:
    r=requests.post(SERVER+'/signup', json=payload, timeout=30)
    print('status', r.status_code)
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)
except Exception as e:
    print('error', e)
