import os
from dotenv import load_dotenv
from firebase_admin import credentials

# Load environment variables
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DB", "")
}

SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "default_secret_key")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "firebase-key.json")
cred = credentials.Certificate(FIREBASE_KEY_PATH)
