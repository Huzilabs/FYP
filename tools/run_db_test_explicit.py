import os
import re
import traceback
import urllib.parse
import socket

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import psycopg2

def mask(dsn):
    return re.sub(r'://([^:]+):[^@]+@', r'://\1:****@', dsn)

def main():
    d = os.getenv('SUPABASE_DB_URL')
    print('DSN present:', bool(d))
    if not d:
        print('No SUPABASE_DB_URL in environment')
        return
    print('masked:', mask(d))
    print('raw:', d)

    u = urllib.parse.urlparse(d)
    user = u.username
    password = u.password
    dbname = u.path.lstrip('/')
    host = u.hostname
    port = u.port or 5432

    params = dict(user=user, password=password, dbname=dbname, host=host, port=port, sslmode='require')
    print('\nTrying explicit params connect to host:', host, 'port:', port)
    try:
        conn = psycopg2.connect(**params)
        conn.close()
        print('CONNECT_OK')
    except Exception:
        print('--- explicit params connect failed ---')
        traceback.print_exc()

    # Try resolving IPv4 and connecting directly to IPv4 address
    try:
        infos = socket.getaddrinfo(host, port, family=socket.AF_INET, type=socket.SOCK_STREAM)
        ipv4 = infos[0][4][0] if infos else None
    except Exception:
        ipv4 = None

    if ipv4:
        print('\nFound IPv4 address:', ipv4, ' — trying connect to IPv4 directly')
        try:
            conn = psycopg2.connect(user=user, password=password, dbname=dbname, host=ipv4, port=port, sslmode='require')
            conn.close()
            print('CONNECT_OK_IPV4')
        except Exception:
            print('--- IPv4 direct connect failed ---')
            traceback.print_exc()
    else:
        print('\nNo IPv4 address found for host (or resolution failed)')

if __name__ == '__main__':
    main()
