from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from app.schemas.ats import (
    ATSAnalysisRequest, ATSAnalysisResult, ATSComparisonResult,
    ATSScoreHistory, ATSBenchmark, ATSOptimizationSuggestion
)
from app.schemas.response import SuccessResponse
from app.services.ats_analysis_service import ATSAnalysisService
from app.services.ats_enhancement_service import ATSEnhancementService
from app.services.resume_service import ResumeService
from app.core.dependencies import get_current_active_user, get_db, rate_limit_ats_analysis
from app.repositories.ats_repository import ATSRepository

router = APIRouter()


@router.post("/{resume_id}/analyze", response_model=ATSAnalysisResult)
async def analyze_resume_ats(
        resume_id: UUID,
        analysis_request: ATSAnalysisRequest = Body(...),
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db),
        _: None = Depends(rate_limit_ats_analysis)  # Rate limiting for expensive operations
):
    """Perform comprehensive ATS analysis on a resume"""
    try:
        # Get resume and verify ownership
        resume_service = ResumeService(db)
        resume = await resume_service.get_resume(resume_id, UUID(current_user["id"]))

        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        # Validate analysis request
        if analysis_request.job_description and len(analysis_request.job_description) > 10000:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Job description too long (max 10,000 characters)"
            )

        # Perform ATS analysis
        ats_service = ATSAnalysisService()
        analysis_result = await ats_service.analyze_resume(
            resume_content=resume.content.dict(),
            job_description=analysis_request.job_description,
            target_industry=analysis_request.target_industry
        )

        # Save analysis results
        try:
            ats_repo = ATSRepository(db)
            await ats_repo.save_analysis_result(
                resume_id=resume_id,
                user_id=UUID(current_user["id"]),
                analysis_result=analysis_result
            )
        except Exception as save_error:
            # Log but don't fail the request if saving fails
            logger.error(f"Failed to save ATS analysis: {save_error}")

        return analysis_result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error analyzing resume {resume_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze resume"
        )


@router.get("/{resume_id}/score-history", response_model=ATSScoreHistory)
async def get_ats_score_history(
        resume_id: UUID,
        limit: int = Query(10, ge=1, le=50, description="Number of historical scores to return"),
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get historical ATS scores for a resume"""
    try:
        # Verify resume ownership
        resume_service = ResumeService(db)
        resume = await resume_service.get_resume(resume_id, UUID(current_user["id"]))

        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        # Get score history
        ats_repo = ATSRepository(db)
        score_history = await ats_repo.get_score_history(resume_id, limit)

        return score_history

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting score history for resume {resume_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve score history"
        )


@router.post("/{resume_id}/compare-jobs", response_model=ATSComparisonResult)
async def compare_resume_against_jobs(
        resume_id: UUID,
        job_descriptions: List[str] = Body(..., min_items=1, max_items=5),
        job_titles: Optional[List[str]] = Body(None),
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db),
        _: None = Depends(rate_limit_ats_analysis)
):
    """Compare resume against multiple job descriptions"""
    try:
        # Validate input
        if any(len(desc) > 5000 for desc in job_descriptions):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Job descriptions too long (max 5,000 characters each)"
            )

        if job_titles and len(job_titles) != len(job_descriptions):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Number of job titles must match number of job descriptions"
            )

        # Get resume and verify ownership
        resume_service = ResumeService(db)
        resume = await resume_service.get_resume(resume_id, UUID(current_user["id"]))

        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        # Perform comparison analysis
        ats_service = ATSAnalysisService()
        comparison_results = []

        for i, job_desc in enumerate(job_descriptions):
            try:
                job_title = job_titles[i] if job_titles and i < len(job_titles) else f"Job {i + 1}"

                analysis = await ats_service.analyze_resume(
                    resume_content=resume.content.dict(),
                    job_description=job_desc
                )

                comparison_results.append({
                    "job_title": job_title,
                    "job_description": job_desc[:200] + "..." if len(job_desc) > 200 else job_desc,
                    "match_percentage": analysis.job_match_percentage or 0,
                    "ats_score": analysis.overall_ats_score,
                    "keyword_score": analysis.keyword_score,
                    "missing_keywords": analysis.keyword_analysis.missing_keywords[:10],
                    "top_recommendations": [rec.title for rec in analysis.recommendations[:3]]
                })

            except Exception as job_error:
                logger.error(f"Error analyzing job {i}: {job_error}")
                comparison_results.append({
                    "job_title": job_titles[i] if job_titles and i < len(job_titles) else f"Job {i + 1}",
                    "job_description": job_desc[:200] + "..." if len(job_desc) > 200 else job_desc,
                    "match_percentage": 0,
                    "ats_score": 0,
                    "keyword_score": 0,
                    "missing_keywords": [],
                    "top_recommendations": [],
                    "error": "Analysis failed"
                })

        # Calculate summary statistics
        successful_results = [r for r in comparison_results if "error" not in r]

        if successful_results:
            best_match = max(successful_results, key=lambda x: x["match_percentage"])
            best_match_job = best_match["job_title"]
            avg_match = sum(result["match_percentage"] for result in successful_results) / len(successful_results)
        else:
            best_match_job = "None"
            avg_match = 0