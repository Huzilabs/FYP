import base64
import io
import os
import time
import uuid
from typing import Tuple, Optional

from flask import Flask, jsonify, render_template, request
from PIL import Image
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
SUPABASE_DB_URL = os.getenv('SUPABASE_DB_URL') or os.getenv('DATABASE_URL')
SUPABASE_BUCKET = os.getenv('SUPABASE_BUCKET')

sb = None
if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
	try:
		from supabase import create_client

		sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
	except Exception:
		sb = None

APP_ROOT = os.path.dirname(__file__)
DATA_DIR = os.path.join(APP_ROOT, 'data')
DEBUG_DIR = os.path.join(DATA_DIR, 'debug')
os.makedirs(DEBUG_DIR, exist_ok=True)

app = Flask(__name__, template_folder='templates')


def coerce_bool(value: Optional[str]) -> bool:
	if isinstance(value, bool):
		return value
	if value is None:
		return False
	return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def get_db_conn():
	if not SUPABASE_DB_URL:
		raise RuntimeError('SUPABASE_DB_URL not set')
	try:
		import psycopg2  # type: ignore
	except Exception as exc:
		raise RuntimeError('psycopg2 is required: ' + str(exc))
	conn = psycopg2.connect(SUPABASE_DB_URL)
	conn.autocommit = False
	return conn


def normalize_public_url(pu) -> str:
	if pu is None:
		return ''
	if isinstance(pu, dict):
		for key in ('publicURL', 'public_url', 'url'):
			if pu.get(key):
				return str(pu[key])
		values = list(pu.values())
		return str(values[0]) if values else ''
	return str(pu)


def decode_base64_image(data_url: str) -> Tuple['numpy.ndarray', bytes]:
	if ',' not in data_url:
		raise ValueError('invalid data URL')
	_, b64 = data_url.split(',', 1)
	img_bytes = base64.b64decode(b64)
	img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
	import numpy as np

	arr = np.array(img)
	return arr, img_bytes


def save_debug_image(prefix: str, img_arr) -> None:
	try:
		name = f"{prefix}_{uuid.uuid4().hex}.jpg"
		Image.fromarray(img_arr).save(os.path.join(DEBUG_DIR, name))
	except Exception:
		app.logger.exception('failed to persist debug image')


def ensure_storage_ready():
	if not sb or not SUPABASE_BUCKET:
		raise RuntimeError('Supabase storage not configured')


def save_image_to_storage(path: str, img_bytes: bytes) -> str:
	ensure_storage_ready()
	try:
		sb.storage.from_(SUPABASE_BUCKET).upload(path, img_bytes)
		pu = sb.storage.from_(SUPABASE_BUCKET).get_public_url(path)
		return normalize_public_url(pu)
	except Exception as exc:
		app.logger.debug('storage upload failed: %s', repr(exc))
		try:
			pu = sb.storage.from_(SUPABASE_BUCKET).get_public_url(path)
			url = normalize_public_url(pu)
			if url:
				return url
		except Exception:
			pass
		import tempfile

		tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
		try:
			tmp_file.write(img_bytes)
			tmp_file.flush()
			tmp_file.close()
			with open(tmp_file.name, 'rb') as handle:
				sb.storage.from_(SUPABASE_BUCKET).upload(path, handle.read())
			pu = sb.storage.from_(SUPABASE_BUCKET).get_public_url(path)
			return normalize_public_url(pu)
		finally:
			try:
				os.unlink(tmp_file.name)
			except Exception:
				pass


def download_from_storage(path: str) -> bytes:
	ensure_storage_ready()
	try:
		data = sb.storage.from_(SUPABASE_BUCKET).download(path)
		if isinstance(data, (bytes, bytearray)):
			return bytes(data)
		if isinstance(data, dict) and 'data' in data:
			return bytes(data['data'])
	except Exception:
		pass
	pu = sb.storage.from_(SUPABASE_BUCKET).get_public_url(path)
	url = normalize_public_url(pu)
	if not url:
		raise RuntimeError('unable to retrieve file from storage')
	import requests

	resp = requests.get(url, timeout=30)
	resp.raise_for_status()
	return resp.content


def compute_face_encoding(img_arr):
	try:
		import face_recognition
	except Exception as exc:
		raise RuntimeError('face_recognition import failed: ' + str(exc))
	# Log image details for debugging
	app.logger.debug('face detection: image shape %s, dtype %s', img_arr.shape, img_arr.dtype)
	# Use 'large' model for better accuracy, add jitters for robustness
	encodings = face_recognition.face_encodings(img_arr, model='large', num_jitters=5, num_upsamples=2)
	app.logger.debug('face detection: found %d encodings', len(encodings))
	if not encodings:
		return None
	return encodings[0]
def insert_embedding(cur, user_id: int, encoding, source: str) -> None:
	vec_vals = ','.join(repr(float(x)) for x in encoding)
	for cast in ('vector', 'float8[]'):
		try:
			literal = f"ARRAY[{vec_vals}]::{cast}"
			sql = f"""
				INSERT INTO public.embeddings (user_id, embedding, source, created_at)
				VALUES (%s, {literal}, %s, now())
			"""
			cur.execute(sql, (user_id, source))
			return
		except Exception as exc:
			app.logger.debug('embedding insert failed (%s): %s', cast, repr(exc))
	raise RuntimeError('embedding insert failed for all casts')


@app.errorhandler(404)
def handle_404(err):
	try:
		if request.path.startswith('/api/'):
			return jsonify({'ok': False, 'error': 'not_found', 'path': request.path}), 404
	except Exception:
		pass
	return err


@app.route('/_routes', methods=['GET'])
def list_routes():
	rules = sorted(rule.rule for rule in app.url_map.iter_rules())
	return jsonify({'routes': rules})


@app.route('/', methods=['GET'])
def index():
	template = app.template_folder or ''
	index_path = os.path.join(template, 'index.html')
	if template and os.path.exists(index_path):
		return render_template('index.html')
	return 'OK'


@app.route('/signup', methods=['GET'])
def signup():
	tmpl = app.template_folder or ''
	page = os.path.join(tmpl, 'welcome.html')
	if tmpl and os.path.exists(page):
		return render_template('welcome.html')
	return render_template('index.html') if os.path.exists(os.path.join(tmpl, 'index.html')) else 'Signup'


@app.route('/api/upload_face', methods=['POST'])
def api_upload_face():
	payload = request.get_json(force=True) if request.is_json else request.form.to_dict()
	data_url = payload.get('face_image') or payload.get('image')
	if not data_url:
		return jsonify({'ok': False, 'error': 'missing_image'}), 400
	try:
		img_arr, img_bytes = decode_base64_image(data_url)
	except Exception as exc:
		return jsonify({'ok': False, 'error': 'bad_image', 'detail': str(exc)}), 400

	save_debug_image('upload', img_arr)

	try:
		ensure_storage_ready()
	except Exception as exc:
		return jsonify({'ok': False, 'error': 'storage_not_configured', 'detail': str(exc)}), 500

	temp_path = f"temp/{uuid.uuid4().hex}.jpg"
	try:
		public_url = save_image_to_storage(temp_path, img_bytes)
	except Exception as exc:
		return jsonify({'ok': False, 'error': 'upload_failed', 'detail': str(exc)}), 500

	return jsonify({'ok': True, 'temp_storage_path': temp_path, 'public_url': public_url}), 200


def load_image_from_temp(temp_path: str):
	img_bytes = download_from_storage(temp_path)
	img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
	import numpy as np

	return np.array(img), img_bytes


@app.route('/api/register', methods=['POST'])
def api_register():
	payload = request.get_json(force=True) if request.is_json else request.form.to_dict()
	display_name = payload.get('display_name') or payload.get('name')
	username = payload.get('username')
	email = payload.get('email')
	phone = payload.get('phone')
	consent = coerce_bool(payload.get('consent_terms'))
	data_url = payload.get('face_image') or payload.get('image')
	temp_path = payload.get('temp_storage_path')

	if not display_name or not username or not consent or not (data_url or temp_path):
		return jsonify({'ok': False, 'error': 'missing_fields'}), 400

	try:
		if temp_path:
			img_arr, img_bytes = load_image_from_temp(temp_path)
		else:
			img_arr, img_bytes = decode_base64_image(data_url)
	except Exception as exc:
		app.logger.exception('register: load image failed')
		return jsonify({'ok': False, 'error': 'bad_image', 'detail': str(exc)}), 400

	save_debug_image('register', img_arr)

	encoding = compute_face_encoding(img_arr)
	if encoding is None:
		return jsonify({'ok': False, 'error': 'no_face', 'message': 'No face detected. Ensure good lighting, clear focus on face, and try again.'}), 200

	try:
		ensure_storage_ready()
	except Exception as exc:
		return jsonify({'ok': False, 'error': 'storage_not_configured', 'detail': str(exc)}), 500

	conn = get_db_conn()
	cur = conn.cursor()
	try:
		cur.execute(
			"""
				INSERT INTO public.users (display_name, username, email, phone, created_at)
				VALUES (%s, %s, %s, %s, now())
				ON CONFLICT (username) DO UPDATE SET display_name = EXCLUDED.display_name
				RETURNING id
			""",
			(display_name, username, email, phone),
		)
		user_id = cur.fetchone()[0]

		filename = os.path.basename(temp_path) if temp_path else f"{int(time.time())}_{uuid.uuid4().hex}.jpg"
		storage_path = f"{user_id}/{filename}"
		public_url = save_image_to_storage(storage_path, img_bytes)

		cur.execute(
			"""
				INSERT INTO public.user_images (user_id, storage_path, public_url, width, height, mime_type, uploaded_at, is_profile, file_size)
				VALUES (%s, %s, %s, %s, %s, %s, now(), %s, %s)
			""",
			(
				user_id,
				storage_path,
				public_url,
				img_arr.shape[1],
				img_arr.shape[0],
				'image/jpeg',
				True,
				len(img_bytes),
			),
		)

		insert_embedding(cur, user_id, encoding, 'signup')
		conn.commit()
	except Exception as exc:
		conn.rollback()
		app.logger.exception('register: db error')
		return jsonify({'ok': False, 'error': 'db_error', 'detail': str(exc)}), 500
	finally:
		cur.close()
		conn.close()

	return jsonify({'ok': True, 'user_id': str(user_id), 'profile_image_url': public_url}), 201


@app.route('/api/login_face', methods=['POST'])
def api_login_face():
	payload = request.get_json(force=True) if request.is_json else request.form.to_dict()
	data_url = payload.get('face_image') or payload.get('image')
	if not data_url:
		return jsonify({'ok': False, 'error': 'missing_image'}), 400
	try:
		img_arr, _ = decode_base64_image(data_url)
	except Exception as exc:
		return jsonify({'ok': False, 'error': 'bad_image', 'detail': str(exc)}), 400

	encoding = compute_face_encoding(img_arr)
	if encoding is None:
		return jsonify({'ok': False, 'error': 'no_face', 'message': 'No face detected. Ensure good lighting, clear focus on face, and try again.'}), 200

	threshold = float(payload.get('threshold') or 0.5)
	limit = int(payload.get('limit') or 1)
	conn = get_db_conn()
	cur = conn.cursor()
	try:
		vec_literal = 'ARRAY[' + ','.join(repr(float(x)) for x in encoding) + ']::vector'
		sql = f"""
			SELECT embedding_id, user_id, dist
			FROM public.find_nearest_embeddings({vec_literal}, %s)
			LIMIT %s
		"""
		cur.execute(sql, (threshold, limit))
		row = cur.fetchone()
		if not row:
			conn.commit()
			return jsonify({'ok': False, 'error': 'no_match'}), 200
		_, user_id, dist = row
		cur.execute('SELECT id, display_name, username FROM public.users WHERE id = %s', (user_id,))
		user_row = cur.fetchone()
		conn.commit()
	except Exception as exc:
		conn.rollback()
		app.logger.exception('login_face: db error')
		return jsonify({'ok': False, 'error': 'db_error', 'detail': str(exc)}), 500
	finally:
		cur.close()
		conn.close()

	if not user_row:
		return jsonify({'ok': False, 'error': 'user_missing'}), 404
	if dist > threshold:
		return jsonify({'ok': False, 'error': 'no_match', 'min_distance': float(dist)}), 200
	return jsonify({'ok': True, 'user': {'id': str(user_row[0]), 'display_name': user_row[1], 'username': user_row[2]}, 'distance': float(dist)}), 200


if __name__ == '__main__':
	os.makedirs(DATA_DIR, exist_ok=True)
	print('webapp.py: launching Flask on http://0.0.0.0:5000', flush=True)
	app.run(host='0.0.0.0', port=5000, debug=True)
