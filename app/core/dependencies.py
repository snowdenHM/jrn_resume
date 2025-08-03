from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging
import uuid
import asyncio
import time
from functools import lru_cache
from collections import defaultdict
import threading

from app.core.config import settings
from app.core.security import decode_jwt_token, verify_token_with_main_api, validate_token_format
from app.database.connection import get_db

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)

# Cache for user data to reduce API calls
_user_cache = {}
_cache_ttl = 300  # 5 minutes
_cache_lock = threading.Lock()

# Rate limiting storage
_rate_limit_storage = defaultdict(list)
_rate_limit_lock = threading.Lock()


async def get_current_user(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    Get current user from JWT token.
    First tries local JWT decode, then falls back to main API verification.
    """
    # Check if credentials are provided
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Validate token format
    if not validate_token_format(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Check cache first
        with _cache_lock:
            cached_user = _user_cache.get(token)
            if cached_user and cached_user.get('expires_at', 0) > time.time():
                logger.debug("Retrieved user from cache")
                return cached_user['user_data']

        # First try to decode JWT locally for performance
        user_data = None
        payload = decode_jwt_token(token)

        if payload:
            user_id = payload.get("sub")
            email = payload.get("email")

            if user_id and email:
                logger.info(f"User authenticated locally: {user_id}")
                user_data = {
                    "id": user_id,
                    "email": email,
                    "token": token
                }
            else:
                logger.warning("Local JWT decode missing required fields")

        # If local decode fails or incomplete, verify with main API
        if not user_data:
            logger.info("Local JWT decode failed, verifying with main API")
            try:
                api_user_data = await verify_token_with_main_api(token)

                if api_user_data:
                    user_data = {
                        "id": str(api_user_data.get("id")),
                        "email": api_user_data.get("email"),
                        "first_name": api_user_data.get("first_name"),
                        "last_name": api_user_data.get("last_name"),
                        "is_active": api_user_data.get("is_active", True),
                        "token": token
                    }
                    logger.info(f"User authenticated via main API: {user_data['id']}")
                else:
                    logger.warning("Main API verification failed")

            except Exception as api_error:
                logger.error(f"Main API verification error: {api_error}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication service unavailable",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # If both methods fail, raise unauthorized
        if not user_data:
            logger.warning("Both local and API authentication failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Cache successful authentication
        with _cache_lock:
            _user_cache[token] = {
                'user_data': user_data,
                'expires_at': time.time() + _cache_ttl
            }

        return user_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
        current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Ensure user is active"""
    if not current_user.get("is_active", True):
        logger.warning(f"Inactive user attempted access: {current_user.get('id')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    return current_user


def verify_user_owns_resource(resource_user_id: str, current_user_id: str) -> bool:
    """Verify that the current user owns the resource"""
    try:
        # Handle both string UUIDs and UUID objects
        if isinstance(resource_user_id, uuid.UUID):
            resource_uuid = resource_user_id
        else:
            resource_uuid = uuid.UUID(str(resource_user_id))

        if isinstance(current_user_id, uuid.UUID):
            current_uuid = current_user_id
        else:
            current_uuid = uuid.UUID(str(current_user_id))

        return resource_uuid == current_uuid
    except (ValueError, TypeError) as e:
        logger.error(f"UUID validation error: {e}")
        return False


def get_user_id_from_token(
        current_user: Dict[str, Any] = Depends(get_current_user)
) -> str:
    """Extract user ID from current user"""
    return current_user["id"]


class RateLimitChecker:
    """Rate limiting dependency with in-memory backend"""

    def __init__(self, requests: int = 100, window: int = 60):
        self.requests = requests
        self.window = window

    async def __call__(self, request: Request):
        """Check rate limit for request"""
        try:
            # Get client IP
            client_ip = request.client.host if request.client else "unknown"
            current_time = time.time()

            with _rate_limit_lock:
                # Clean old entries
                cutoff_time = current_time - self.window
                _rate_limit_storage[client_ip] = [
                    timestamp for timestamp in _rate_limit_storage[client_ip]
                    if timestamp > cutoff_time
                ]

                # Check rate limit
                if len(_rate_limit_storage[client_ip]) >= self.requests:
                    logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded"
                    )

                # Add current request
                _rate_limit_storage[client_ip].append(current_time)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Don't block on rate limiting errors in development
            if settings.environment == "production":
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit service unavailable"
                )


# Common rate limiters
rate_limit_standard = RateLimitChecker(
    requests=settings.rate_limit_requests,
    window=settings.rate_limit_window
)

rate_limit_strict = RateLimitChecker(requests=20, window=60)
rate_limit_ats_analysis = RateLimitChecker(requests=10, window=300)  # 10 per 5 minutes


# Optional authentication (for public endpoints that benefit from auth)
async def get_current_user_optional(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """Get current user if token is provided, otherwise return None"""
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException as e:
        # Log the error but don't raise it for optional auth
        logger.debug(f"Optional authentication failed: {e.detail}")
        return None
    except Exception as e:
        logger.error(f"Optional authentication error: {e}")
        return None


# Clean up expired cache entries periodically
async def cleanup_user_cache():
    """Clean up expired cache entries"""
    current_time = time.time()
    with _cache_lock:
        expired_tokens = [
            token for token, data in _user_cache.items()
            if data.get('expires_at', 0) <= current_time
        ]

        for token in expired_tokens:
            del _user_cache[token]

    logger.debug(f"Cleaned up {len(expired_tokens)} expired cache entries")


# Cleanup rate limit storage periodically
async def cleanup_rate_limit_storage():
    """Clean up old rate limit entries"""
    current_time = time.time()
    with _rate_limit_lock:
        for ip in list(_rate_limit_storage.keys()):
            cutoff_time = current_time - 3600  # Keep 1 hour of history
            _rate_limit_storage[ip] = [
                timestamp for timestamp in _rate_limit_storage[ip]
                if timestamp > cutoff_time
            ]
            # Remove empty entries
            if not _rate_limit_storage[ip]:
                del _rate_limit_storage[ip]