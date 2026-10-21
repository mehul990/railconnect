import bcrypt
import secrets
import string
import hashlib
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from typing import Optional, Dict, Any
from app.config import settings


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token with JTI and expiration."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    jti = secrets.token_hex(16)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": jti
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def get_token_identifier(token: str) -> str:
    """Return a unique deterministic SHA256 identifier for a token to store in revocation blocklist."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_pnr() -> str:
    """Generate a unique 10-character Indian Railway style PNR (e.g., RC49103829)."""
    digits = "".join(secrets.choice(string.digits) for _ in range(8))
    return f"RC{digits}"


def generate_reset_token() -> str:
    """Generate a high-entropy URL-safe token for password reset."""
    return secrets.token_urlsafe(32)
