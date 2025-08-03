from datetime import datetime, timedelta
from typing import Any, Union, Optional, Dict
from jose import jwt, JWTError
from passlib.context import CryptContext
import httpx
import logging
import asyncio
from functools import lru_cache

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
    try:
        encoded_jwt = jwt.encode(
            to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Hash password"""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Password hashing error: {e}")
        raise


def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode JWT token and return payload"""
    try:
        # Validate token format first
        if not validate_token_format(token):
            logger.warning("Invalid token format provided")
            return None

        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        # Validate required fields
        if not payload.get("sub"):
            logger.warning("JWT token missing subject field")
            return None

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            logger.warning("JWT token has expired")
            return None

        return payload

    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error decoding JWT: {e}")
        return None


async def verify_token_with_main_api(token: str) -> Optional[Dict[str, Any]]:
    """Verify token with main JobReadyNow API"""
    if not token or not validate_token_format(token):
        logger.warning("Invalid token provided to main API verification")
        return None

    try:
        timeout = httpx.Timeout(settings.main_api_timeout)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                f"{settings.main_api_url}/auth/me",
                headers={"Authorization": f"Bearer {token}"},
                follow_redirects=True
            )

            if response.status_code == 200:
                user_data = response.json()

                # Validate response data
                if not user_data.get('id'):
                    logger.warning("Main API returned user data without ID")
                    return None

                logger.info(f"Token verified for user: {user_data.get('id')}")
                return user_data

            elif response.status_code == 401:
                logger.warning("Token rejected by main API (401)")
                return None
            elif response.status_code == 403:
                logger.warning("Token forbidden by main API (403)")
                return None
            else:
                logger.warning(f"Main API returned unexpected status: {response.status_code}")
                return None

    except httpx.TimeoutException:
        logger.error("Main API timeout during token verification")
        return None
    except httpx.ConnectError:
        logger.error("Cannot connect to main API for token verification")
        return None
    except httpx.RequestError as e:
        logger.error(f"Main API request error: {e}")
        return None
    except ValueError as e:
        logger.error(f"Invalid JSON response from main API: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during main API verification: {e}")
        return None


def extract_user_id_from_token(token: str) -> Optional[str]:
    """Extract user ID from JWT token"""
    try:
        payload = decode_jwt_token(token)
        if payload:
            return payload.get("sub")
        return None
    except Exception as e:
        logger.error(f"Error extracting user ID from token: {e}")
        return None


def validate_token_format(token: str) -> bool:
    """Validate JWT token format"""
    if not token:
        return False

    if not isinstance(token, str):
        return False

    # JWT tokens have 3 parts separated by dots
    parts = token.split('.')
    if len(parts) != 3:
        return False

    # Each part should be base64 encoded (basic check)
    for part in parts:
        if not part or len(part) < 1:
            return False

    return True


@lru_cache(maxsize=1000)
def validate_token_signature(token: str) -> bool:
    """Validate JWT token signature (cached)"""
    try:
        jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False}  # Just check signature
        )
        return True
    except JWTError:
        return False
    except Exception as e:
        logger.error(f"Token signature validation error: {e}")
        return False


def sanitize_auth_header(auth_header: str) -> Optional[str]:
    """Sanitize and extract token from authorization header"""
    if not auth_header:
        return None

    # Remove 'Bearer ' prefix if present
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]  # Remove 'Bearer ' (7 characters)
    else:
        token = auth_header

    # Basic sanitization
    token = token.strip()

    # Validate format
    if validate_token_format(token):
        return token

    return None


def generate_secure_token(length: int = 32) -> str:
    """Generate a secure random token"""
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_sensitive_data(data: str) -> str:
    """Hash sensitive data for logging/storage"""
    import hashlib

    return hashlib.sha256(data.encode()).hexdigest()[:16]  # First 16 chars for logging