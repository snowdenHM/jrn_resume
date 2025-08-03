from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging
import uuid

from app.core.config import settings
from app.core.security import decode_jwt_token, verify_token_with_main_api, validate_token_format
from app.database.connection import get_db

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


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
        # First try to decode JWT locally for performance
        payload = decode_jwt_token(token)

        if payload:
            user_id = payload.get("sub")
            email = payload.get("email")

            if user_id:
                logger.info(f"User authenticated locally: {user_id}")
                return {
                    "id": user_id,
                    "email": email,
                    "token": token
                }

        # If local decode fails or user_id is missing, verify with main API
        logger.info("Local JWT decode failed, verifying with main API")
        user_data = await verify_token_with_main_api(token)

        if user_data:
            return {
                "id": str(user_data.get("id")),
                "email": user_data.get("email"),
                "first_name": user_data.get("first_name"),
                "last_name": user_data.get("last_name"),
                "is_active": user_data.get("is_active", True),
                "token": token
            }

        # If both methods fail, raise unauthorized
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    return current_user


def verify_user_owns_resource(resource_user_id: str, current_user_id: str) -> bool:
    """Verify that the current user owns the resource"""
    try:
        # Convert to UUID for proper comparison
        resource_uuid = uuid.UUID(resource_user_id)
        current_uuid = uuid.UUID(current_user_id)
        return resource_uuid == current_uuid
    except (ValueError, TypeError):
        return False


async def get_db_session() -> Session:
    """Get database session dependency"""
    return get_db()


def get_user_id_from_token(
        current_user: Dict[str, Any] = Depends(get_current_user)
) -> str:
    """Extract user ID from current user"""
    return current_user["id"]


class RateLimitChecker:
    """Rate limiting dependency"""

    def __init__(self, requests: int = 100, window: int = 60):
        self.requests = requests
        self.window = window

    async def __call__(self, request: Request):
        # Implementation would use Redis or in-memory cache
        # For now, just pass through
        pass


# Common rate limiters
rate_limit_standard = RateLimitChecker(
    requests=settings.rate_limit_requests,
    window=settings.rate_limit_window
)

rate_limit_strict = RateLimitChecker(requests=20, window=60)


# Optional authentication (for public endpoints that benefit from auth)
async def get_current_user_optional(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """Get current user if token is provided, otherwise return None"""
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None