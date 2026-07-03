# -*- coding: utf-8 -*-
"""
Shared security utilities — password hashing and verification.
Uses bcrypt directly for secure password storage.
Legacy SHA-256 compatibility retained for existing user passwords.
"""
import hashlib
import bcrypt


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Returns a bcrypt hash string (e.g. $2b$12$...).
    """
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored hash.

    Supports both current bcrypt hashes and legacy SHA-256 (salt$hash) format.
    """
    if not hashed:
        return False

    # Legacy SHA-256 format: salt$sha256hex (salt is 32 hex chars)
    if not hashed.startswith("$2") and '$' in hashed:
        parts = hashed.split('$')
        if len(parts) == 2:
            salt, h = parts
            return hashlib.sha256((salt + plain).encode()).hexdigest() == h
        return False

    # Current bcrypt format
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except (ValueError, TypeError):
        return False


def needs_password_upgrade(hashed: str) -> bool:
    """Check if a password hash should be upgraded to bcrypt."""
    return not hashed.startswith("$2") and '$' in hashed
