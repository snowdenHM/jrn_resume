from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
import logging

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

# Add logger
logger = logging.getLogger(__name__)

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
        logger.info(f"Starting ATS analysis for resume {resume_id} by user {current_user['id']}")

        # Get resume and verify ownership
        resume_service = ResumeService(db)
        resume = await resume_service.get_resume(resume_id, UUID(current_user["id"]))

        if not resume:
            logger.warning(f"Resume {resume_id} not found for user {current_user['id']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        # Validate analysis request
        if analysis_request.job_description and len(analysis_request.job_description) > 10000:
            logger.warning(f"Job description too long: {len(analysis_request.job_description)} characters")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Job description too long (max 10,000 characters)"
            )

        # Validate target industry if provided
        if analysis_request.target_industry and len(analysis_request.target_industry) > 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Target industry name too long (max 100 characters)"
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
            logger.info(f"ATS analysis results saved for resume {resume_id}")
        except Exception as save_error:
            # Log but don't fail the request if saving fails
            logger.error(f"Failed to save ATS analysis: {save_error}")

        logger.info(f"ATS analysis completed for resume {resume_id} with score {analysis_result.overall_ats_score}")
        return analysis_result

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error in ATS analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error analyzing resume {resume_id}: {e}", exc_info=True)
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
        logger.info(f"Getting ATS score history for resume {resume_id}")

        # Verify resume ownership
        resume_service = ResumeService(db)
        resume = await resume_service.get_resume(resume_id, UUID(current_user["id"]))

        if not resume:
            logger.warning(f"Resume {resume_id} not found for user {current_user['id']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        # Get score history
        ats_repo = ATSRepository(db)
        score_history = await ats_repo.get_score_history(resume_id, limit)

        logger.info(f"Retrieved {len(score_history.scores)} historical scores for resume {resume_id}")
        return score_history

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting score history for resume {resume_id}: {e}", exc_info=True)
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
        logger.info(f"Comparing resume {resume_id} against {len(job_descriptions)} jobs")

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
            logger.warning(f"Resume {resume_id} not found for user {current_user['id']}")
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

        # Generate summary recommendations
        all_missing_keywords = []
        for result in successful_results:
            all_missing_keywords.extend(result["missing_keywords"])

        # Get most common missing keywords
        from collections import Counter
        common_missing = [kw for kw, _ in Counter(all_missing_keywords).most_common(5)]

        recommendations_summary = []
        if common_missing:
            recommendations_summary.append(f"Add these commonly missing keywords: {', '.join(common_missing)}")
        if avg_match < 60:
            recommendations_summary.append("Consider tailoring your resume more specifically to job requirements")
        if len(successful_results) < len(job_descriptions):
            recommendations_summary.append("Some job analyses failed - try with shorter job descriptions")

        comparison_result = ATSComparisonResult(
            resume_id=str(resume_id),
            job_comparisons=comparison_results,
            best_match_job=best_match_job,
            average_match_percentage=round(avg_match, 1),
            recommendations_summary=recommendations_summary
        )

        logger.info(
            f"Completed job comparison for resume {resume_id}. Best match: {best_match_job} ({best_match.get('match_percentage', 0):.1f}%)")
        return comparison_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing resume against jobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare resume against jobs"
        )


@router.get("/{resume_id}/optimization-suggestions", response_model=List[ATSOptimizationSuggestion])
async def get_optimization_suggestions(
        resume_id: UUID,
        job_description: Optional[str] = Query(None, max_length=5000,
                                               description="Job description for tailored suggestions"),
        target_industry: Optional[str] = Query(None, max_length=100, description="Target industry"),
        max_suggestions: int = Query(10, ge=1, le=20, description="Maximum number of suggestions"),
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get specific ATS optimization suggestions for a resume"""
    try:
        logger.info(f"Getting optimization suggestions for resume {resume_id}")

        # Verify resume ownership
        resume_service = ResumeService(db)
        resume = await resume_service.get_resume(resume_id, UUID(current_user["id"]))

        if not resume:
            logger.warning(f"Resume {resume_id} not found for user {current_user['id']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        # Get optimization suggestions
        enhancement_service = ATSEnhancementService()
        suggestions = await enhancement_service.generate_optimization_suggestions(
            resume_content=resume.content.dict(),
            job_description=job_description,
            target_industry=target_industry,
            max_suggestions=max_suggestions
        )

        logger.info(f"Generated {len(suggestions)} optimization suggestions for resume {resume_id}")
        return suggestions

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting optimization suggestions for resume {resume_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get optimization suggestions"
        )


@router.get("/benchmarks", response_model=List[ATSBenchmark])
async def get_industry_benchmarks(
        industry: Optional[str] = Query(None, description="Filter by industry"),
        role_level: Optional[str] = Query(None, description="Filter by role level"),
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get ATS benchmarks by industry and role level"""
    try:
        logger.info(f"Getting ATS benchmarks for industry: {industry}, role_level: {role_level}")

        enhancement_service = ATSEnhancementService()
        benchmarks = await enhancement_service.get_ats_benchmarks(
            industry=industry,
            role_level=role_level
        )

        logger.info(f"Retrieved {len(benchmarks)} ATS benchmarks")
        return benchmarks

    except Exception as e:
        logger.error(f"Error getting ATS benchmarks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ATS benchmarks"
        )


@router.get("/user-statistics", response_model=SuccessResponse)
async def get_user_ats_statistics(
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get comprehensive ATS statistics for the current user"""
    try:
        logger.info(f"Getting ATS statistics for user {current_user['id']}")

        ats_repo = ATSRepository(db)
        stats = await ats_repo.get_user_ats_statistics(UUID(current_user["id"]))

        return SuccessResponse(
            message="ATS statistics retrieved successfully",
            data=stats
        )

    except Exception as e:
        logger.error(f"Error getting user ATS statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ATS statistics"
        )


@router.get("/{resume_id}/detailed-analysis", response_model=SuccessResponse)
async def get_detailed_ats_analysis(
        resume_id: UUID,
        include_suggestions: bool = Query(True, description="Include optimization suggestions"),
        include_benchmarks: bool = Query(True, description="Include industry benchmarks"),
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get detailed ATS analysis including history, suggestions, and benchmarks"""
    try:
        logger.info(f"Getting detailed ATS analysis for resume {resume_id}")

        # Verify resume ownership
        resume_service = ResumeService(db)
        resume = await resume_service.get_resume(resume_id, UUID(current_user["id"]))

        if not resume:
            logger.warning(f"Resume {resume_id} not found for user {current_user['id']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        # Get latest analysis
        ats_repo = ATSRepository(db)
        latest_analysis = await ats_repo.get_latest_analysis(resume_id, UUID(current_user["id"]))

        # Get score history
        score_history = await ats_repo.get_score_history(resume_id, limit=20)

        detailed_analysis = {
            "resume_id": str(resume_id),
            "latest_analysis": latest_analysis.to_dict() if latest_analysis else None,
            "score_history": score_history.dict(),
            "analysis_count": len(score_history.scores)
        }

        # Include suggestions if requested
        if include_suggestions and latest_analysis:
            try:
                enhancement_service = ATSEnhancementService()
                suggestions = await enhancement_service.generate_optimization_suggestions(
                    resume_content=resume.content.dict(),
                    max_suggestions=15
                )
                detailed_analysis["optimization_suggestions"] = [s.dict() for s in suggestions]
            except Exception as e:
                logger.error(f"Error getting suggestions: {e}")
                detailed_analysis["optimization_suggestions"] = []

        # Include benchmarks if requested
        if include_benchmarks:
            try:
                enhancement_service = ATSEnhancementService()
                benchmarks = await enhancement_service.get_ats_benchmarks()
                detailed_analysis["industry_benchmarks"] = [b.dict() for b in benchmarks]
            except Exception as e:
                logger.error(f"Error getting benchmarks: {e}")
                detailed_analysis["industry_benchmarks"] = []

        return SuccessResponse(
            message="Detailed ATS analysis retrieved successfully",
            data=detailed_analysis
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting detailed ATS analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get detailed ATS analysis"
        )


@router.delete("/{resume_id}/analysis-history", response_model=SuccessResponse)
async def clear_ats_analysis_history(
        resume_id: UUID,
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Clear ATS analysis history for a resume (keep only the latest)"""
    try:
        logger.info(f"Clearing ATS analysis history for resume {resume_id}")

        # Verify resume ownership
        resume_service = ResumeService(db)
        resume = await resume_service.get_resume(resume_id, UUID(current_user["id"]))

        if not resume:
            logger.warning(f"Resume {resume_id} not found for user {current_user['id']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        # Clear analysis history except latest
        ats_repo = ATSRepository(db)

        # Get all analyses for this resume
        analyses = await ats_repo.get_analysis_history(resume_id, UUID(current_user["id"]), limit=100)

        if len(analyses) <= 1:
            return SuccessResponse(
                message="No analysis history to clear",
                data={"cleared_count": 0}
            )

        # Keep the latest, delete the rest
        analyses_to_delete = analyses[1:]  # Skip the first (latest) one
        cleared_count = 0

        for analysis in analyses_to_delete:
            try:
                db.delete(analysis)
                cleared_count += 1
            except Exception as e:
                logger.error(f"Error deleting analysis {analysis.id}: {e}")

        db.commit()

        return SuccessResponse(
            message=f"Cleared {cleared_count} old ATS analyses",
            data={"cleared_count": cleared_count}
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error clearing ATS analysis history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear analysis history"
        )


@router.get("/top-performing-resumes", response_model=SuccessResponse)
async def get_top_performing_resumes(
        limit: int = Query(5, ge=1, le=20, description="Number of top resumes to return"),
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get user's top performing resumes based on ATS scores"""
    try:
        logger.info(f"Getting top {limit} performing resumes for user {current_user['id']}")

        ats_repo = ATSRepository(db)
        top_resumes = await ats_repo.get_top_performing_resumes(
            user_id=UUID(current_user["id"]),
            limit=limit
        )

        return SuccessResponse(
            message=f"Retrieved top {len(top_resumes)} performing resumes",
            data={
                "top_resumes": top_resumes,
                "count": len(top_resumes)
            }
        )

    except Exception as e:
        logger.error(f"Error getting top performing resumes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get top performing resumes"
        )


@router.get("/improvement-suggestions-stats", response_model=SuccessResponse)
async def get_improvement_suggestions_stats(
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get statistics about improvement suggestions across all user's resumes"""
    try:
        logger.info(f"Getting improvement suggestions stats for user {current_user['id']}")

        ats_repo = ATSRepository(db)
        stats = await ats_repo.get_improvement_suggestions_stats(UUID(current_user["id"]))

        return SuccessResponse(
            message="Improvement suggestions statistics retrieved successfully",
            data=stats
        )

    except Exception as e:
        logger.error(f"Error getting improvement suggestions stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get improvement suggestions statistics"
        )


@router.post("/{resume_id}/bulk-analyze", response_model=SuccessResponse)
async def bulk_analyze_against_multiple_industries(
        resume_id: UUID,
        industries: List[str] = Body(..., min_items=1, max_items=10),
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db),
        _: None = Depends(rate_limit_ats_analysis)
):
    """Analyze resume against multiple industries for comprehensive insights"""
    try:
        logger.info(f"Bulk analyzing resume {resume_id} against {len(industries)} industries")

        # Verify resume ownership
        resume_service = ResumeService(db)
        resume = await resume_service.get_resume(resume_id, UUID(current_user["id"]))

        if not resume:
            logger.warning(f"Resume {resume_id} not found for user {current_user['id']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        # Validate industries
        valid_industries = ["technology", "healthcare", "finance", "marketing", "sales", "education", "manufacturing",
                            "consulting"]
        invalid_industries = [ind for ind in industries if ind.lower() not in valid_industries]

        if invalid_industries:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid industries: {', '.join(invalid_industries)}. Valid options: {', '.join(valid_industries)}"
            )

        # Perform analysis for each industry
        ats_service = ATSAnalysisService()
        industry_analyses = []

        for industry in industries:
            try:
                analysis = await ats_service.analyze_resume(
                    resume_content=resume.content.dict(),
                    target_industry=industry
                )

                industry_analyses.append({
                    "industry": industry,
                    "overall_score": analysis.overall_ats_score,
                    "keyword_score": analysis.keyword_score,
                    "formatting_score": analysis.formatting_score,
                    "content_score": analysis.content_structure_score,
                    "readability_score": analysis.readability_score,
                    "top_recommendations": [rec.title for rec in analysis.recommendations[:3]],
                    "industry_insights": analysis.industry_insights
                })

            except Exception as industry_error:
                logger.error(f"Error analyzing for industry {industry}: {industry_error}")
                industry_analyses.append({
                    "industry": industry,
                    "error": "Analysis failed",
                    "overall_score": 0
                })

        # Find best and worst performing industries
        successful_analyses = [a for a in industry_analyses if "error" not in a]

        best_industry = None
        worst_industry = None
        avg_score = 0

        if successful_analyses:
            best_industry = max(successful_analyses, key=lambda x: x["overall_score"])
            worst_industry = min(successful_analyses, key=lambda x: x["overall_score"])
            avg_score = sum(a["overall_score"] for a in successful_analyses) / len(successful_analyses)

        # Generate cross-industry recommendations
        all_recommendations = []
        for analysis in successful_analyses:
            all_recommendations.extend(analysis.get("top_recommendations", []))

        from collections import Counter
        common_recommendations = [rec for rec, count in Counter(all_recommendations).most_common(5)]

        bulk_analysis_result = {
            "resume_id": str(resume_id),
            "industries_analyzed": len(industries),
            "successful_analyses": len(successful_analyses),
            "average_score": round(avg_score, 1),
            "best_industry": best_industry["industry"] if best_industry else None,
            "best_score": best_industry["overall_score"] if best_industry else 0,
            "worst_industry": worst_industry["industry"] if worst_industry else None,
            "worst_score": worst_industry["overall_score"] if worst_industry else 0,
            "industry_analyses": industry_analyses,
            "common_recommendations": common_recommendations,
            "insights": {
                "most_consistent_scores": len(set(a["overall_score"] for a in successful_analyses)) <= 2,
                "score_variance": max(a["overall_score"] for a in successful_analyses) - min(
                    a["overall_score"] for a in successful_analyses) if successful_analyses else 0
            }
        }

        return SuccessResponse(
            message=f"Bulk analysis completed for {len(successful_analyses)} industries",
            data=bulk_analysis_result
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete bulk analysis"
        )