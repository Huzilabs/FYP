"""Small notifications server providing SSE and fallback API for unread notifications.

Run alongside `webapp_new.py` during development:

  SUPABASE_DB_URL=... python notifications_server.py

This server exposes:
- GET /api/users/<user_id>/notifications                     -> JSON unread notifications
- GET /api/users/<user_id>/notifications/stream              -> SSE stream of unread notifications

It marks notifications `delivered = TRUE` after sending over SSE.
"""
import os
import time
import json
import psycopg2
import psycopg2.extras
from flask import Flask, Response, stream_with_context, jsonify

app = Flask(__name__)


def get_conn():
    dsn = os.getenv('SUPABASE_DB_URL') or os.getenv('DATABASE_URL')
    if not dsn:
        raise RuntimeError('SUPABASE_DB_URL or DATABASE_URL must be set')
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    return conn


@app.route('/api/users/<user_id>/notifications')
def list_notifications(user_id):
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT id, title, body, payload, created_at, delivered, read_at FROM public.user_notifications WHERE user_id=%s ORDER BY created_at DESC LIMIT 100", (user_id,))
        rows = cur.fetchall()
        return jsonify(rows)
    finally:
        conn.close()


@app.route('/api/users/<user_id>/notifications/stream')
def stream_notifications(user_id):
    def event_stream():
        conn = get_conn()
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            # simple poll loop; production may use LISTEN/NOTIFY or pubsub
            while True:
                cur.execute("SELECT id, title, body, payload, created_at FROM public.user_notifications WHERE user_id=%s AND delivered=FALSE ORDER BY created_at ASC", (user_id,))
                rows = cur.fetchall()
                ids = []
                for r in rows:
                    payload = {
                        'id': str(r['id']),
                        'title': r['title'],
                        'body': r['body'],
                        'payload': r['payload'],
                        'created_at': r['created_at'].isoformat() if r['created_at'] else None,
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                    ids.append(r['id'])

                if ids:
                    # mark delivered
                    cur.execute("UPDATE public.user_notifications SET delivered=TRUE WHERE id = ANY(%s)", (ids,))
                    conn.commit()

                time.sleep(1)
        except GeneratorExit:
            # client disconnected
            try:
                conn.close()
            except Exception:
                pass
            return
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return

    return Response(stream_with_context(event_stream()), mimetype='text/event-stream')


if __name__ == '__main__':
    port = int(os.getenv('NOTIFICATIONS_PORT', '5010'))
    app.run(host='0.0.0.0', port=port, debug=True)
