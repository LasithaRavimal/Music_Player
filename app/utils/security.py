from datetime import datetime, timedelta
from typing import Optional
import warnings
import logging

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# Suppress bcrypt warning
warnings.filterwarnings("ignore", message=".*bcrypt.*")
logging.getLogger("passlib").setLevel(logging.ERROR)

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =====================================
# PASSWORD VERIFICATION
# =====================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


# =====================================
# PASSWORD HASHING
# =====================================
def get_password_hash(password: str) -> str:
    """Generate hashed password"""
    return pwd_context.hash(password)


# =====================================
# CREATE JWT TOKEN
# =====================================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create JWT access token for authenticated user
    """

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


# =====================================
# DECODE JWT TOKEN
# =====================================
def decode_access_token(token: str):
    """
    Decode and validate JWT token
    """

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload

    except JWTError:
        return None