from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.schemas.resume import (
    ResumeCreate, ResumeUpdate, ResumeResponse, ResumeListItem,
    ResumeDuplicate, ResumeValidation, ResumePreview
)
from app.schemas.response import PaginatedResponse, SuccessResponse
from app.services.resume_service import ResumeService
from app.core.dependencies import get_current_active_user, get_db
from app.core.config import settings

router = APIRouter()


@router.post("/", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def create_resume(
        resume_data: ResumeCreate,
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Create a new resume"""
    try:
        service = ResumeService(db)
        return await service.create_resume(
            user_id=UUID(current_user["id"]),
            resume_data=resume_data
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create resume"
        )


@router.get("/", response_model=PaginatedResponse[ResumeListItem])
async def list_resumes(
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(10, ge=1, le=100, description="Items per page"),
        is_active: Optional[bool] = Query(None, description="Filter by active status"),
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """List user's resumes with pagination"""
    try:
        service = ResumeService(db)
        return await service.get_user_resumes(
            user_id=UUID(current_user["id"]),
            page=page,
            size=size,
            is_active=is_active
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resumes"
        )


@router.get("/search", response_model=PaginatedResponse[ResumeListItem])
async def search_resumes(
        q: str = Query(..., min_length=1, description="Search query"),
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(10, ge=1, le=100, description="Items per page"),
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Search user's resumes"""
    try:
        service = ResumeService(db)
        return await service.search_resumes(
            user_id=UUID(current_user["id"]),
            search_term=q,
            page=page,
            size=size
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search resumes"
        )


@router.get("/stats")
async def get_resume_stats(
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get user's resume statistics"""
    try:
        service = ResumeService(db)
        stats = await service.get_user_resume_stats(UUID(current_user["id"]))
        return SuccessResponse(data=stats)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get resume statistics"
        )


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
        resume_id: UUID,
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get specific resume by ID"""
    try:
        service = ResumeService(db)
        resume = await service.get_resume(
            resume_id=resume_id,
            user_id=UUID(current_user["id"])
        )

        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        return resume
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resume"
        )


@router.put("/{resume_id}", response_model=ResumeResponse)
async def update_resume(
        resume_id: UUID,
        update_data: ResumeUpdate,
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Update existing resume"""
    try:
        service = ResumeService(db)
        resume = await service.update_resume(
            resume_id=resume_id,
            user_id=UUID(current_user["id"]),
            update_data=update_data
        )

        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        return resume
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update resume"
        )


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
        resume_id: UUID,
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Delete resume"""
    try:
        service = ResumeService(db)
        success = await service.delete_resume(
            resume_id=resume_id,
            user_id=UUID(current_user["id"])
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete resume"
        )


@router.post("/{resume_id}/duplicate", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_resume(
        resume_id: UUID,
        duplicate_data: ResumeDuplicate,
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Create a copy of existing resume"""
    try:
        service = ResumeService(db)
        duplicated_resume = await service.duplicate_resume(
            resume_id=resume_id,
            user_id=UUID(current_user["id"]),
            new_title=duplicate_data.title
        )

        if not duplicated_resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        return duplicated_resume
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to duplicate resume"
        )


@router.post("/{resume_id}/validate", response_model=ResumeValidation)
async def validate_resume(
        resume_id: UUID,
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Validate resume content and get recommendations"""
    try:
        service = ResumeService(db)
        validation_result = await service.validate_resume(
            resume_id=resume_id,
            user_id=UUID(current_user["id"])
        )

        if not validation_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        return validation_result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate resume"
        )


@router.get("/{resume_id}/preview", response_model=ResumePreview)
async def get_resume_preview(
        resume_id: UUID,
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get resume preview with HTML and completeness info"""
    try:
        service = ResumeService(db)
        preview = await service.get_resume_preview(
            resume_id=resume_id,
            user_id=UUID(current_user["id"])
        )

        if not preview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        return preview
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate resume preview"
        )


@router.post("/{resume_id}/export")
async def export_resume(
        resume_id: UUID,
        export_format: str = Query("pdf", description="Export format (pdf, docx, html)"),
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Export resume to specified format"""
    try:
        service = ResumeService(db)
        export_job = await service.export_resume(
            resume_id=resume_id,
            user_id=UUID(current_user["id"]),
            export_format=export_format
        )

        if not export_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        return SuccessResponse(data=export_job)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export resume"
        )