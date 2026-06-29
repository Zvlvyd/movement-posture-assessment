# -*- coding: utf-8 -*-
"""
Shared security utilities — password hashing and verification.
Uses bcrypt via passlib for secure password storage.
Legacy SHA-256 compatibility retained for existing user passwords.
"""
import hashlib
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Characters that bcrypt $2b$ prefix wonʼt match, to help detect legacy hashes
_BCRYPT_PREFIX = "$2"


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Returns a bcrypt hash string (e.g. $2b$12$...).
    """
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored hash.

    Supports both current bcrypt hashes and legacy SHA-256 (salt$hash) format.
    """
    if not hashed:
        return False

    # Legacy SHA-256 format: salt$sha256hex (salt is 32 hex chars)
    if not hashed.startswith(_BCRYPT_PREFIX) and '$' in hashed:
        parts = hashed.split('$')
        if len(parts) == 2:
            salt, h = parts
            return hashlib.sha256((salt + plain).encode()).hexdigest() == h

    # Current bcrypt format
    return pwd_context.verify(plain, hashed)


def needs_password_upgrade(hashed: str) -> bool:
    """Check if a password hash should be upgraded to bcrypt."""
    return not hashed.startswith(_BCRYPT_PREFIX) and '$' in hashed
