from flask import Flask, request, jsonify, render_template
import os
import io
import base64
from PIL import Image
import time
import pickle

print("webapp.py: starting (pid={})".format(os.getpid()), flush=True)
import os
import io
import base64
from PIL import Image
import time
import pickle

APP_ROOT = os.path.dirname(__file__)
DATA_DIR = os.path.join(APP_ROOT, "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
NAMES_PKL = os.path.join(DATA_DIR, "names.pkl")
FACES_PKL = os.path.join(DATA_DIR, "faces_data.pkl")
DIST_THRESHOLD = 0.5

app = Flask(__name__, template_folder="templates")

def ensure_data_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    if not os.path.exists(NAMES_PKL):
        with open(NAMES_PKL, "wb") as f:
            pickle.dump([], f)
    if not os.path.exists(FACES_PKL):
        with open(FACES_PKL, "wb") as f:
            pickle.dump([], f)

def load_local_embeddings():
    # lazy import numpy to avoid slow startup during imports
    import numpy as np
    ensure_data_dirs()
    with open(NAMES_PKL, "rb") as f:
        names = pickle.load(f)
    with open(FACES_PKL, "rb") as f:
        faces = pickle.load(f)
    # convert to numpy arrays
    faces = [np.array(x) for x in faces]
    return names, faces

def save_local_embedding(name, encoding):
    ensure_data_dirs()
    # save image info is handled by caller
    try:
        with open(NAMES_PKL, "rb") as f:
            names = pickle.load(f)
    except Exception:
        names = []
    try:
        with open(FACES_PKL, "rb") as f:
            faces = pickle.load(f)
    except Exception:
        faces = []
    names.append(name)
    faces.append(encoding.tolist())
    with open(NAMES_PKL, "wb") as f:
        pickle.dump(names, f)
    with open(FACES_PKL, "wb") as f:
        pickle.dump(faces, f)

def decode_base64_image(data_url):
    # data_url like 'data:image/jpeg;base64,/9j/4AAQ...'
    if "," not in data_url:
        raise ValueError("Not a data URL")
    header, b64 = data_url.split(",", 1)
    img_bytes = base64.b64decode(b64)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    # lazy import numpy here as well
    import numpy as np
    arr = np.array(img)
    return arr

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/signup", methods=["POST"])
def signup():
    # expects form fields: name, image (data URL)
    name = request.form.get("name", "").strip()
    image_data = request.form.get("image", "")
    app.logger.info(f"signup request for name={name} received")
    if not name:
        app.logger.warning("signup: missing name")
        return jsonify({"ok": False, "error": "missing_name"}), 400
    if not image_data:
        app.logger.warning("signup: missing image")
        return jsonify({"ok": False, "error": "missing_image"}), 400
    try:
        img = decode_base64_image(image_data)
    except Exception as e:
        app.logger.exception("signup: bad_image")
        return jsonify({"ok": False, "error": "bad_image", "detail": str(e)}), 400

    # lazy import face_recognition to avoid heavy import during startup
    import face_recognition
    encs = face_recognition.face_encodings(img)
    if not encs:
        app.logger.info("signup: no face detected in captured frame")
        # include a helpful suggestion in the response
        return jsonify({"ok": False, "error": "no_face", "detail": "No face detected. Ensure your face is centered, well-lit, and unobstructed."}), 200

    encoding = encs[0]
    # save image to data/images/<name>/timestamp.jpg
    person_dir = os.path.join(IMAGES_DIR, name)
    os.makedirs(person_dir, exist_ok=True)
    filename = os.path.join(person_dir, f"{int(time.time())}.jpg")
    # save with PIL (image is RGB)
    Image.fromarray(img).save(filename)

    save_local_embedding(name, encoding)
    app.logger.info(f"signup: saved embedding and image for {name}")
    return jsonify({"ok": True, "name": name})

@app.route("/login", methods=["POST"])
def login():
    # expects form field: image (data URL)
    image_data = request.form.get("image", "")
    if not image_data:
        return jsonify({"ok": False, "error": "missing_image"}), 400
    try:
        img = decode_base64_image(image_data)
    except Exception as e:
        return jsonify({"ok": False, "error": "bad_image", "detail": str(e)}), 400

    import face_recognition
    encs = face_recognition.face_encodings(img)
    if not encs:
        return jsonify({"ok": False, "error": "no_face"}), 200
    encoding = encs[0]
    names, faces = load_local_embeddings()
    if not names:
        return jsonify({"ok": False, "error": "no_registered"}), 200

    # compute distances
    faces_np = faces
    dists = face_recognition.face_distance(faces_np, encoding)
    # avoid importing numpy here; use ndarray method
    min_idx = int(dists.argmin())
    min_dist = float(dists[min_idx])
    if min_dist <= DIST_THRESHOLD:
        return jsonify({"ok": True, "name": names[min_idx], "distance": min_dist}), 200
    else:
        return jsonify({"ok": False, "error": "no_match", "min_distance": min_dist}), 200


@app.route("/welcome")
def welcome():
    # simple page shown after successful login; template reads query param or we could pass name
    return render_template("welcome.html")

if __name__ == "__main__":
    # quick safety: create data dir
    ensure_data_dirs()
    print("webapp.py: launching Flask on http://0.0.0.0:5000", flush=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
