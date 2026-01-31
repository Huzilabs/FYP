# Setup Guide - Face Recognition App

## Current Status
✅ Supabase credentials configured
✅ Flask backend running with CORS
✅ Next.js frontend running
⚠️ Database tables need to be created
⚠️ face_recognition library missing

## Step 1: Create Database Tables

1. Go to your Supabase Dashboard: https://supabase.com/dashboard
2. Select your project: `gnftheueosouyceptdsb`
3. Click on "SQL Editor" in the left sidebar
4. Click "New Query"
5. Copy ALL content from `supabase_setup.sql` and paste it
6. Click "Run" to execute

This will create:
- `users` table
- `user_images` table  
- `embeddings` table with pgvector extension
- `find_nearest_embeddings()` function for face matching
- Row Level Security policies

## Step 2: Create Storage Bucket

1. In Supabase Dashboard, click "Storage" in left sidebar
2. Click "Create a new bucket"
3. Name: `face_oftheusers` (must match .env SUPABASE_BUCKET)
4. Make it **Private** (not public)
5. Click "Create bucket"

## Step 3: Install face_recognition Library

The `face_recognition` library requires:
- Visual Studio Build Tools
- CMake
- dlib (C++ library)

### Option A: Install Requirements (Recommended for Production)

1. Install Visual Studio 2022 Build Tools:
   - Download from: https://visualstudio.microsoft.com/downloads/
   - Select "Desktop development with C++"
   - Install (may take 30+ minutes)

2. Install face_recognition:
   ```powershell
   cd E:\fyp\FYP
   .\.venv\Scripts\python.exe -m pip install face_recognition
   ```

3. Restart Flask server

### Option B: Use OpenCV Alternative (Quick Start)

If you want to test without face_recognition:
- The app will work for registration (storing images)
- Face recognition login will not work yet
- You can implement OpenCV-based face detection as alternative

## Step 4: Test All Endpoints

Once database is set up, test these endpoints:

1. **Registration** (`POST /api/register`)
   - Go to: http://localhost:3000/register
   - Fill form + capture face
   - Should create user in database

2. **Login** (`POST /api/login_face`)
   - Go to: http://localhost:3000/login  
   - Capture face
   - Requires face_recognition library

3. **User Management**
   - `GET /api/users/<user_id>` - Get user details
   - `PUT /api/users/<user_id>` - Update user
   - `DELETE /api/users/<user_id>` - Delete user

4. **Face Detection** (`POST /api/detect_face`)
   - Detects faces in image
   - Requires face_recognition library

## Available Endpoints Summary

```
POST   /api/detect_face       - Detect faces in image
POST   /api/upload_face_temp  - Upload temporary face image
POST   /api/capture_face      - Capture and store face image
POST   /api/register          - Register new user with face
POST   /api/attach_image      - Attach image to existing user
POST   /api/login_face        - Login using face recognition
GET    /api/users/<id>        - Get user details
PUT    /api/users/<id>        - Update user
DELETE /api/users/<id>        - Delete user
DELETE /api/user_images/<id>  - Delete user image
GET    /api/admin/embeddings  - View embeddings (debug)
```

## Troubleshooting

### "Failed to fetch" error
- ✅ CORS is now enabled
- ✅ Supabase credentials configured
- Check: Database tables created?
- Check: Storage bucket created?

### "face_recognition import failed"
- Install Visual Studio Build Tools + face_recognition
- OR wait for OpenCV alternative implementation

### "could not translate host name"
- ✅ Fixed - Real Supabase URL now in .env
- Restart Flask if still seeing this error

## Next Steps

1. Run the SQL script in Supabase SQL Editor
2. Create the storage bucket
3. Try registration at http://localhost:3000/register
4. If you need face login, install face_recognition library

