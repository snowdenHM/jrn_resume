from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List, Optional, Any, Dict
from datetime import datetime

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema"""
    items: List[T]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    size: int = Field(..., ge=1, description="Items per page")
    pages: int = Field(..., ge=1, description="Total number of pages")
    has_next: bool = Field(False, description="Whether there's a next page")
    has_prev: bool = Field(False, description="Whether there's a previous page")

    @classmethod
    def create(
            cls,
            items: List[T],
            total: int,
            page: int,
            size: int
    ) -> "PaginatedResponse[T]":
        """Create paginated response"""
        pages = (total + size - 1) // size if total > 0 else 1
        has_next = page < pages
        has_prev = page > 1

        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
            has_next=has_next,
            has_prev=has_prev
        )


class BaseResponse(BaseModel):
    """Base response schema"""
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SuccessResponse(BaseResponse):
    """Success response schema"""
    data: Optional[Any] = None


class ErrorResponse(BaseResponse):
    """Error response schema"""
    success: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class HealthCheckResponse(BaseModel):
    """Health check response schema"""
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    checks: Optional[Dict[str, Any]] = Field(None, description="Detailed health checks")


class ExportResponse(BaseModel):
    """Export response schema"""
    export_id: str = Field(..., description="Export job ID")
    status: str = Field(..., description="Export status")
    download_url: Optional[str] = Field(None, description="Download URL when ready")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Download URL expiration")


class ValidationErrorDetail(BaseModel):
    """Validation error detail schema"""
    field: str = Field(..., description="Field name with error")
    message: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")


class ValidationErrorResponse(ErrorResponse):
    """Validation error response schema"""
    error_code: str = "VALIDATION_ERROR"
    validation_errors: List[ValidationErrorDetail] = []


class NotFoundResponse(ErrorResponse):
    """Not found error response schema"""
    error_code: str = "RESOURCE_NOT_FOUND"


class UnauthorizedResponse(ErrorResponse):
    """Unauthorized error response schema"""
    error_code: str = "UNAUTHORIZED"


class ForbiddenResponse(ErrorResponse):
    """Forbidden error response schema"""
    error_code: str = "FORBIDDEN"


class ConflictResponse(ErrorResponse):
    """Conflict error response schema"""
    error_code: str = "CONFLICT"


class RateLimitResponse(ErrorResponse):
    """Rate limit error response schema"""
    error_code: str = "RATE_LIMIT_EXCEEDED"
    retry_after: Optional[int] = Field(None, description="Retry after seconds")


class ServiceUnavailableResponse(ErrorResponse):
    """Service unavailable error response schema"""
    error_code: str = "SERVICE_UNAVAILABLE"
    retry_after: Optional[int] = Field(None, description="Retry after seconds")