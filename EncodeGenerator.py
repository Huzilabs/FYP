import os
import pickle
import numpy as np
import face_recognition
from db_supabase import save_embedding, upload_user_image, add_user
from dotenv import load_dotenv
from uuid import uuid4

load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
NAMES_FILE = os.path.join(DATA_DIR, 'names.pkl')
FACES_FILE = os.path.join(DATA_DIR, 'faces_data.pkl')


def load_local_data():
    with open(NAMES_FILE, 'rb') as f:
        names = pickle.load(f)
    with open(FACES_FILE, 'rb') as f:
        faces = pickle.load(f)
    return names, faces


def generate_and_upload():
    names, faces = load_local_data()
    print(f"Loaded {len(names)} names and {faces.shape[0]} faces from local data")

    for idx, name in enumerate(names):
        try:
            print(f"Processing {idx+1}/{len(names)}: {name}")
            # faces contains flattened images; reshape back to approx 50x150x1 or 50x150x3 depending on source
            face_flat = faces[idx]
            # Heuristic: try to reshape to something plausible (most datasets store 7500 = 50*50*3? adjust as needed)
            possible_shapes = [(50,50,3),(50,150,1),(150,50,1),(75,100,1)]
            img = None
            for s in possible_shapes:
                try:
                    arr = np.array(face_flat)
                    img = arr.reshape(s)
                    break
                except Exception:
                    img = None
            if img is None:
                print(f"Can't reshape face array for {name}, skipping image upload")
            else:
                # Convert to uint8
                img_u8 = np.clip(img, 0, 255).astype('uint8')
                # Save temporarily to file
                tmp_path = os.path.join('tmp', f'{uuid4().hex}.png')
                os.makedirs('tmp', exist_ok=True)
                from PIL import Image
                Image.fromarray(img_u8).save(tmp_path)
                # Upload to Supabase storage
                url = upload_user_image(name, tmp_path)
                print(f"Uploaded image for {name}: {url}")

            # Attempt to compute embedding using face_recognition
            # If faces images are not full photos, skip and log
            try:
                # face_recognition.face_encodings expects an image; if img is None we skip
                if img is None:
                    print(f"No image for {name}, skipping embedding generation")
                    continue
                encs = face_recognition.face_encodings(img_u8)
                if not encs:
                    print(f"No face found when encoding {name}, skipping")
                    continue
                embedding = encs[0]
                saved = save_embedding(name, embedding)
                print(f"Saved embedding for {name}: {saved}")
            except Exception as e:
                print(f"Error generating embedding for {name}: {e}")
        except Exception as e:
            print(f"Error processing {name}: {e}")

if __name__ == '__main__':
    generate_and_upload()
