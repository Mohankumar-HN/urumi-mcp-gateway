import hashlib
import secrets

def generate_api_key() -> str:
    """Generate a secure API key."""
    return "urumi_" + secrets.token_urlsafe(32)

def hash_api_key(api_key: str) -> str:
    """Hash an API key before storing it in the database."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()