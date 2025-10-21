import os
from dotenv import load_dotenv
import json
import firebase_admin
from firebase_admin import credentials, storage

# --- Load environment variables ---
load_dotenv()  # For local .env file. Render uses its own env vars.

# --- Database Configuration ---
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DB", "")
}

# --- Flask Secret & Admin Credentials ---
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "default_secret_key")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# --- Firebase Configuration ---
# 1️⃣ Local file option (for testing)
firebase_key_path = os.getenv("FIREBASE_KEY_PATH")
if firebase_key_path and os.path.exists(firebase_key_path):
    cred = credentials.Certificate(firebase_key_path)
else:
    # 2️⃣ JSON string from environment variable (for Render deployment)
    firebase_key_json = os.getenv("FIREBASE_KEY_JSON")
    if not firebase_key_json:
        raise ValueError("Firebase key not provided. Set FIREBASE_KEY_JSON in environment.")
    cred_dict = json.loads(firebase_key_json)
    cred = credentials.Certificate(cred_dict)

# Initialize Firebase Admin with storage bucket
bucket_name = os.getenv("FIREBASE_BUCKET", "dataportal-6d718.appspot.com")
firebase_admin.initialize_app(cred, {
    'storageBucket': bucket_name
})

# Get storage bucket reference
bucket = storage.bucket()

# Optional: print to verify correct setup (remove in production)
print(f"[CONFIG] Firebase bucket set to: {bucket_name}")
