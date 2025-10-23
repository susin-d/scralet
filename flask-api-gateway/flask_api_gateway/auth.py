from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from flask import request
from werkzeug.exceptions import HTTPException

from .config import config

# Password hashing - use pbkdf2_sha256 as it's more compatible
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# JWT Configuration
SECRET_KEY = config.jwt_secret_key
ALGORITHM = config.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = config.jwt_access_token_expire_minutes

# Blacklisted tokens (for logout)
blacklisted_tokens: set = set()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    # Truncate password to 72 bytes for bcrypt compatibility
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password = password_bytes[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None or token in blacklisted_tokens:
            return None
        return username
    except JWTError:
        return None


def blacklist_token(token: str):
    """Add a token to the blacklist."""
    blacklisted_tokens.add(token)


def get_current_admin_user() -> Dict[str, Any]:
    """Get the current authenticated admin user from JWT token."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(401, description="Invalid authentication credentials")

    token = auth_header.split(' ')[1]
    username = verify_token(token)
    if username is None:
        raise HTTPException(401, description="Invalid authentication credentials")

    from .main import admin_users  # Import here to avoid circular import
    user = admin_users.get(username)
    if user is None or not user.get("is_active"):
        raise HTTPException(401, description="Invalid authentication credentials")

    return user


def require_auth(func):
    """Decorator to require authentication for a route."""
    def wrapper(*args, **kwargs):
        get_current_admin_user()  # This will raise an exception if not authenticated
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper