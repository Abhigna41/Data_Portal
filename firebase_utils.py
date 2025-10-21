import os
from firebase_admin import storage

FIREBASE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET", "")


def get_bucket():
    """Return the active firebase storage bucket.

    If FIREBASE_STORAGE_BUCKET env var is set, use that. Otherwise the default
    bucket configured on the initialized firebase app will be returned.
    """
    if FIREBASE_BUCKET:
        return storage.bucket(FIREBASE_BUCKET)
    return storage.bucket()


def upload_bytes(path_in_bucket: str, data: bytes, content_type: str = "application/octet-stream"):
    """Upload bytes to the given path in the storage bucket."""
    bucket = get_bucket()
    blob = bucket.blob(path_in_bucket)
    blob.upload_from_string(data, content_type=content_type)
    return blob.public_url


def download_bytes(path_in_bucket: str) -> bytes:
    """Download object bytes from storage bucket."""
    bucket = get_bucket()
    blob = bucket.blob(path_in_bucket)
    return blob.download_as_bytes()
