import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "0000"),
    "database": os.getenv("MYSQL_DB", "data_portal")
}

SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "default_secret_key")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "brahma")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ragham11")
