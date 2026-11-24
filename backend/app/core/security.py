from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from pwdlib import PasswordHash
from app.core.config import settings
password_hash = PasswordHash.recommended()
def hash_password(value: str) -> str: return password_hash.hash(value)
def verify_password(value: str, hashed: str) -> bool: return password_hash.verify(value, hashed)
def create_access_token(subject: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": subject, "exp": expires}, settings.jwt_secret, algorithm="HS256")
def decode_token(token: str) -> str:
    try:
        subject = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"]).get("sub")
        if not subject: raise ValueError
        return subject
    except (JWTError, ValueError) as exc: raise ValueError("Invalid token") from exc
