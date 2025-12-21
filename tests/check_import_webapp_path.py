import importlib.util
import traceback
p = r'c:\Users\uses\Downloads\face recognition\webapp_new.py'
try:
    spec = importlib.util.spec_from_file_location('webapp_new', p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print('loaded webapp_new from', p)
except Exception:
    traceback.print_exc()
    raise
