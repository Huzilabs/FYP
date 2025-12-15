# Complete Supabase Face Recognition Code

## Copy each section below into separate .py files

===============================================================================
FILE: db_supabase.py
===============================================================================

```python
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import numpy as np
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Set SUPABASE_URL and SUPABASE_KEY in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def add_user(user_id: str, name: str, major: str, starting_year: int,
             standing: str, year: int) -> Dict:
    data = {
        "id": user_id,
        "name": name,
        "major": major,
        "starting_year": starting_year,
        "total_attendance": 0,
        "standing": standing,
        "year": year,
        "last_attendance_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    response = supabase.table("users").upsert(data).execute()
    return response.data[0] if response.data else None

def get_user(user_id: str) -> Optional[Dict]:
    response = supabase.table("users").select("*").eq("id", user_id).execute()
    return response.data[0] if response.data else None

def update_attendance(user_id: str) -> bool:
    user = get_user(user_id)
    if not user:
        return False
    new_total = user.get("total_attendance", 0) + 1
    data = {
        "total_attendance": new_total,
        "last_attendance_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    response = supabase.table("users").update(data).eq("id", user_id).execute()
    return len(response.data) > 0

def save_embedding(user_id: str, embedding: np.ndarray) -> bool:
    embedding_list = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding
    data = {
        "user_id": user_id,
        "embedding": embedding_list,
        "created_at": datetime.now().isoformat()
    }
    try:
        response = supabase.table("embeddings").insert(data).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error saving embedding: {e}")
        return False

def get_all_embeddings() -> List[Tuple[str, np.ndarray]]:
    response = supabase.table("embeddings").select("user_id, embedding").execute()
    embeddings = []
    for row in response.data:
        user_id = row["user_id"]
        embedding = np.array(row["embedding"], dtype=np.float64)
        embeddings.append((user_id, embedding))
    return embeddings

def load_embeddings_for_recognition() -> Tuple[List[np.ndarray], List[str]]:
    all_embeddings = get_all_embeddings()
    encode_list = []
    user_ids = []
    for user_id, embedding in all_embeddings:
        encode_list.append(embedding)
        user_ids.append(user_id)
    return encode_list, user_ids

def upload_user_image(user_id: str, image_path: str) -> Optional[str]:
    try:
        with open(image_path, 'rb') as f:
            file_data = f.read()
        file_name = f"users/{user_id}.png"
        response = supabase.storage.from_("images").upload(
            file_name, file_data,
            file_options={"content-type": "image/png", "upsert": "true"}
        )
        public_url = supabase.storage.from_("images").get_public_url(file_name)
        return public_url
    except Exception as e:
        print(f"Error uploading image: {e}")
        return None

def download_user_image(user_id: str) -> Optional[bytes]:
    try:
        file_name = f"users/{user_id}.png"
        response = supabase.storage.from_("images").download(file_name)
        return response
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

def log_attendance(user_id: str, method: str = "face", confidence: float = None) -> bool:
    data = {
        "user_id": user_id,
        "timestamp": datetime.now().isoformat(),
        "method": method,
        "confidence": confidence
    }
    try:
        response = supabase.table("attendance_log").insert(data).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error logging attendance: {e}")
        return False

def check_recent_attendance(user_id: str, min_seconds: int = 30) -> bool:
    user = get_user(user_id)
    if not user or not user.get("last_attendance_time"):
        return False
    try:
        last_time = datetime.strptime(user["last_attendance_time"], "%Y-%m-%d %H:%M:%S")
        seconds_elapsed = (datetime.now() - last_time).total_seconds()
        return seconds_elapsed < min_seconds
    except Exception as e:
        print(f"Error checking recent attendance: {e}")
        return False

def get_all_users() -> List[Dict]:
    response = supabase.table("users").select("*").execute()
    return response.data if response.data else []

if __name__ == "__main__":
    print("Testing Supabase connection...")
    try:
        users = get_all_users()
        print(f"✓ Connected! Found {len(users)} users.")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
```

===============================================================================
FILE: AddDataToDatabase.py
===============================================================================

```python
from db_supabase import add_user

data = {
    "321654": {
        "name": "Murtaza Hassan",
        "major": "Robotics",
        "starting_year": 2017,
        "standing": "G",
        "year": 4
    },
    "852741": {
        "name": "Emly Blunt",
        "major": "Economics",
        "starting_year": 2021,
        "standing": "B",
        "year": 1
    },
    "963852": {
        "name": "Elon Musk",
        "major": "Physics",
        "starting_year": 2020,
        "standing": "G",
        "year": 2
    }
}

print("Adding users to Supabase...")
for user_id, info in data.items():
    result = add_user(
        user_id=user_id,
        name=info["name"],
        major=info["major"],
        starting_year=info["starting_year"],
        standing=info["standing"],
        year=info["year"]
    )
    if result:
        print(f"✓ Added {info['name']} (ID: {user_id})")
    else:
        print(f"✗ Failed to add {info['name']}")

print("\nDone!")
```

===============================================================================
FILE: EncodeGenerator.py
===============================================================================

```python
import cv2
import face_recognition
import os
from db_supabase import save_embedding, upload_user_image, get_user
import pickle

def find_encodings(images_list):
    encode_list = []
    for idx, img in enumerate(images_list):
        if img is None:
            print(f"Warning: Image {idx} is None, skipping...")
            continue
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(img_rgb)
        if len(encodings) == 0:
            print(f"Warning: No face in image {idx}")
            continue
        encode = encodings[0]
        encode_list.append(encode)
    return encode_list

def main():
    folder_path = 'Images'
    if not os.path.exists(folder_path):
        print(f"Error: '{folder_path}' not found!")
        return

    path_list = os.listdir(folder_path)
    if not path_list:
        print(f"Error: No images in '{folder_path}'!")
        return

    print(f"Found {len(path_list)} images")
    img_list = []
    user_ids = []
    valid_paths = []

    for path in path_list:
        if not path.lower().endswith(('.png', '.jpg', '.jpeg')):
            continue
        img_path = os.path.join(folder_path, path)
        img = cv2.imread(img_path)
        if img is None:
            continue
        img_list.append(img)
        user_ids.append(os.path.splitext(path)[0])
        valid_paths.append(img_path)

    print(f"Processing {len(img_list)} images...")
    encode_list_known = find_encodings(img_list)

    if len(encode_list_known) != len(user_ids):
        user_ids = user_ids[:len(encode_list_known)]
        valid_paths = valid_paths[:len(encode_list_known)]

    print(f"Generated {len(encode_list_known)} encodings")
    print("Uploading to Supabase...")

    for user_id, encoding, img_path in zip(user_ids, encode_list_known, valid_paths):
        user = get_user(user_id)
        if not user:
            print(f"Warning: User {user_id} not in database")
            continue
        if save_embedding(user_id, encoding):
            print(f"✓ Saved embedding for {user_id}")
        upload_user_image(user_id, img_path)

    # Save local backup
    encode_list_known_with_ids = [encode_list_known, user_ids]
    with open("EncodeFile.p", 'wb') as file:
        pickle.dump(encode_list_known_with_ids, file)
    print("✓ Local backup saved")
    print("Done!")

if __name__ == "__main__":
    main()
```

===============================================================================
FILE: Main.py
===============================================================================

```python
import os
import numpy as np
import cv2
import face_recognition
try:
    import cvzone
    HAS_CVZONE = True
except ImportError:
    HAS_CVZONE = False
    print("cvzone not found, using basic overlay")

from db_supabase import (
    get_user, update_attendance, download_user_image,
    load_embeddings_for_recognition, check_recent_attendance, log_attendance
)

cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)

background_path = 'Resources/background.png'
if os.path.exists(background_path):
    imgBackground = cv2.imread(background_path)
else:
    imgBackground = None

mode_images = []
modes_path = 'Resources/Modes'
if os.path.exists(modes_path):
    for path in sorted(os.listdir(modes_path)):
        img = cv2.imread(os.path.join(modes_path, path))
        if img is not None:
            mode_images.append(img)
if not mode_images:
    for i in range(4):
        mode_images.append(np.zeros((633, 414, 3), dtype=np.uint8))

print("Loading encodings...")
encode_list_known, user_ids = load_embeddings_for_recognition()
print(f"Loaded {len(user_ids)} users")

mode_type = 0
counter = 0
current_user_id = -1
img_user = []

print("Press 'q' to quit")

while True:
    success, img = cap.read()
    if not success:
        break

    img_small = cv2.resize(img, (0, 0), None, 0.25, 0.25)
    img_small = cv2.cvtColor(img_small, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(img_small)
    face_encodings = face_recognition.face_encodings(img_small, face_locations)

    if imgBackground is not None:
        display_img = imgBackground.copy()
        display_img[162:162 + 480, 55:55 + 640] = img
        display_img[44:44 + 633, 808:808 + 414] = mode_images[mode_type]
    else:
        display_img = img.copy()

    if face_locations:
        for encode_face, face_loc in zip(face_encodings, face_locations):
            matches = face_recognition.compare_faces(encode_list_known, encode_face)
            face_distances = face_recognition.face_distance(encode_list_known, encode_face)
            match_index = np.argmin(face_distances)

            if matches[match_index]:
                y1, x2, y2, x1 = face_loc
                y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4

                if imgBackground is not None and HAS_CVZONE:
                    bbox = 55 + x1, 162 + y1, x2 - x1, y2 - y1
                    display_img = cvzone.cornerRect(display_img, bbox, rt=0)
                else:
                    cv2.rectangle(display_img, (x1, y1), (x2, y2), (0, 255, 0), 2)

                current_user_id = user_ids[match_index]
                if counter == 0:
                    counter = 1
                    mode_type = 1

        if counter != 0:
            if counter == 1:
                user_info = get_user(current_user_id)
                if user_info:
                    print(f"Recognized: {user_info['name']}")
                    if not check_recent_attendance(current_user_id, 30):
                        update_attendance(current_user_id)
                        log_attendance(current_user_id, "face", 0.9)
                        print("  Attendance marked")

            if mode_type != 3 and 10 < counter < 20:
                mode_type = 2

            counter += 1
            if counter >= 20:
                counter = 0
                mode_type = 0
    else:
        mode_type = 0
        counter = 0

    cv2.imshow("Face Attendance", display_img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

===============================================================================
FILE: requirements.txt
===============================================================================

```
supabase==2.13.1
python-dotenv==1.0.0
opencv-python==4.10.0.84
numpy==1.24.3
Pillow==10.4.0
cvzone==1.6.1
```

Note: Install dlib and face_recognition via conda, not pip!

===============================================================================
FILE: .env.example
===============================================================================

```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-anon-key-here
```

Copy this to .env and fill in your actual Supabase credentials.

===============================================================================
