"""Capture face images, generate pickles (names + encodings), and test recognition.

Usage examples (PowerShell):

# 1) Capture 5 images from webcam for user 'alice' (interactive; press space to capture each)
conda run -n face-recognition-project python tools\create_pickles_and_test.py --capture-name alice --capture-count 5

# 2) Generate pickles from an images tree data/images/<name>/*.jpg
conda run -n face-recognition-project python tools\create_pickles_and_test.py --from-images

# 3) Test recognition on an image using generated pickles
conda run -n face-recognition-project python tools\create_pickles_and_test.py --test-image path\to\img.jpg

# 4) Capture + generate + test in sequence
conda run -n face-recognition-project python tools\create_pickles_and_test.py --capture-name bob --capture-count 3 --from-images --test-image tests\example.jpg

Note: This script requires a working `face_recognition` installation (dlib) and a camera for capture.
"""

import os
import time
import argparse
import pickle
from pathlib import Path

import cv2
import numpy as np
import face_recognition


def capture_images(name: str, count: int = 5, out_root: Path = Path('data/images')) -> None:
    out_dir = out_root / name
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError('Cannot open camera for capture')
    print(f"Capture mode: press SPACE to capture a frame for '{name}'. Need {count} captures.")
    captured = 0
    while captured < count:
        ret, frame = cap.read()
        if not ret:
            print('Failed to read frame from camera')
            break
        disp = frame.copy()
        cv2.putText(disp, f'Press SPACE to capture ({captured}/{count}) or q to quit', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
        cv2.imshow('Capture', disp)
        key = cv2.waitKey(1)
        if key == ord('q'):
            break
        if key == 32:  # space
            # try to detect face and save cropped face if possible
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            locs = face_recognition.face_locations(rgb)
            if locs:
                top, right, bottom, left = locs[0]
                crop = frame[top:bottom, left:right]
                filename = out_dir / f'{int(time.time())}_{captured}.jpg'
                cv2.imwrite(str(filename), crop)
                print('Saved face crop to', filename)
            else:
                # save full frame as fallback
                filename = out_dir / f'{int(time.time())}_{captured}_full.jpg'
                cv2.imwrite(str(filename), frame)
                print('No face detected; saved full frame to', filename)
            captured += 1
    cap.release()
    cv2.destroyAllWindows()


def generate_pickles_from_images(images_root: Path = Path('data/images'), names_file: Path = Path('data/names.pkl'), faces_file: Path = Path('data/faces_data.pkl')) -> None:
    images_root = Path(images_root)
    if not images_root.exists():
        raise FileNotFoundError(f'Images root not found: {images_root}')
    names = []
    encs = []
    for p in sorted(images_root.iterdir()):
        if not p.is_dir():
            continue
        name = p.name
        print('Processing', name)
        found = False
        for img_path in sorted(p.glob('*')):
            try:
                img = face_recognition.load_image_file(str(img_path))
                locs = face_recognition.face_locations(img)
                if not locs:
                    continue
                e = face_recognition.face_encodings(img, locs)
                if e:
                    encs.append(e[0].tolist())
                    names.append(name)
                    found = True
                    print('  -> encoding from', img_path)
                    break
            except Exception as exc:
                print('  failed for', img_path, exc)
        if not found:
            print('  no faces found for', name)
    os.makedirs(names_file.parent, exist_ok=True)
    with open(names_file, 'wb') as f:
        pickle.dump(names, f)
    with open(faces_file, 'wb') as f:
        pickle.dump(encs, f)
    print('Wrote', names_file, 'and', faces_file)


def test_recognition_image(test_image: Path, names_file: Path = Path('data/names.pkl'), faces_file: Path = Path('data/faces_data.pkl'), threshold: float = 0.6) -> None:
    test_image = Path(test_image)
    if not test_image.exists():
        raise FileNotFoundError('Test image not found: ' + str(test_image))
    with open(names_file, 'rb') as f:
        names = pickle.load(f)
    with open(faces_file, 'rb') as f:
        encs = pickle.load(f)
    encs = [np.array(e) for e in encs]
    img = face_recognition.load_image_file(str(test_image))
    locs = face_recognition.face_locations(img)
    enc2 = face_recognition.face_encodings(img, locs)
    if not enc2:
        print('No face found in test image')
        return
    # compare first face
    enc = enc2[0]
    dists = face_recognition.face_distance(encs, enc)
    best_idx = int(np.argmin(dists))
    best_dist = float(dists[best_idx])
    if best_dist < threshold:
        print(f'MATCH: {names[best_idx]} (dist={best_dist:.3f})')
    else:
        print(f'No match (best: {names[best_idx]} dist={best_dist:.3f})')


def test_recognition_webcam(names_file: Path = Path('data/names.pkl'), faces_file: Path = Path('data/faces_data.pkl'), threshold: float = 0.6):
    with open(names_file, 'rb') as f:
        names = pickle.load(f)
    with open(faces_file, 'rb') as f:
        encs = pickle.load(f)
    encs = [np.array(e) for e in encs]
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError('Cannot open camera')
    print('Webcam test running; press q to quit')
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locs = face_recognition.face_locations(rgb)
        encs_frame = face_recognition.face_encodings(rgb, locs)
        for i, e in enumerate(encs_frame):
            dists = face_recognition.face_distance(encs, e)
            if len(dists) == 0:
                continue
            best_idx = int(np.argmin(dists))
            best_dist = float(dists[best_idx])
            top, right, bottom, left = locs[i]
            if best_dist < threshold:
                label = f'{names[best_idx]} ({best_dist:.2f})'
            else:
                label = f'Unknown ({best_dist:.2f})'
            cv2.rectangle(frame, (left, top), (right, bottom), (0,255,0), 2)
            cv2.putText(frame, label, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
        cv2.imshow('Webcam test', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--capture-name', type=str, help='Name of person to capture images for')
    p.add_argument('--capture-count', type=int, default=5, help='Number of captures to take')
    p.add_argument('--from-images', action='store_true', help='Generate pickles from data/images/ folder')
    p.add_argument('--test-image', type=str, help='Path to test image for recognition')
    p.add_argument('--webcam-test', action='store_true', help='Run a webcam recognition test (interactive)')
    p.add_argument('--threshold', type=float, default=0.6, help='Distance threshold for match')
    args = p.parse_args()

    try:
        if args.capture_name:
            capture_images(args.capture_name, args.capture_count)
        if args.from_images:
            generate_pickles_from_images()
        if args.test_image:
            test_recognition_image(Path(args.test_image), threshold=args.threshold)
        if args.webcam_test:
            test_recognition_webcam(threshold=args.threshold)
        if not any([args.capture_name, args.from_images, args.test_image, args.webcam_test]):
            p.print_help()
    except Exception as e:
        print('Error:', e)


if __name__ == '__main__':
    main()
