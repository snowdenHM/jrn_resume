from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
import logging

from app.schemas.cover_letter import (
    CoverLetterCreate, CoverLetterUpdate, CoverLetterResponse, CoverLetterListItem,
    CoverLetterDuplicate, CoverLetterValidation, CoverLetterPreview, CoverLetterFromResume,
    CoverLetterAIRequest
)
from app.schemas.response import PaginatedResponse, SuccessResponse
from app.services.cover_letter_service import CoverLetterService
from app.core.dependencies import get_current_active_user, get_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=CoverLetterResponse, status_code=status.HTTP_201_CREATED)
async def create_cover_letter(
        cover_letter_data: CoverLetterCreate,
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Create a new cover letter"""
    try:
        service = CoverLetterService(db)
        return await service.create_cover_letter(
            user_id=UUID(current_user["id"]),
            cover_letter_data=cover_letter_data
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating cover letter: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create cover letter"
        )


@router.get("/", response_model=PaginatedResponse[CoverLetterListItem])
async def list_cover_letters(
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(10, ge=1, le=100, description="Items per page"),
        is_active: Optional[bool] = Query(None, description="Filter by active status"),
        company_name: Optional[str] = Query(None, description="Filter by company name"),
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """List user's cover letters with pagination"""
    try:
        service = CoverLetterService(db)
        return await service.get_user_cover_letters(
            user_id=UUID(current_user["id"]),
            page=page,
            size=size,
            is_active=is_active,
            company_name=company_name
        )
    except Exception as e:
        logger.error(f"Error listing cover letters: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cover letters"
        )


@router.get("/search", response_model=PaginatedResponse[CoverLetterListItem])
async def search_cover_letters(
        q: str = Query(..., min_length=1, description="Search query"),
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(10, ge=1, le=100, description="Items per page"),
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Search user's cover letters"""
    try:
        service = CoverLetterService(db)
        results, total = await service.search_cover_letters(
            user_id=UUID(current_user["id"]),
            search_term=q,
            page=page,
            size=size
        )

        # Convert to list items
        cover_letter_items = []
        for cover_letter in results:
            try:
                completeness = cover_letter.calculate_completeness()
                word_count = cover_letter.get_word_count()

                cover_letter_item = CoverLetterListItem(
                    id=cover_letter.id,
                    title=cover_letter.title,
                    job_title=cover_letter.job_title,
                    company_name=cover_letter.company_name,
                    template_id=cover_letter.template_id,
                    version=cover_letter.version,
                    is_active=cover_letter.is_active,
                    is_template=cover_letter.is_template,
                    created_at=cover_letter.created_at,
                    updated_at=cover_letter.updated_at,
                    completeness_percentage=completeness['percentage'],
                    word_count=word_count
                )
                cover_letter_items.append(cover_letter_item)
            except Exception as e:
                logger.error(f"Error processing cover letter {cover_letter.id}: {e}")

        return PaginatedResponse.create(
            items=cover_letter_items,
            total=total,
            page=page,
            size=size
        )
    except Exception as e:
        logger.error(f"Error searching cover letters: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search cover letters"
        )


@router.get("/stats")
async def get_cover_letter_stats(
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get user's cover letter statistics"""
    try:
        service = CoverLetterService(db)
        stats = await service.get_user_cover_letter_stats(UUID(current_user["id"]))
        return SuccessResponse(data=stats)
    except Exception as e:
        logger.error(f"Error getting cover letter stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cover letter statistics"
        )


@router.get("/{cover_letter_id}", response_model=CoverLetterResponse)
async def get_cover_letter(
        cover_letter_id: UUID,
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get specific cover letter by ID"""
    try:
        service = CoverLetterService(db)
        cover_letter = await service.get_cover_letter(
            cover_letter_id=cover_letter_id,
            user_id=UUID(current_user["id"])
        )

        if not cover_letter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cover letter not found"
            )

        return cover_letter
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cover letter: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cover letter"
        )


@router.put("/{cover_letter_id}", response_model=CoverLetterResponse)
async def update_cover_letter(
        cover_letter_id: UUID,
        update_data: CoverLetterUpdate,
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Update existing cover letter"""
    try:
        service = CoverLetterService(db)
        cover_letter = await service.update_cover_letter(
            cover_letter_id=cover_letter_id,
            user_id=UUID(current_user["id"]),
            update_data=update_data
        )

        if not cover_letter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cover letter not found"
            )

        return cover_letter
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating cover letter: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update cover letter"
        )


@router.delete("/{cover_letter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cover_letter(
        cover_letter_id: UUID,
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Delete cover letter"""
    try:
        service = CoverLetterService(db)
        success = await service.delete_cover_letter(
            cover_letter_id=cover_letter_id,
            user_id=UUID(current_user["id"])
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cover letter not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting cover letter: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete cover letter"
        )


@router.post("/{cover_letter_id}/duplicate", response_model=CoverLetterResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_cover_letter(
        cover_letter_id: UUID,
        duplicate_data: CoverLetterDuplicate,
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Create a copy of existing cover letter"""
    try:
        service = CoverLetterService(db)
        duplicated_cover_letter = await service.duplicate_cover_letter(
            cover_letter_id=cover_letter_id,
            user_id=UUID(current_user["id"]),
            new_title=duplicate_data.title,
            new_job_title=duplicate_data.job_title,
            new_company_name=duplicate_data.company_name
        )

        if not duplicated_cover_letter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cover letter not found"
            )

        return duplicated_cover_letter
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating cover letter: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to duplicate cover letter"
        )


@router.post("/{cover_letter_id}/validate", response_model=CoverLetterValidation)
async def validate_cover_letter(
        cover_letter_id: UUID,
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Validate cover letter content and get recommendations"""
    try:
        service = CoverLetterService(db)
        validation_result = await service.validate_cover_letter(
            cover_letter_id=cover_letter_id,
            user_id=UUID(current_user["id"])
        )

        if not validation_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cover letter not found"
            )

        return validation_result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating cover letter: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate cover letter"
        )


@router.get("/{cover_letter_id}/preview", response_model=CoverLetterPreview)
async def get_cover_letter_preview(
        cover_letter_id: UUID,
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get cover letter preview with HTML and completeness info"""
    try:
        service = CoverLetterService(db)
        preview = await service.get_cover_letter_preview(
            cover_letter_id=cover_letter_id,
            user_id=UUID(current_user["id"])
        )

        if not preview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cover letter not found"
            )

        return preview
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cover letter preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate cover letter preview"
        )


@router.post("/from-resume", response_model=CoverLetterResponse, status_code=status.HTTP_201_CREATED)
async def generate_cover_letter_from_resume(
        request_data: CoverLetterFromResume,
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Generate cover letter from resume data"""
    try:
        service = CoverLetterService(db)
        cover_letter = await service.generate_from_resume(
            user_id=UUID(current_user["id"]),
            request_data=request_data
        )
        return cover_letter
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating cover letter from resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate cover letter from resume"
        )


@router.post("/ai-generate", response_model=CoverLetterResponse, status_code=status.HTTP_201_CREATED)
async def generate_ai_cover_letter(
        request_data: CoverLetterAIRequest,
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Generate cover letter using AI"""
    try:
        service = CoverLetterService(db)
        cover_letter = await service.generate_ai_cover_letter(
            user_id=UUID(current_user["id"]),
            request_data=request_data
        )
        return cover_letter
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating AI cover letter: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate AI cover letter"
        )