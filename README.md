# FaceAuth — simple local face registration & login

This repository contains a minimal, local face-recognition flow implemented with Flask.
It lets a user register by capturing a webcam frame (saved locally) and then login by matching live frames against stored embeddings.

Contents included in this branch:

- `webapp.py` — Flask server providing `/` (UI), `/signup` and `/login` endpoints.
- `templates/index.html`, `templates/welcome.html` — UI pages (webcam UI, signup form, login flow).
- `requirements.txt` — minimal Python packages used.
- `tools/create_pickles_and_test.py` — helper to create pickles from images and test recognition (optional).
- `tests/headless_test.py` — headless test helper (optional).

Not included
- `data/images/` (image files) are ignored to avoid committing photos.
- `.env` (contains keys) is not included. Supabase-related files (e.g. `db_supabase.py`) are present in the repo but not used by the local Flask UI by default.

How this project stores data
- By default the Flask app stores registered user names in `data/names.pkl` and face embeddings in `data/faces_data.pkl`. Captured images are written to `data/images/<name>/`.
- The current local UI does NOT require any remote DB; Supabase helper code exists in the repo but is not used by the UI unless you wire it up and provide credentials.

Quick start (Windows / PowerShell)

1) Create / activate conda env and install dependencies (or use your existing env with dlib/face_recognition installed):

```powershell
conda create -n face-recognition-project python=3.8 -y
conda activate face-recognition-project
# install heavy libs via conda-forge if needed (dlib/face_recognition)
conda install -n face-recognition-project -c conda-forge dlib face_recognition opencv pillow cmake -y
pip install -r "C:\Users\uses\Downloads\face recognition\requirements.txt"
```

2) Run the app (foreground, so you can see logs):

```powershell
conda activate face-recognition-project
python -u "C:\Users\uses\Downloads\face recognition\webapp.py"
# Open http://127.0.0.1:5000 in your browser
```

3) Use the UI:
- Click "Sign Up" → enter a name → click Register (the UI will start the camera and capture frames).
- Click "Login (5s)" → the UI will capture frames for up to 5s and redirect to a welcome page on success.

Security notes
- This is a demo/local prototype. Do not expose it publicly without adding authentication, HTTPS, and anti-spoofing/liveness checks.

If you want me to push the code to your GitHub repo or adjust which files are included, tell me and I will push to a branch (default: `feature/faceauth`).
# Face Recognition Attendance System with Supabase# face_recognition_project

## Overview

This is a face recognition attendance system that uses dlib/face_recognition for embeddings (128-d vectors) and Supabase as the backend database instead of Firebase.

## Face Recognition Model Used

- **Model**: dlib's ResNet-based face recognition model
- **Embedding**: 128-dimensional face encodings
- **Detection**: HOG (Histogram of Oriented Gradients) by default
- **Matching**: Euclidean distance between embeddings

## Prerequisites

- Python 3.8+
- Conda environment (recommended for dlib on Windows)
- Supabase account and project

## Installation

### 1. Create Conda Environment

```bash
conda create -n face-recognition python=3.8 -y
conda activate face-recognition
```

### 2. Install Dependencies

```bash
# Install face recognition stack (Windows)
conda install -c conda-forge dlib face_recognition opencv numpy -y

# Install other dependencies
pip install supabase python-dotenv cvzone pillow
```

### 3. Supabase Setup

#### Create Tables in Supabase SQL Editor:

```sql
-- Users table
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  major TEXT,
  starting_year INTEGER,
  total_attendance INTEGER DEFAULT 0,
  standing TEXT,
  year INTEGER,
  last_attendance_time TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Embeddings table
CREATE TABLE embeddings (
  id SERIAL PRIMARY KEY,
  user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
  embedding JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Attendance log table
CREATE TABLE attendance_log (
  id SERIAL PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  timestamp TIMESTAMP DEFAULT NOW(),
  method TEXT,
  confidence REAL
);

-- Create indexes
CREATE INDEX idx_embeddings_user_id ON embeddings(user_id);
CREATE INDEX idx_attendance_user_id ON attendance_log(user_id);
CREATE INDEX idx_attendance_timestamp ON attendance_log(timestamp);
```

#### Create Storage Bucket:

1. Go to Supabase Dashboard → Storage
2. Create a new bucket named `images`
3. Make it public or configure policies as needed

### 4. Configure Environment

Create `.env` file:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key
```

## Project Structure

```
face recognition/
├── .env                    # Supabase credentials
├── db_supabase.py         # Supabase helper functions
├── AddDataToDatabase.py   # Add sample users
├── EncodeGenerator.py     # Generate embeddings
├── Main.py                # Face recognition system
├── Images/                # User images (userid.png)
├── Resources/             # UI resources (optional)
│   ├── background.png
│   └── Modes/
└── README.md
```

## Usage

### Step 1: Add Users to Database

```bash
python AddDataToDatabase.py
```

### Step 2: Add User Images

- Create `Images/` folder
- Add user photos named as `<user_id>.png`
- Example: `321654.png`, `852741.png`

### Step 3: Generate Embeddings

```bash
python EncodeGenerator.py
```

### Step 4: Run Face Recognition

```bash
python Main.py
```

Press 'q' to quit.

## Code Files

All code files are provided in the sections below. Copy each section into the respective file.

---

## Comparison: Firebase vs Supabase

### What Changed:

1. **Database**: Firebase Realtime Database → Supabase Postgres
2. **Storage**: Firebase Storage → Supabase Storage
3. **Authentication**: firebase-admin SDK → supabase-py client
4. **Data Format**: Embeddings stored as JSONB arrays in Postgres

### What Stayed The Same:

- Face recognition model (dlib 128-d embeddings)
- Detection and matching logic
- UI and display flow
- Attendance tracking logic

### Model Details:

The Firebase code you shared uses `face_recognition.face_encodings()` which:

- Uses dlib's pretrained ResNet model
- Produces 128-dimensional embeddings
- Compares faces using Euclidean distance
- Threshold typically 0.6 (closer to 0 = better match)

This is the industry-standard approach and is what we're keeping in the Supabase version.

## Next Steps

1. **Test locally** with SQLite first (optional):
   - I can provide SQLite version if you want offline-first testing
2. **Mobile integration**:

   - Convert embeddings computation to TFLite
   - Use Supabase client on mobile (React Native, Flutter, etc.)

3. **Add liveness detection** for spoofing prevention

4. **Accessibility features** for elderly users:
   - Voice prompts
   - Large UI elements
   - Caregiver notifications

## Troubleshooting

### "No module named 'dlib'"

- Use conda: `conda install -c conda-forge dlib`

### "SUPABASE_URL not found"

- Check .env file exists and is in the same directory
- Verify .env format (no quotes needed)

### "No encodings found"

- Run `EncodeGenerator.py` first
- Check that Images/ folder has .png files
- Verify face is clearly visible in images

### "User not found in database"

- Run `AddDataToDatabase.py` first
- Or manually add users via Supabase dashboard

## Support

For issues:

1. Check Supabase dashboard logs
2. Verify table structure matches SQL above
3. Test connection: `python db_supabase.py`

## License

Educational/Personal Use
