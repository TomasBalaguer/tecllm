"""
Security utilities for API key management.
API keys are stored with prefix (for lookup) and hash (for verification).
"""
import secrets
import hashlib
from typing import Tuple


# API Key format: sk_{prefix}_{secret}
# Example: sk_abc12345_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KEY_PREFIX_LIVE = "sk_"
PREFIX_LENGTH = 8
SECRET_LENGTH = 32


def generate_api_key() -> Tuple[str, str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple[full_key, prefix, hash]:
        - full_key: Complete key to show to user ONCE (sk_abc12345_xxxxx...)
        - prefix: First part for DB lookup (sk_abc12345)
        - hash: SHA-256 hash of full key for verification
    """
    prefix_random = secrets.token_urlsafe(PREFIX_LENGTH)[:PREFIX_LENGTH]
    secret = secrets.token_urlsafe(SECRET_LENGTH)[:SECRET_LENGTH]

    full_key = f"{KEY_PREFIX_LIVE}{prefix_random}_{secret}"
    key_prefix = f"{KEY_PREFIX_LIVE}{prefix_random}"
    key_hash = hash_api_key(full_key)

    return full_key, key_prefix, key_hash


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA-256.

    Args:
        api_key: The full API key

    Returns:
        SHA-256 hash of the key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(provided_key: str, stored_hash: str) -> bool:
    """
    Verify an API key against its stored hash.
    Uses constant-time comparison to prevent timing attacks.

    Args:
        provided_key: The API key provided in the request
        stored_hash: The hash stored in the database

    Returns:
        True if the key is valid, False otherwise
    """
    provided_hash = hash_api_key(provided_key)
    return secrets.compare_digest(provided_hash, stored_hash)


def extract_prefix(api_key: str) -> str | None:
    """
    Extract the prefix from an API key for database lookup.

    Args:
        api_key: The full API key (sk_abc12345_xxxxx...)

    Returns:
        The prefix (sk_abc12345) or None if invalid format
    """
    if not api_key or not api_key.startswith(KEY_PREFIX_LIVE):
        return None

    parts = api_key.split("_", 2)  # Split into at most 3 parts
    if len(parts) < 3:
        return None

    # Reconstruct prefix: sk_abc12345
    return f"{parts[0]}_{parts[1]}"


def validate_key_format(api_key: str) -> bool:
    """
    Validate the format of an API key.

    Args:
        api_key: The API key to validate

    Returns:
        True if format is valid, False otherwise
    """
    if not api_key:
        return False

    if not api_key.startswith(KEY_PREFIX_LIVE):
        return False

    parts = api_key.split("_", 2)
    if len(parts) != 3:
        return False

    # Check lengths
    prefix_part = parts[1]
    secret_part = parts[2]

    if len(prefix_part) != PREFIX_LENGTH:
        return False

    if len(secret_part) < SECRET_LENGTH // 2:  # Allow some flexibility
        return False

    return True
