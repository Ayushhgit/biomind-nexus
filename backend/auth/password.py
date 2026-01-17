"""
BioMind Nexus - Password Hashing Utilities

Production-grade password hashing using bcrypt.
Work factor is configurable but defaults to 12 (industry standard).

Security:
- Never log or expose plaintext passwords
- bcrypt includes salt automatically
- Resistant to GPU/ASIC attacks
- Supports hash upgrades on login
"""

import bcrypt
from typing import Tuple


# Work factor for bcrypt (2^12 = 4096 iterations)
# Increase for higher security, decrease for faster tests
BCRYPT_WORK_FACTOR = 12


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plaintext password
        
    Returns:
        bcrypt hash string (includes salt)
        
    Example:
        >>> hashed = hash_password("SecureP@ss123")
        >>> hashed.startswith("$2b$")
        True
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=BCRYPT_WORK_FACTOR)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a bcrypt hash.
    
    Uses constant-time comparison to prevent timing attacks.
    
    Args:
        plain_password: Plaintext password to verify
        hashed_password: bcrypt hash to check against
        
    Returns:
        True if password matches, False otherwise
        
    Example:
        >>> hashed = hash_password("SecureP@ss123")
        >>> verify_password("SecureP@ss123", hashed)
        True
        >>> verify_password("WrongPassword", hashed)
        False
    """
    try:
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except (ValueError, TypeError):
        # Invalid hash format
        return False


def needs_rehash(hashed_password: str, target_work_factor: int = BCRYPT_WORK_FACTOR) -> bool:
    """
    Check if a password hash needs to be upgraded.
    
    Useful for migrating from weaker hash algorithms or
    increasing work factor over time.
    
    Args:
        hashed_password: Existing bcrypt hash
        target_work_factor: Desired work factor
        
    Returns:
        True if hash should be regenerated
        
    Example:
        # After increasing BCRYPT_WORK_FACTOR from 10 to 12:
        >>> needs_rehash(old_hash)  # Generated with factor 10
        True
    """
    try:
        # bcrypt hash format: $2b$XX$...
        # XX is the work factor in decimal
        prefix, work_factor_str, _ = hashed_password.split("$")[1:4]
        current_work_factor = int(work_factor_str)
        return current_work_factor < target_work_factor
    except (ValueError, IndexError):
        # Not a valid bcrypt hash, definitely needs rehash
        return True


def is_valid_bcrypt_hash(hash_string: str) -> bool:
    """
    Check if a string is a valid bcrypt hash format.
    
    Args:
        hash_string: String to validate
        
    Returns:
        True if valid bcrypt format
    """
    if not hash_string:
        return False
    
    # bcrypt hashes start with $2a$, $2b$, or $2y$
    valid_prefixes = ("$2a$", "$2b$", "$2y$")
    if not hash_string.startswith(valid_prefixes):
        return False
    
    # Standard bcrypt hash is 60 characters
    if len(hash_string) != 60:
        return False
    
    return True
