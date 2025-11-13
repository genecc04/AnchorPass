import bcrypt
from core import db
import os
import base64

MASTER_KEY = "master_password_hash"
SALT_KEY = "encryption_salt"


def master_exists():
    return db.get_setting(MASTER_KEY) is not None


def set_master(password: str):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12))
    db.set_setting(MASTER_KEY, hashed.decode())
    salt = db.get_setting(SALT_KEY)
    if not salt:
        salt = base64.urlsafe_b64encode(os.urandom(16)).decode()
        db.set_setting(SALT_KEY, salt)


def update_master_password_hash(password: str):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12))
    db.set_setting(MASTER_KEY, hashed.decode())


def verify_master(password: str) -> bool:
    stored_hash = db.get_setting(MASTER_KEY)
    if not stored_hash:
        return False
    return bcrypt.checkpw(password.encode(), stored_hash.encode())


def get_salt() -> str:
    salt = db.get_setting(SALT_KEY)
    if not salt:
        salt = base64.urlsafe_b64encode(os.urandom(16)).decode()
        db.set_setting(SALT_KEY, salt)
    return salt
