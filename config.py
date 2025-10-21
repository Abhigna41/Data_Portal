import os
import json
import firebase_admin
from firebase_admin import credentials, storage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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

# --- Firebase Configuration (Use only JSON string, no file) ---
firebase_key_json = os.getenv("FIREBASE_KEY_JSON")
if not firebase_key_json:
    raise ValueError("Firebase key not provided. Set FIREBASE_KEY_JSON in environment.")

cred_dict = json.loads(firebase_key_json)
cred = credentials.Certificate(cred_dict)

bucket_name = os.getenv("FIREBASE_BUCKET", "dataportal-6d718.appspot.com")
firebase_admin.initialize_app(cred, {
    'storageBucket': bucket_name
})

# Firebase storage bucket reference
bucket = storage.bucket()
