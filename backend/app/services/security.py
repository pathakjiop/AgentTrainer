import hashlib
import secrets

API_KEY_PREFIX = "af_live_"

def generate_api_key() -> tuple[str, str, str]:
    """
    Returns (raw_key, key_hash, prefix)
    raw_key is shown only once to the user.
    """
    token = secrets.token_urlsafe(32)
    raw_key = f"{API_KEY_PREFIX}{token}"
    key_hash = hash_api_key(raw_key)
    prefix = raw_key[:12] + "..."
    return raw_key, key_hash, prefix

def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
