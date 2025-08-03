from datetime import datetime, timedelta
from typing import Any, Union, Optional, Dict
from jose import jwt, JWTError
from passlib.context import CryptContext
import httpx
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
        subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode JWT token and return payload"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


async def verify_token_with_main_api(token: str) -> Optional[Dict[str, Any]]:
    """Verify token with main JobReadyNow API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.main_api_url}/auth/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=settings.main_api_timeout
            )

            if response.status_code == 200:
                user_data = response.json()
                logger.info(f"Token verified for user: {user_data.get('id')}")
                return user_data
            else:
                logger.warning(f"Token verification failed: {response.status_code}")
                return None

    except httpx.TimeoutException:
        logger.error("Main API timeout during token verification")
        return None
    except httpx.RequestError as e:
        logger.error(f"Main API request error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {e}")
        return None


def extract_user_id_from_token(token: str) -> Optional[str]:
    """Extract user ID from JWT token"""
    payload = decode_jwt_token(token)
    if payload:
        return payload.get("sub")
    return None


def validate_token_format(token: str) -> bool:
    """Validate JWT token format"""
    if not token:
        return False

    # JWT tokens have 3 parts separated by dots
    parts = token.split('.')
    return len(parts) == 3