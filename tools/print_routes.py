import runpy
import json

globals = runpy.run_path('c:\\Users\\uses\\Downloads\\face recognition\\webapp_new.py', run_name='webapp_module')
app = globals.get('app')
if not app:
    print('NO APP')
else:
    rules = []
    for r in app.url_map.iter_rules():
        rules.append({'rule': str(r), 'methods': sorted(list(r.methods))})
    print(json.dumps(rules, indent=2))
