import traceback
try:
    import importlib
    importlib.invalidate_caches()
    import webapp_new
    print('imported webapp_new OK')
except Exception:
    traceback.print_exc()
    raise
