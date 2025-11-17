from __future__ import annotations
import base64
from typing import Union
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet

_TAG_PREFIX = "v1:"

def looks_tagged(token: str) -> bool:
    return isinstance(token, str) and token.startswith(_TAG_PREFIX)

def strip_tag(token: str) -> str:
    if not isinstance(token, str):
        return ""
    return token[len(_TAG_PREFIX):] if looks_tagged(token) else token

def tag_token(token: str) -> str:
    if not token:
        return ""
    return token if looks_tagged(token) else f"{_TAG_PREFIX}{token}"

_PBKDF2_ITERATIONS = 390_000

def derive_key(password: str, salt: bytes) -> bytes:
    if not isinstance(salt, (bytes, bytearray)):
        raise TypeError("salt must be bytes")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=bytes(salt),
        iterations=_PBKDF2_ITERATIONS,
        backend=default_backend(),
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))

def make_cipher(password: str, salt: Union[str, bytes]) -> Fernet:
    if isinstance(salt, str):
        try:
            salt_bytes = base64.urlsafe_b64decode(salt.encode("utf-8"))
        except Exception:
            salt_bytes = salt.encode("utf-8")
    else:
        salt_bytes = bytes(salt)
    key = derive_key(password, salt_bytes)
    return Fernet(key)

def encrypt_text(cipher: Fernet, plaintext: Union[str, bytes, None]) -> str:
    if plaintext is None:
        plaintext = ""
    if isinstance(plaintext, bytes):
        pt = plaintext
    else:
        pt = str(plaintext).encode("utf-8")
    try:
        token = cipher.encrypt(pt)
        return token.decode("utf-8")
    except Exception:
        return ""

def decrypt_text(cipher: Fernet, ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        return cipher.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except Exception:
        return "[Decryption failed]"

def decrypt_any(cipher: Fernet, token: str) -> str:
    if not token:
        return ""
    raw = strip_tag(token)
    pt = decrypt_text(cipher, raw)
    return "" if pt == "[Decryption failed]" else pt

#Legacy support for versions before alpha release
DEFAULT_SALT = b"secure-password-manager"

def derive_cipher_from_password(password: str) -> Fernet:
    return make_cipher(password, DEFAULT_SALT)

def encrypt_value(value: str, cipher: Fernet) -> str:
    return encrypt_text(cipher, value)

def decrypt_value(value: str, cipher: Fernet) -> str:
    return decrypt_any(cipher, value)
