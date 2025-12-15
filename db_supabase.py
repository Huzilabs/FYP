import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import numpy as np
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==================== USER MANAGEMENT ====================

def add_user(user_id: str, name: str, major: str, starting_year: int, 
             standing: str, year: int) -> Dict:
    """Add a new user to the database"""
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
    """Get user information by ID"""
    response = supabase.table("users").select("*").eq("id", user_id).execute()
    return response.data[0] if response.data else None

def update_attendance(user_id: str) -> bool:
    """Update user's attendance count and last attendance time"""
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

# ==================== EMBEDDINGS MANAGEMENT ====================

def save_embedding(user_id: str, embedding: np.ndarray) -> bool:
    """Save face embedding for a user (stored as serialized blob in JSON)"""
    # Convert numpy array to list for JSON storage
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
    """Get all embeddings from database. Returns list of (user_id, embedding_array)"""
    response = supabase.table("embeddings").select("user_id, embedding").execute()
    
    embeddings = []
    for row in response.data:
        user_id = row["user_id"]
        # Convert list back to numpy array
        embedding = np.array(row["embedding"], dtype=np.float64)
        embeddings.append((user_id, embedding))
    
    return embeddings

def load_embeddings_for_recognition() -> Tuple[List[np.ndarray], List[str]]:
    """Load embeddings in format needed for face_recognition matching"""
    all_embeddings = get_all_embeddings()
    
    encode_list = []
    user_ids = []
    
    for user_id, embedding in all_embeddings:
        encode_list.append(embedding)
        user_ids.append(user_id)
    
    return encode_list, user_ids

# ==================== IMAGE STORAGE ====================

def upload_user_image(user_id: str, image_path: str) -> Optional[str]:
    """Upload user image to Supabase storage"""
    try:
        with open(image_path, 'rb') as f:
            file_data = f.read()
        
        # Upload to storage bucket
        file_name = f"users/{user_id}.png"
        response = supabase.storage.from_("images").upload(
            file_name, 
            file_data,
            file_options={"content-type": "image/png", "upsert": "true"}
        )
        
        # Get public URL
        public_url = supabase.storage.from_("images").get_public_url(file_name)
        return public_url
    except Exception as e:
        print(f"Error uploading image: {e}")
        return None

def download_user_image(user_id: str) -> Optional[bytes]:
    """Download user image from Supabase storage"""
    try:
        file_name = f"users/{user_id}.png"
        response = supabase.storage.from_("images").download(file_name)
        return response
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

# ==================== ATTENDANCE LOGGING ====================

def log_attendance(user_id: str, method: str = "face", confidence: float = None) -> bool:
    """Log an attendance entry"""
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

# ==================== UTILITY FUNCTIONS ====================

def check_recent_attendance(user_id: str, min_seconds: int = 30) -> bool:
    """Check if user has marked attendance recently (within min_seconds)"""
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
    """Get all users from database"""
    response = supabase.table("users").select("*").execute()
    return response.data if response.data else []

if __name__ == "__main__":
    # Test connection
    print("Testing Supabase connection...")
    try:
        users = get_all_users()
        print(f"✓ Connected successfully! Found {len(users)} users.")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
