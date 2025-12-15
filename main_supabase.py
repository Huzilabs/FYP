"""Simple entrypoint for Supabase-backed face recognition.

This file is a clean, minimal replacement for the corrupted Main.py. It loads
embeddings from Supabase, opens the webcam, performs recognition, and logs
attendance.

Run with: python main_supabase.py
"""

import time
from typing import List, Tuple

import numpy as np
import face_recognition
import cv2
from dotenv import load_dotenv

from db_supabase import load_embeddings_for_recognition, log_attendance, update_attendance

load_dotenv()

# Load known embeddings from Supabase
encode_list_known, user_ids = load_embeddings_for_recognition()
encode_list_known = [np.array(e) for e in encode_list_known]

print(f"Loaded {len(user_ids)} known embeddings from Supabase")

# Threshold for face distance; lower = stricter match
DIST_THRESHOLD = 0.6


def recognize_once(frame: np.ndarray) -> List[Tuple[Tuple[int, int, int, int], str, float]]:
    """Detect faces in a single frame and match against known encodings.

    Returns a list of tuples: (location, user_id_or_None, distance_or_None)
    """
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    boxes = face_recognition.face_locations(rgb)
    encodings = face_recognition.face_encodings(rgb, boxes)

    results = []
    for i, enc in enumerate(encodings):
        if not encode_list_known:
            results.append((None, None, None))
            continue
        dists = face_recognition.face_distance(encode_list_known, enc)
        best_idx = int(np.argmin(dists))
        best_dist = float(dists[best_idx])
        loc = boxes[i] if i < len(boxes) else None
        if best_dist < DIST_THRESHOLD:
            results.append((loc, user_ids[best_idx], best_dist))
        else:
            results.append((loc, None, best_dist))
    return results


def main_loop():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    last_seen = {}
    print("Starting recognition. Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        results = recognize_once(frame)
        for loc, user_id, dist in results:
            if loc:
                top, right, bottom, left = loc
                name = user_id if user_id else "Unknown"
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                if user_id:
                    now = time.time()
                    last = last_seen.get(user_id, 0)
                    if now - last > 30:
                        print(f"Recognized {user_id} (dist={dist:.3f})")
                        success = log_attendance(user_id, method='face', confidence=dist)
                        if success:
                            update_attendance(user_id)
                        last_seen[user_id] = now

        cv2.imshow('Recognition', frame)
        key = cv2.waitKey(1)
        if key & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main_loop()
