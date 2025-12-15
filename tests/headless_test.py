"""Headless recognition test.

Usage:
  python tests/headless_test.py --image PATH_TO_TEST_IMAGE

Behavior:
- If SUPABASE_URL and SUPABASE_KEY are present in environment (via .env), it will load embeddings
  with `db_supabase.load_embeddings_for_recognition()`.
- Otherwise it will attempt to load `data/names.pkl` and `data/faces_data.pkl` from the repo.
- The script computes an encoding for the provided image and prints the top match (user_id/name and distance).
"""
import os
import sys
import argparse
import pickle
import numpy as np
import face_recognition

# Try to import db_supabase if credentials exist
USE_SUPABASE = bool(os.getenv('SUPABASE_URL')) and bool(os.getenv('SUPABASE_KEY'))
if USE_SUPABASE:
    try:
        from db_supabase import load_embeddings_for_recognition
    except Exception as e:
        print(f"Warning: failed to import db_supabase: {e}")
        USE_SUPABASE = False


DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
NAMES_FILE = os.path.join(DATA_DIR, 'names.pkl')
FACES_FILE = os.path.join(DATA_DIR, 'faces_data.pkl')


def load_local_pickles():
    if not os.path.exists(NAMES_FILE) or not os.path.exists(FACES_FILE):
        raise FileNotFoundError('Local data pickles not found in data/ (names.pkl, faces_data.pkl)')
    with open(NAMES_FILE, 'rb') as f:
        names = pickle.load(f)
    with open(FACES_FILE, 'rb') as f:
        faces = pickle.load(f)
    # faces may already be encodings or flattened images; we try to interpret
    # If faces looks like a list of 128-d embeddings, use them directly.
    arr = np.array(faces)
    if arr.ndim == 2 and arr.shape[1] in (128, 512):
        encodings = [np.array(x, dtype=float) for x in arr]
    else:
        # attempt to compute encodings from reconstructed images
        encodings = []
        for i, flat in enumerate(arr):
            try:
                img = np.array(flat)
                # try reshape heuristics for common shapes
                possible = [(50,50,3),(50,150,3),(75,100,3),(150,50,3),(50,50)]
                reshaped = None
                for s in possible:
                    try:
                        reshaped = img.reshape(s)
                        break
                    except Exception:
                        reshaped = None
                if reshaped is None:
                    continue
                # If single-channel, convert to RGB
                if reshaped.ndim == 2:
                    rgb = reshaped
                elif reshaped.shape[2] == 1:
                    rgb = reshaped[:,:,0]
                else:
                    rgb = reshaped[:,:,:3]
                encs = face_recognition.face_encodings(np.asarray(rgb))
                if encs:
                    encodings.append(encs[0])
            except Exception:
                continue
    return names, encodings


def load_known():
    if USE_SUPABASE:
        print('Loading embeddings from Supabase...')
        encs, ids = load_embeddings_for_recognition()
        encs = [np.array(e, dtype=float) for e in encs]
        return ids, encs
    else:
        print('Loading local pickles...')
        names, encs = load_local_pickles()
        return names, encs


def get_image_encoding(path: str):
    img = face_recognition.load_image_file(path)
    encs = face_recognition.face_encodings(img)
    if not encs:
        raise RuntimeError('No face found in test image')
    return encs[0]


def find_best_match(test_enc, known_encs, known_ids):
    if not known_encs:
        return None, None
    dists = face_recognition.face_distance(known_encs, test_enc)
    best_idx = int(np.argmin(dists))
    return known_ids[best_idx], float(dists[best_idx])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--image', '-i', required=True, help='Path to test image')
    args = p.parse_args()

    if not os.path.exists(args.image):
        print('Test image not found:', args.image)
        sys.exit(2)

    known_ids, known_encs = load_known()
    print(f'Known encodings: {len(known_encs)}')

    try:
        test_enc = get_image_encoding(args.image)
    except Exception as e:
        print('Failed to get encoding from test image:', e)
        sys.exit(3)

    match_id, dist = find_best_match(test_enc, known_encs, known_ids)
    if match_id is None:
        print('No known encodings to compare against')
        sys.exit(0)

    print(f'Best match: {match_id}  (distance={dist:.4f})')
    # Show top 5 distances for debugging
    dists = face_recognition.face_distance(known_encs, test_enc)
    top5 = np.argsort(dists)[:5]
    print('Top 5:')
    for idx in top5:
        print(f'  {known_ids[idx]} -> {dists[idx]:.4f}')


if __name__ == '__main__':
    main()
