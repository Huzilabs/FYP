import base64
import io
import os
import time
import uuid
from typing import Tuple, Optional

from flask import Flask, jsonify, render_template, request
from PIL import Image
from dotenv import load_dotenv
import logging
import sys
import json
import numpy as np

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

# Configure logging to stdout so terminal shows logs reliably
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s', force=True)
app.logger.handlers = []
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)

# Cache whether pgvector `vector` type exists to avoid repeated checks
_HAS_VECTOR = None


def _detect_vector_type() -> bool:
	global _HAS_VECTOR
	if _HAS_VECTOR is not None:
		return _HAS_VECTOR
	try:
		conn = None
		try:
			conn = get_db_conn()
			# run detection in autocommit mode to avoid interacting with caller transactions
			conn.autocommit = True
			cur = conn.cursor()
			cur.execute("SELECT EXISTS(SELECT 1 FROM pg_type WHERE typname = %s)", ('vector',))
			_HAS_VECTOR = bool(cur.fetchone()[0])
			try:
				cur.close()
			except Exception:
				pass
		finally:
			try:
				if conn:
					conn.close()
			except Exception:
				pass
	except Exception:
		_HAS_VECTOR = False
	return _HAS_VECTOR


def coerce_bool(value: Optional[str]) -> bool:
	if isinstance(value, bool):
		return value
	if value is None:
		return False
	return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _get_actor_user_id():
	"""Resolve caller identity for owner-only checks.

	This accepts either header `X-User-Id` or form/json field `actor_user_id`.
	It's a minimal protection mechanism intended for local/dev usage until
	proper authentication is added (JWT / API key / Supabase auth).
	"""
	# Prefer header
	try:
		uid = request.headers.get('X-User-Id')
		if uid:
			return uid
	except Exception:
		pass
	# Fall back to body param
	try:
		payload = request.get_json(silent=True) if request.is_json else request.form.to_dict()
		if payload:
			uid = payload.get('actor_user_id') or payload.get('user_id')
			if uid:
				return uid
	except Exception:
		pass
	return None


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


def decode_base64_image(data_url: str) -> Tuple[np.ndarray, bytes]:
	if ',' not in data_url:
		raise ValueError('invalid data URL')
	_, b64 = data_url.split(',', 1)
	img_bytes = base64.b64decode(b64)
	img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
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
		raise RuntimeError('Supabase storage not configured; check SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_BUCKET')


def _public_or_signed_url(path: str) -> str:
	"""Return best-effort public URL; fallback to signed URL if bucket is private."""
	try:
		pu = sb.storage.from_(SUPABASE_BUCKET).get_public_url(path)
		app.logger.debug('get_public_url raw response: %r', pu)
		url = normalize_public_url(pu)
		app.logger.debug('normalized public url: %s', url)
		if url and 'not_found' not in url:
			return url
	except Exception:
		pass
	try:
		signed = sb.storage.from_(SUPABASE_BUCKET).create_signed_url(path, 60 * 60 * 24 * 365)  # 1 year
		app.logger.debug('create_signed_url raw response: %r', signed)
		url = normalize_public_url(signed)
		app.logger.debug('normalized signed url: %s', url)
		if url:
			return url
	except Exception:
		pass
	return ''


def save_image_to_storage(path: str, img_bytes: bytes) -> str:
	ensure_storage_ready()
	try:
		# storage3 upload expects file bytes; avoid passing boolean values in file options
		resp = sb.storage.from_(SUPABASE_BUCKET).upload(path, img_bytes)
		app.logger.info('storage.upload response: %r', resp)
		url = _public_or_signed_url(path)
		app.logger.info('save_image_to_storage resolved url: %s for path: %s', url, path)
		return url
	except Exception as exc:
		app.logger.exception('storage upload failed: %s', exc)
		try:
			url = _public_or_signed_url(path)
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
			return _public_or_signed_url(path)
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
	print(f'compute_face_encoding: image shape={getattr(img_arr, "shape", None)}', flush=True)
	# Fast path: prefer the lightweight `hog` detector with minimal upsampling
	# and low jitter for encoding. If hog finds no faces, fall back to cnn.
	locations = []
	try:
		locations = face_recognition.face_locations(img_arr, model='hog', number_of_times_to_upsample=0)
	except Exception:
		try:
			locations = face_recognition.face_locations(img_arr)
		except Exception:
			locations = []

	app.logger.debug('face detection (fast/hog) found %d locations', len(locations))

	# If no faces found with hog, try cnn once with a small upsample for accuracy
	if not locations:
		try:
			locations = face_recognition.face_locations(img_arr, model='cnn', number_of_times_to_upsample=1)
		except Exception:
			try:
				locations = face_recognition.face_locations(img_arr)
			except Exception:
				locations = []

	app.logger.debug('face detection: final locations count %d', len(locations))
	if not locations:
		return None

	# Compute encodings with minimal jitter to speed up processing.
	encodings = []
	try:
		# Many builds accept `known_face_locations` and `num_jitters`; use low jitter (1)
		encodings = face_recognition.face_encodings(img_arr, known_face_locations=locations, num_jitters=1)
	except TypeError:
		try:
			encodings = face_recognition.face_encodings(img_arr, locations)
		except Exception:
			encodings = []
	except Exception:
		encodings = []

	app.logger.debug('face detection: found %d encodings', len(encodings))
	if not encodings:
		return None
	return encodings[0]


def insert_embedding(cur, user_id: str, encoding, source: str) -> None:
	# Detect vector availability using a separate connection (cached).
	has_vector = _detect_vector_type()

	# Prefer inserting as PostgreSQL float8[] which works even when pgvector
	# extension isn't installed. If that fails and `vector` type is available,
	# fall back to the ::vector cast.
	list_vals = list(float(x) for x in encoding)
	sql_array = """
		INSERT INTO public.embeddings (user_id, embedding, source, created_at)
		VALUES (%s, %s, %s, now())
	"""
	try:
		app.logger.debug('insert_embedding: attempting float8[] insert, user=%s length=%d', user_id, len(encoding))
		app.logger.debug('insert_embedding: sql=%s params=%s', sql_array.strip(), '[<list float>]')
		cur.execute(sql_array, (user_id, list_vals, source))
		return
	except Exception:
		app.logger.exception('insert_embedding: float8[] insert failed, will try vector cast if available')

	if has_vector:
		try:
			vec_text = '[' + ','.join(str(float(x)) for x in encoding) + ']'
			sql_vec = """
				INSERT INTO public.embeddings (user_id, embedding, source, created_at)
				VALUES (%s, %s::vector, %s, now())
			"""
			app.logger.debug('insert_embedding: attempting ::vector insert, user=%s length=%d', user_id, len(encoding))
			app.logger.debug('insert_embedding: sql=%s params=%s', sql_vec.strip(), '[vec_text, source]')
			cur.execute(sql_vec, (user_id, vec_text, source))
			return
		except Exception:
			app.logger.exception('insert_embedding: ::vector insert also failed')

	# If we reached here, both insertion attempts failed — raise to caller
	raise RuntimeError('embedding insert failed for all strategies')


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


@app.route('/api/detect_face', methods=['POST'])
def api_detect_face():
	payload = request.get_json(force=True) if request.is_json else request.form.to_dict()
	data_url = payload.get('face_image') or payload.get('image')
	if not data_url:
		return jsonify({'ok': False, 'error': 'missing_image'}), 400
	# Accept either a data URL (base64), an HTTP(S) URL (public Supabase URL),
	# or a Supabase storage path (download via download_from_storage).
	img_arr = None
	try:
		# HTTP(S) URL: fetch bytes via requests
		if isinstance(data_url, str) and (data_url.startswith('http://') or data_url.startswith('https://')):
			import requests
			resp = requests.get(data_url, timeout=20)
			resp.raise_for_status()
			img_bytes = resp.content
			from PIL import Image as PILImage
			img = PILImage.open(io.BytesIO(img_bytes)).convert('RGB')
			img_arr = np.array(img)
		# Data URL (base64): decode locally
		elif isinstance(data_url, str) and data_url.startswith('data:'):
			img_arr, _ = decode_base64_image(data_url)
		else:
			# Treat input as a storage path: prefer resolving a public URL and fetching
			# that URL so frontends can simply pass the public link. If that fails,
			# fall back to direct download_from_storage or base64 decode.
			fetched = False
			if sb and SUPABASE_BUCKET:
				try:
					pub = _public_or_signed_url(data_url)
					if pub:
						import requests
						r = requests.get(pub, timeout=20)
						r.raise_for_status()
						img_bytes = r.content
						from PIL import Image as PILImage
						img = PILImage.open(io.BytesIO(img_bytes)).convert('RGB')
						img_arr = np.array(img)
						fetched = True
				except Exception:
					fetched = False
			if not fetched:
				try:
					raw = download_from_storage(data_url)
					img_bytes = raw
					from PIL import Image as PILImage
					img = PILImage.open(io.BytesIO(img_bytes)).convert('RGB')
					img_arr = np.array(img)
				except Exception:
					img_arr, _ = decode_base64_image(data_url)
	except Exception as exc:
		return jsonify({'ok': False, 'error': 'bad_image', 'detail': str(exc)}), 400

	try:
		import face_recognition
	except Exception as exc:
		return jsonify({'ok': False, 'error': 'face_recognition_failed', 'detail': str(exc)}), 500

	locations = face_recognition.face_locations(img_arr, model='large', number_of_times_to_upsample=2)
	faces = [{'top': t, 'right': r, 'bottom': b, 'left': l} for t, r, b, l in locations]

	# Read-only detect: return bounding boxes only (no DB writes).
	return jsonify({'ok': True, 'faces': faces}), 200


@app.route('/api/upload_face_temp', methods=['POST'])
def api_upload_face_temp():
	"""Upload a face image to temp/ and return storage_path + usable URL (public or signed).
	Use this if your frontend still expects a temp upload step before capture/register.
	"""
	payload = request.get_json(force=True) if request.is_json else request.form.to_dict()
	data_url = payload.get('face_image') or payload.get('image')
	if not data_url:
		return jsonify({'ok': False, 'error': 'missing_image'}), 400
	try:
		img_arr, img_bytes = decode_base64_image(data_url)
	except Exception as exc:
		return jsonify({'ok': False, 'error': 'bad_image', 'detail': str(exc)}), 400

	save_debug_image('upload_temp', img_arr)

	try:
		ensure_storage_ready()
	except Exception as exc:
		return jsonify({'ok': False, 'error': 'storage_not_configured', 'detail': str(exc)}), 500

	storage_path = f"temp/{uuid.uuid4().hex}.jpg"
	try:
		url = save_image_to_storage(storage_path, img_bytes)
		if not url:
			app.logger.warning('upload returned empty url for %s', storage_path)
			url = storage_path
	except Exception as exc:
		app.logger.exception('upload_face_temp failed: %s', exc)
		return jsonify({'ok': False, 'error': 'upload_failed', 'detail': str(exc)}), 500

	# Always return a preview data URL so frontend can show image immediately
	try:
		preview_data_url = 'data:image/jpeg;base64,' + base64.b64encode(img_bytes).decode()
	except Exception:
		preview_data_url = None

	app.logger.info('upload_face_temp succeeded: path=%s url=%s', storage_path, url)
	return jsonify({'ok': True, 'temp_storage_path': storage_path, 'public_url': url, 'preview_data_url': preview_data_url}), 200


# Legacy alias so existing frontend calls to /api/upload_face keep working
@app.route('/api/upload_face', methods=['POST'])
def api_upload_face_legacy():
	return api_upload_face_temp()


@app.route('/api/capture_face', methods=['POST'])
def api_capture_face():
	payload = request.get_json(force=True) if request.is_json else request.form.to_dict()
	user_id = payload.get('user_id')
	data_url = payload.get('face_image') or payload.get('image')
	# allow capture-first flow: if no user_id provided, create a provisional user record
	if not data_url:
		return jsonify({'ok': False, 'error': 'missing_image'}), 400

	# Accept data URL, HTTP(S) URL, or storage path. Prefer public URL for storage paths.
	try:
		if isinstance(data_url, str) and (data_url.startswith('http://') or data_url.startswith('https://')):
			import requests
			resp = requests.get(data_url, timeout=20)
			resp.raise_for_status()
			img_bytes = resp.content
			img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
			img_arr = np.array(img)
		elif isinstance(data_url, str) and data_url.startswith('data:'):
			img_arr, img_bytes = decode_base64_image(data_url)
		else:
			fetched = False
			if sb and SUPABASE_BUCKET:
				try:
					pub = _public_or_signed_url(data_url)
					if pub:
						import requests
						r = requests.get(pub, timeout=20)
						r.raise_for_status()
						img_bytes = r.content
						img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
						img_arr = np.array(img)
						fetched = True
				except Exception:
					fetched = False
			if not fetched:
				try:
					raw = download_from_storage(data_url)
					img_bytes = raw
					img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
					img_arr = np.array(img)
				except Exception:
					img_arr, img_bytes = decode_base64_image(data_url)
	except Exception as exc:
		return jsonify({'ok': False, 'error': 'bad_image', 'detail': str(exc)}), 400

	save_debug_image('capture', img_arr)

	encoding = compute_face_encoding(img_arr)
	if encoding is None:
		return jsonify({'ok': False, 'error': 'no_face', 'message': 'No face detected. Ensure good lighting, clear focus on face, and try again.'}), 200

	try:
		ensure_storage_ready()
	except Exception as exc:
		return jsonify({'ok': False, 'error': 'storage_not_configured', 'detail': str(exc)}), 500

	# If user_id missing, create provisional user to attach face/embedding to
	provisional_created = False
	if not user_id:
		conn = get_db_conn()
		cur = conn.cursor()
		try:
			temp_username = f"temp_{uuid.uuid4().hex[:8]}"
			cur.execute(
				"""
					INSERT INTO public.users (display_name, username, email, phone, created_at, verified)
					VALUES (%s, %s, %s, %s, now(), false)
					RETURNING id
				""",
				(temp_username, temp_username, None, None),
			)
			user_id = cur.fetchone()[0]
			conn.commit()
			provisional_created = True
		except Exception as exc:
			conn.rollback()
			app.logger.exception('provisional user create failed')
			cur.close()
			conn.close()
			return jsonify({'ok': False, 'error': 'db_error', 'detail': str(exc)}), 500
		finally:
			cur.close()
			conn.close()

	conn = get_db_conn()
	cur = conn.cursor()
	try:
		filename = f"{int(time.time())}_{uuid.uuid4().hex}.jpg"
		storage_path = f"{user_id}/{filename}"
		public_url = save_image_to_storage(storage_path, img_bytes)
		if not public_url:
			public_url = storage_path  # return path so client can still reference

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

		insert_embedding(cur, user_id, encoding, 'capture')
		conn.commit()
	except Exception as exc:
		conn.rollback()
		app.logger.exception('capture_face: db error')
		return jsonify({'ok': False, 'error': 'db_error', 'detail': str(exc)}), 500
	finally:
		cur.close()
		conn.close()

	try:
		preview_data_url = 'data:image/jpeg;base64,' + base64.b64encode(img_bytes).decode()
	except Exception:
		preview_data_url = None
	app.logger.info('capture_face succeeded: user=%s path=%s url=%s', user_id, storage_path, public_url)
	return jsonify({'ok': True, 'profile_image_url': public_url, 'storage_path': storage_path, 'preview_data_url': preview_data_url}), 201




@app.route('/api/register', methods=['POST'])
def api_register():
	payload = request.get_json(force=True) if request.is_json else request.form.to_dict()
	display_name = payload.get('display_name') or payload.get('name')
	username = payload.get('username')
	email = payload.get('email')
	phone = payload.get('phone')
	consent = coerce_bool(payload.get('consent_terms'))

	if not display_name or not username or not consent:
		return jsonify({'ok': False, 'error': 'missing_fields'}), 400

	# parse optional profile fields
	date_of_birth = payload.get('date_of_birth') or None
	# emergency_contact may be JSON string or form-encoded string
	emergency_contact_raw = payload.get('emergency_contact')
	emergency_contact = None
	if emergency_contact_raw:
		try:
			if isinstance(emergency_contact_raw, str):
				emergency_contact = json.loads(emergency_contact_raw)
			else:
				emergency_contact = emergency_contact_raw
		except Exception:
			emergency_contact = {'raw': emergency_contact_raw}

	# medications: accept JSON array or comma-separated list
	medications_field = payload.get('medications')
	medications = None
	if medications_field:
		try:
			if isinstance(medications_field, str) and medications_field.strip().startswith('['):
				medications = json.loads(medications_field)
			elif isinstance(medications_field, str):
				medications = [m.strip() for m in medications_field.split(',') if m.strip()]
			else:
				medications = medications_field
		except Exception:
			medications = [medications_field]

	# allergies: accept comma-separated values and convert to text[]
	allergies_field = payload.get('allergies')
	allergies = None
	if allergies_field:
		if isinstance(allergies_field, str):
			allergies = [a.strip() for a in allergies_field.split(',') if a.strip()]
		else:
			allergies = allergies_field

	accessibility_needs = payload.get('accessibility_needs')
	preferred_language = payload.get('preferred_language')

	conn = get_db_conn()
	cur = conn.cursor()
	try:
		# Use psycopg2 Json wrapper for jsonb columns
		try:
			from psycopg2.extras import Json
		except Exception:
			Json = lambda x: json.dumps(x) if x is not None else None

		cur.execute(
			"""
				INSERT INTO public.users (
					display_name, username, email, phone, date_of_birth,
					emergency_contact, medications, allergies, accessibility_needs, preferred_language, created_at
				)
				VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
				ON CONFLICT (username) DO UPDATE SET
					display_name = EXCLUDED.display_name,
					email = EXCLUDED.email,
					phone = EXCLUDED.phone,
					date_of_birth = EXCLUDED.date_of_birth,
					emergency_contact = EXCLUDED.emergency_contact,
					medications = EXCLUDED.medications,
					allergies = EXCLUDED.allergies,
					accessibility_needs = EXCLUDED.accessibility_needs,
					preferred_language = EXCLUDED.preferred_language
				RETURNING id
			""",
			(
				display_name,
				username,
				email,
				phone,
				date_of_birth,
				Json(emergency_contact) if emergency_contact is not None else None,
				Json(medications) if medications is not None else None,
				allergies,
				accessibility_needs,
				preferred_language,
			),
		)
		user_id = cur.fetchone()[0]
		conn.commit()
	except Exception as exc:
		conn.rollback()
		app.logger.exception('register: db error')
		return jsonify({'ok': False, 'error': 'db_error', 'detail': str(exc)}), 500
	finally:
		cur.close()
		conn.close()

	# If the client provided an image data URL or temp path, attach it to the user and insert embedding
	image_data_url = payload.get('image') or payload.get('face_image') or payload.get('image_url')
	temp_path = payload.get('temp_storage_path') or payload.get('temp_path')
	if image_data_url or temp_path:
		try:
			if image_data_url:
				# Accept data URL, HTTP(S) URL, or storage path
				if isinstance(image_data_url, str) and (image_data_url.startswith('http://') or image_data_url.startswith('https://')):
					import requests
					resp = requests.get(image_data_url, timeout=20)
					resp.raise_for_status()
					img_bytes = resp.content
					img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
					img_arr = np.array(img)
				elif isinstance(image_data_url, str) and image_data_url.startswith('data:'):
					img_arr, img_bytes = decode_base64_image(image_data_url)
				else:
					# treat as storage path
					try:
						raw = download_from_storage(image_data_url)
						img_bytes = raw
						img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
						img_arr = np.array(img)
					except Exception:
						img_arr, img_bytes = decode_base64_image(image_data_url)
			else:
				# download from temp storage and re-upload into user folder
				raw = download_from_storage(temp_path)
				img_bytes = raw
				from PIL import Image as PILImage
				import numpy as np
				img = PILImage.open(io.BytesIO(img_bytes)).convert('RGB')
				img_arr = np.array(img)

			save_debug_image('register', img_arr)
			conn = get_db_conn()
			cur = conn.cursor()
			try:
				filename = f"{int(time.time())}_{uuid.uuid4().hex}.jpg"
				storage_path = f"{user_id}/{filename}"
				public_url = save_image_to_storage(storage_path, img_bytes) or storage_path
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
				encoding = compute_face_encoding(img_arr)
				if encoding is not None:
					insert_embedding(cur, user_id, encoding, 'register')
				conn.commit()
			except Exception as exc:
				conn.rollback()
				app.logger.exception('register: failed to attach image')
			finally:
				cur.close()
				conn.close()
		except Exception:
			app.logger.exception('register: image handling failed')

	return jsonify({'ok': True, 'user_id': str(user_id), 'display_name': display_name}), 201


# Legacy POST /signup route used by the web client (form POST)
@app.route('/signup', methods=['POST'])
def signup_post():
	# reuse api_register which reads from the same request context
	return api_register()


@app.route('/api/attach_image', methods=['POST'])
def api_attach_image():
	"""Attach an image to an existing user. Accepts `user_id` and `face_image` (data URL)
	or `temp_storage_path`. This runs in its own transactions and won't rollback user creation.
	"""
	payload = request.get_json(force=True) if request.is_json else request.form.to_dict()
	user_id = payload.get('user_id')
	if not user_id:
		return jsonify({'ok': False, 'error': 'missing_user_id'}), 400

	data_url = payload.get('face_image') or payload.get('image')
	temp_path = payload.get('temp_storage_path') or payload.get('temp_path')
	if not data_url and not temp_path:
		return jsonify({'ok': False, 'error': 'missing_image'}), 400

	try:
		if data_url:
			# Accept HTTP(S) URL, data URL, or treat as storage path. Prefer public URL.
			if isinstance(data_url, str) and (data_url.startswith('http://') or data_url.startswith('https://')):
				import requests
				r = requests.get(data_url, timeout=20)
				r.raise_for_status()
				img_bytes = r.content
				img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
				img_arr = np.array(img)
			elif isinstance(data_url, str) and data_url.startswith('data:'):
				img_arr, img_bytes = decode_base64_image(data_url)
			else:
				fetched = False
				if sb and SUPABASE_BUCKET:
					try:
						pub = _public_or_signed_url(data_url)
						if pub:
							import requests
							r = requests.get(pub, timeout=20)
							r.raise_for_status()
							img_bytes = r.content
							img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
							img_arr = np.array(img)
							fetched = True
					except Exception:
						fetched = False
				if not fetched:
					try:
						raw = download_from_storage(data_url)
						img_bytes = raw
						img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
						img_arr = np.array(img)
					except Exception:
						img_arr, img_bytes = decode_base64_image(data_url)
		else:
			raw = download_from_storage(temp_path)
			img_bytes = raw
			from PIL import Image as PILImage
			import numpy as np
			img = PILImage.open(io.BytesIO(img_bytes)).convert('RGB')
			img_arr = np.array(img)

		save_debug_image('attach', img_arr)

		# Insert user_images in its own transaction
		try:
			img_conn = get_db_conn()
			img_cur = img_conn.cursor()
			filename = f"{int(time.time())}_{uuid.uuid4().hex}.jpg"
			storage_path = f"{user_id}/{filename}"
			public_url = save_image_to_storage(storage_path, img_bytes) or storage_path
			img_cur.execute(
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
			img_conn.commit()
		except Exception:
			try:
				img_conn.rollback()
			except Exception:
				pass
			app.logger.exception('attach_image: failed to insert user_images')
			return jsonify({'ok': False, 'error': 'image_save_failed'}), 500
		finally:
			try:
				img_cur.close()
				img_conn.close()
			except Exception:
				pass

		# Try to compute encoding and insert embedding separately
		try:
			encoding = compute_face_encoding(img_arr)
			if encoding is not None:
				emb_conn = get_db_conn()
				emb_cur = emb_conn.cursor()
				try:
					insert_embedding(emb_cur, user_id, encoding, 'attach')
					emb_conn.commit()
				except Exception:
					try:
						emb_conn.rollback()
					except Exception:
						pass
					app.logger.exception('attach_image: failed to insert embedding')
				finally:
					try:
						emb_cur.close()
						emb_conn.close()
					except Exception:
						pass
		except Exception:
			app.logger.exception('attach_image: encoding failed')

		return jsonify({'ok': True, 'storage_path': storage_path, 'public_url': public_url}), 201
	except Exception as exc:
		app.logger.exception('attach_image: unexpected')
		return jsonify({'ok': False, 'error': 'unexpected', 'detail': str(exc)}), 500


@app.route('/api/login_face', methods=['POST'])
def api_login_face():
	payload = request.get_json(force=True) if request.is_json else request.form.to_dict()
	data_url = payload.get('face_image') or payload.get('image')
	if not data_url:
		return jsonify({'ok': False, 'error': 'missing_image'}), 400
	# Accept data URL, HTTP(S) URL, or storage path
	try:
		if isinstance(data_url, str) and (data_url.startswith('http://') or data_url.startswith('https://')):
			import requests
			resp = requests.get(data_url, timeout=20)
			resp.raise_for_status()
			img_bytes = resp.content
			img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
			img_arr = np.array(img)
		elif isinstance(data_url, str) and data_url.startswith('data:'):
			img_arr, _ = decode_base64_image(data_url)
		else:
			fetched = False
			if sb and SUPABASE_BUCKET:
				try:
					pub = _public_or_signed_url(data_url)
					if pub:
						import requests
						r = requests.get(pub, timeout=20)
						r.raise_for_status()
						img_bytes = r.content
						img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
						img_arr = np.array(img)
						fetched = True
				except Exception:
					fetched = False
			if not fetched:
				try:
					raw = download_from_storage(data_url)
					img_bytes = raw
					img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
					img_arr = np.array(img)
				except Exception:
					img_arr, _ = decode_base64_image(data_url)
	except Exception as exc:
		return jsonify({'ok': False, 'error': 'bad_image', 'detail': str(exc)}), 400

	encoding = compute_face_encoding(img_arr)
	if encoding is None:
		return jsonify({'ok': False, 'error': 'no_face', 'message': 'No face detected. Ensure good lighting, clear focus on face, and try again.'}), 200

	threshold = float(payload.get('threshold') or 0.5)
	limit = int(payload.get('limit') or 1)
	# Nearest-embedding lookup requires the pgvector `vector` type and
	# a DB-side function such as `public.find_nearest_embeddings`. If the
	# database does not have pgvector installed, fail early with a helpful
	# error so callers know to enable the extension or provide an alternative.
	if not _detect_vector_type():
		return jsonify({'ok': False, 'error': 'nearest_embeddings_not_supported', 'detail': 'pgvector extension / vector type is not available in the database'}), 501

	conn = get_db_conn()
	cur = conn.cursor()
	try:
		vec_literal = 'ARRAY[' + ','.join(repr(float(x)) for x in encoding) + ']::vector_ext.vector'
		# Call the DB helper with the requested `limit` and then apply the
		# distance threshold in Python. This avoids relying on a second
		# parameter in the DB function being used as a threshold.
		sql = f"""
			SELECT embedding_id, user_id, dist
			FROM public.find_nearest_embeddings({vec_literal}, %s)
		"""
		cur.execute(sql, (limit,))
		row = cur.fetchone()
		if not row:
			conn.commit()
			return jsonify({'ok': False, 'error': 'no_match'}), 200
		_, user_id, dist = row
		# dist is returned as double precision; ensure it's compared to the
		# caller-provided threshold (lower is closer for L2 distance)
		if dist is None or float(dist) > threshold:
			conn.commit()
			return jsonify({'ok': False, 'error': 'no_match', 'min_distance': float(dist) if dist is not None else None}), 200
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


@app.route('/api/admin/embeddings', methods=['GET'])
def api_admin_embeddings():
	"""Admin helper: return embedding metadata for a user. Not secure; intended for local testing only."""
	user_id = request.args.get('user_id')
	if not user_id:
		return jsonify({'ok': False, 'error': 'missing_user_id'}), 400
	try:
		conn = get_db_conn()
		cur = conn.cursor()
		cur.execute("SELECT id, user_id, source, created_at, (embedding IS NOT NULL) as has_embedding FROM public.embeddings WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
		rows = cur.fetchall()
		items = []
		for r in rows:
			items.append({'id': str(r[0]), 'user_id': str(r[1]), 'source': r[2], 'created_at': r[3].isoformat() if getattr(r[3],'isoformat',None) else str(r[3]), 'has_embedding': bool(r[4])})
		cur.close()
		conn.close()
		return jsonify({'ok': True, 'count': len(items), 'items': items}), 200
	except Exception as exc:
		app.logger.exception('admin/embeddings: db error')
		try:
			cur.close()
		except Exception:
			pass
		try:
			conn.close()
		except Exception:
			pass
		return jsonify({'ok': False, 'error': 'db_error', 'detail': str(exc)}), 500


@app.route('/api/users/<user_id>', methods=['GET'])
def api_get_user(user_id):
	"""Return user record, images and embedding metadata."""
	# Only allow the owner (actor) to read this user's details
	actor = _get_actor_user_id()
	if not actor or str(actor) != str(user_id):
		return jsonify({'ok': False, 'error': 'forbidden', 'detail': 'actor must match user_id'}), 403

	try:
		conn = get_db_conn()
		cur = conn.cursor()
		cur.execute("SELECT id, display_name, username, email, phone, date_of_birth, emergency_contact, medications, allergies, accessibility_needs, preferred_language, created_at FROM public.users WHERE id = %s", (user_id,))
		row = cur.fetchone()
		if not row:
			cur.close()
			conn.close()
			return jsonify({'ok': False, 'error': 'user_missing'}), 404

		user = {
			'id': str(row[0]),
			'display_name': row[1],
			'username': row[2],
			'email': row[3],
			'phone': row[4],
			'date_of_birth': row[5],
			'emergency_contact': row[6],
			'medications': row[7],
			'allergies': row[8],
			'accessibility_needs': row[9],
			'preferred_language': row[10],
			'created_at': row[11].isoformat() if getattr(row[11], 'isoformat', None) else str(row[11])
		}

		cur.execute("SELECT id, storage_path, public_url, is_profile, uploaded_at FROM public.user_images WHERE user_id = %s ORDER BY uploaded_at DESC", (user_id,))
		images = []
		for r in cur.fetchall():
			images.append({'id': str(r[0]), 'storage_path': r[1], 'public_url': r[2], 'is_profile': bool(r[3]), 'uploaded_at': r[4].isoformat() if getattr(r[4], 'isoformat', None) else str(r[4])})

		cur.execute("SELECT count(*) FROM public.embeddings WHERE user_id = %s", (user_id,))
		emb_count = cur.fetchone()[0]

		cur.close()
		conn.close()
		return jsonify({'ok': True, 'user': user, 'images': images, 'embedding_count': int(emb_count)}), 200
	except Exception as exc:
		app.logger.exception('get_user: db error')
		try:
			cur.close()
		except Exception:
			pass
		try:
			conn.close()
		except Exception:
			pass
		return jsonify({'ok': False, 'error': 'db_error', 'detail': str(exc)}), 500


@app.route('/api/users/<user_id>', methods=['PUT'])
def api_update_user(user_id):
	"""Update allowed user fields."""
	payload = request.get_json(force=True) if request.is_json else request.form.to_dict()
	allowed = ['display_name', 'email', 'phone', 'date_of_birth', 'emergency_contact', 'medications', 'allergies', 'accessibility_needs', 'preferred_language']
	updates = {}
	for k in allowed:
		if k in payload:
			updates[k] = payload.get(k)

	if not updates:
		return jsonify({'ok': False, 'error': 'no_updates'}), 400

	# Owner-only: ensure caller is the same user
	actor = _get_actor_user_id()
	if not actor or str(actor) != str(user_id):
		return jsonify({'ok': False, 'error': 'forbidden', 'detail': 'actor must match user_id'}), 403

	try:
		conn = get_db_conn()
		cur = conn.cursor()
		try:
			try:
				from psycopg2.extras import Json
			except Exception:
				Json = lambda x: json.dumps(x) if x is not None else None

			set_clauses = []
			params = []
			for k, v in updates.items():
				if k in ('emergency_contact', 'medications'):
					set_clauses.append(f"{k} = %s")
					params.append(Json(v) if v is not None else None)
				else:
					set_clauses.append(f"{k} = %s")
					params.append(v)

			params.append(user_id)
			sql = f"UPDATE public.users SET {', '.join(set_clauses)} WHERE id = %s RETURNING id"
			cur.execute(sql, tuple(params))
			if not cur.fetchone():
				conn.rollback()
				cur.close()
				conn.close()
				return jsonify({'ok': False, 'error': 'user_missing'}), 404
			conn.commit()
		except Exception as exc:
			conn.rollback()
			app.logger.exception('update_user: db error')
			cur.close()
			conn.close()
			return jsonify({'ok': False, 'error': 'db_error', 'detail': str(exc)}), 500
		cur.close()
		conn.close()
		return jsonify({'ok': True}), 200
	except Exception as exc:
		app.logger.exception('update_user: unexpected')
		try:
			cur.close()
		except Exception:
			pass
		try:
			conn.close()
		except Exception:
			pass
		return jsonify({'ok': False, 'error': 'unexpected', 'detail': str(exc)}), 500


@app.route('/api/users/<user_id>', methods=['DELETE'])
def api_delete_user(user_id):
	"""Delete user and related DB rows. Attempts to remove storage files if configured.
	Returns list of removed storage paths (DB rows) so client can confirm storage cleanup.
	"""
	# Owner-only: ensure caller is the same user
	actor = _get_actor_user_id()
	if not actor or str(actor) != str(user_id):
		return jsonify({'ok': False, 'error': 'forbidden', 'detail': 'actor must match user_id'}), 403

	try:
		conn = get_db_conn()
		cur = conn.cursor()
		# collect user image paths
		cur.execute("SELECT storage_path FROM public.user_images WHERE user_id = %s", (user_id,))
		paths = [r[0] for r in cur.fetchall() if r[0]]

		# delete embeddings, images, then user
		cur.execute("DELETE FROM public.embeddings WHERE user_id = %s", (user_id,))
		cur.execute("DELETE FROM public.user_images WHERE user_id = %s", (user_id,))
		cur.execute("DELETE FROM public.users WHERE id = %s RETURNING id", (user_id,))
		res = cur.fetchone()
		if not res:
			conn.rollback()
			cur.close()
			conn.close()
			return jsonify({'ok': False, 'error': 'user_missing'}), 404
		conn.commit()
		cur.close()
		conn.close()

		removed_paths = []
		if sb and SUPABASE_BUCKET and paths:
			try:
				for p in paths:
					try:
						# supabase storage client may accept list or single path depending on SDK
						sb.storage.from_(SUPABASE_BUCKET).remove([p])
						removed_paths.append(p)
					except Exception:
						app.logger.exception('failed to remove storage path: %s', p)
			except Exception:
				app.logger.exception('storage removal error')

		return jsonify({'ok': True, 'removed_storage_paths': removed_paths}), 200
	except Exception as exc:
		app.logger.exception('delete_user: db error')
		try:
			cur.close()
		except Exception:
			pass
		try:
			conn.close()
		except Exception:
			pass
		return jsonify({'ok': False, 'error': 'db_error', 'detail': str(exc)}), 500


@app.route('/api/user_images/<image_id>', methods=['DELETE'])
def api_delete_image(image_id):
	"""Delete a single user_images row and attempt storage removal."""
	# Owner-only: only the owner of the image may delete it. We verify by
	# checking the image row's user_id against the caller identity.
	actor = _get_actor_user_id()
	if not actor:
		return jsonify({'ok': False, 'error': 'forbidden', 'detail': 'missing actor identity'}), 403

	try:
		conn = get_db_conn()
		cur = conn.cursor()
		cur.execute("SELECT storage_path FROM public.user_images WHERE id = %s", (image_id,))
		row = cur.fetchone()
		if not row:
			cur.close()
			conn.close()
			return jsonify({'ok': False, 'error': 'image_missing'}), 404
		path = row[0]
		# verify ownership
		cur.execute("SELECT user_id FROM public.user_images WHERE id = %s", (image_id,))
		owner_row = cur.fetchone()
		if not owner_row or str(owner_row[0]) != str(actor):
			cur.close()
			conn.close()
			return jsonify({'ok': False, 'error': 'forbidden', 'detail': 'not image owner'}), 403
		cur.execute("DELETE FROM public.user_images WHERE id = %s RETURNING id", (image_id,))
		res = cur.fetchone()
		if not res:
			conn.rollback()
			cur.close()
			conn.close()
			return jsonify({'ok': False, 'error': 'delete_failed'}), 500
		conn.commit()
		cur.close()
		conn.close()

		removed = False
		if sb and SUPABASE_BUCKET and path:
			try:
				sb.storage.from_(SUPABASE_BUCKET).remove([path])
				removed = True
			except Exception:
				app.logger.exception('delete_image: storage remove failed for %s', path)

		return jsonify({'ok': True, 'removed_from_storage': removed, 'storage_path': path}), 200
	except Exception as exc:
		app.logger.exception('delete_image: db error')
		try:
			cur.close()
		except Exception:
			pass
		try:
			conn.close()
		except Exception:
			pass
		return jsonify({'ok': False, 'error': 'db_error', 'detail': str(exc)}), 500


if __name__ == '__main__':
	os.makedirs(DATA_DIR, exist_ok=True)
	print('webapp.py: launching Flask on http://0.0.0.0:5000', flush=True)
	app.run(host='0.0.0.0', port=5000, debug=True)