"""Hashing de contrasenas con PBKDF2-HMAC-SHA256 (solo stdlib, sin dependencias)."""
from __future__ import annotations

import hashlib
import hmac
import os

_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    """Devuelve el hash en formato 'salt_hex:digest_hex'."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Compara en tiempo constante una contrasena contra el hash almacenado."""
    try:
        salt_hex, digest_hex = stored.split(":", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt_hex), _ITERATIONS
    )
    return hmac.compare_digest(digest.hex(), digest_hex)
