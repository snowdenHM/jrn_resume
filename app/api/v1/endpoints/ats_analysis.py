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
from app.services.resume_service import ResumeService
from app.core.dependencies import get_current_active_user, get_db
from app.repositories.ats_repository import ATSRepository

router = APIRouter()


@router.post("/{resume_id}/analyze", response_model=ATSAnalysisResult)
async def analyze_resume_ats(
        resume_id: UUID,
        analysis_request: ATSAnalysisRequest = Body(...),
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Perform comprehensive ATS analysis on a resume"""
    try:
        # Get resume
        resume_service = ResumeService(db)
        resume = await resume_service.get_resume(resume_id, UUID(current_user["id"]))

        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        # Perform ATS analysis
        ats_service = ATSAnalysisService()
        analysis_result = await ats_service.analyze_resume(
            resume_content=resume.content,
            job_description=analysis_request.job_description,
            target_industry=analysis_request.target_industry
        )

        # Save analysis results
        ats_repo = ATSRepository(db)
        await ats_repo.save_analysis_result(
            resume_id=resume_id,
            user_id=UUID(current_user["id"]),
            analysis_result=analysis_result
        )

        return analysis_result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze resume: {str(e)}"
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
        ats_repo = ATSRepository(db)

        # Verify resume ownership
        resume_service = ResumeService(db)
        resume = await resume_service.get_resume(resume_id, UUID(current_user["id"]))

        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        # Get score history
        score_history = await ats_repo.get_score_history(resume_id, limit)

        return score_history

    except HTTPException:
        raise
    except Exception as e:
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
        db: Session = Depends(get_db)
):
    """Compare resume against multiple job descriptions"""
    try:
        # Get resume
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
            job_title = job_titles[i] if job_titles and i < len(job_titles) else f"Job {i + 1}"

            analysis = await ats_service.analyze_resume(
                resume_content=resume.content,
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

        # Find best match
        best_match = max(comparison_results, key=lambda x: x["match_percentage"])
        best_match_job = best_match["job_title"]

        # Calculate average match
        avg_match = sum(result["match_percentage"] for result in comparison_results) / len(comparison_results)

        # Generate summary recommendations
        all_missing_keywords = set()
        for result in comparison_results:
            all_missing_keywords.update(result["missing_keywords"])

        summary_recommendations = [
            f"Add these frequently missing keywords: {', '.join(list(all_missing_keywords)[:5])}",
            f"Your resume matches best with: {best_match_job}",
            f"Average job match: {avg_match:.1f}% - aim for 70%+ for better ATS success"
        ]

        comparison_result = ATSComparisonResult(
            resume_id=str(resume_id),
            job_comparisons=comparison_results,
            best_match_job=best_match_job,
            average_match_percentage=avg_match,
            recommendations_summary=summary_recommendations
        )

        return comparison_result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare resume against jobs: {str(e)}"
        )


@router.get("/benchmarks", response_model=List[ATSBenchmark])
async def get_ats_benchmarks(
        industry: Optional[str] = Query(None, description="Filter by industry"),
        role_level: Optional[str] = Query(None, description="Filter by role level")
):
    """Get ATS benchmarks for different industries and role levels"""
    try:
        ats_service = ATSAnalysisService()
        benchmarks = await ats_service.get_ats_benchmarks(industry, role_level)

        return benchmarks

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve ATS benchmarks"
        )


@router.post("/{resume_id}/optimization-suggestions", response_model=List[ATSOptimizationSuggestion])
async def get_optimization_suggestions(
        resume_id: UUID,
        job_description: Optional[str] = Body(None),
        target_industry: Optional[str] = Body(None),
        max_suggestions: int = Query(5, ge=1, le=20),
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get specific text optimization suggestions for resume"""
    try:
        # Get resume
        resume_service = ResumeService(db)
        resume = await resume_service.get_resume(resume_id, UUID(current_user["id"]))

        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        # Generate optimization suggestions
        ats_service = ATSAnalysisService()
        suggestions = await ats_service.generate_optimization_suggestions(
            resume_content=resume.content,
            job_description=job_description,
            target_industry=target_industry,
            max_suggestions=max_suggestions
        )

        return suggestions

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate optimization suggestions"
        )


@router.get("/{resume_id}/ats-report")
async def get_comprehensive_ats_report(
        resume_id: UUID,
        job_description: Optional[str] = Query(None),
        target_industry: Optional[str] = Query(None),
        include_comparisons: bool = Query(False),
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Generate comprehensive ATS report with all analysis components"""
    try:
        # Get resume
        resume_service = ResumeService(db)
        resume = await resume_service.get_resume(resume_id, UUID(current_user["id"]))

        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        # Perform comprehensive analysis
        ats_service = ATSAnalysisService()

        # Basic ATS analysis
        analysis_result = await ats_service.analyze_resume(
            resume_content=resume.content,
            job_description=job_description,
            target_industry=target_industry
        )

        # Get optimization suggestions
        optimization_suggestions = await ats_service.generate_optimization_suggestions(
            resume_content=resume.content,
            job_description=job_description,
            target_industry=target_industry,
            max_suggestions=10
        )

        # Get score history
        ats_repo = ATSRepository(db)
        score_history = await ats_repo.get_score_history(resume_id, 5)

        # Compile comprehensive report
        report = {
            "resume_info": {
                "id": str(resume.id),
                "title": resume.title,
                "last_updated": resume.updated_at,
                "version": resume.version
            },
            "ats_analysis": analysis_result,
            "optimization_suggestions": optimization_suggestions,
            "score_history": score_history,
            "summary": {
                "overall_grade": _get_grade_from_score(analysis_result.overall_ats_score),
                "strengths": _identify_strengths(analysis_result),
                "priority_improvements": [rec.title for rec in analysis_result.recommendations[:3]],
                "next_steps": _generate_next_steps(analysis_result)
            }
        }

        return SuccessResponse(data=report)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate comprehensive ATS report"
        )


@router.post("/bulk-analyze")
async def bulk_analyze_resumes(
        resume_ids: List[UUID] = Body(..., min_items=1, max_items=10),
        job_description: Optional[str] = Body(None),
        target_industry: Optional[str] = Body(None),
        current_user: dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Analyze multiple resumes in bulk"""
    try:
        resume_service = ResumeService(db)
        ats_service = ATSAnalysisService()

        results = []

        for resume_id in resume_ids:
            try:
                # Get resume
                resume = await resume_service.get_resume(resume_id, UUID(current_user["id"]))

                if not resume:
                    results.append({
                        "resume_id": str(resume_id),
                        "status": "error",
                        "message": "Resume not found"
                    })
                    continue

                # Perform analysis
                analysis = await ats_service.analyze_resume(
                    resume_content=resume.content,
                    job_description=job_description,
                    target_industry=target_industry
                )

                results.append({
                    "resume_id": str(resume_id),
                    "resume_title": resume.title,
                    "status": "success",
                    "overall_score": analysis.overall_ats_score,
                    "keyword_score": analysis.keyword_score,
                    "job_match_percentage": analysis.job_match_percentage,
                    "top_recommendation": analysis.recommendations[0].title if analysis.recommendations else None
                })

            except Exception as e:
                results.append({
                    "resume_id": str(resume_id),
                    "status": "error",
                    "message": str(e)
                })

        # Generate summary
        successful_analyses = [r for r in results if r["status"] == "success"]

        summary = {
            "total_resumes": len(resume_ids),
            "successful_analyses": len(successful_analyses),
            "failed_analyses": len(resume_ids) - len(successful_analyses),
            "average_score": sum(r["overall_score"] for r in successful_analyses) / len(
                successful_analyses) if successful_analyses else 0,
            "best_performing_resume": max(successful_analyses,
                                          key=lambda x: x["overall_score"]) if successful_analyses else None
        }

        return SuccessResponse(data={
            "summary": summary,
            "detailed_results": results
        })

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform bulk analysis: {str(e)}"
        )


def _get_grade_from_score(score: int) -> str:
    """Convert numerical score to letter grade"""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


def _identify_strengths(analysis_result: ATSAnalysisResult) -> List[str]:
    """Identify resume strengths based on analysis"""
    strengths = []

    if analysis_result.formatting_score >= 80:
        strengths.append("Well-structured and ATS-friendly formatting")

    if analysis_result.keyword_score >= 75:
        strengths.append("Good keyword optimization")

    if analysis_result.content_structure_score >= 80:
        strengths.append("Strong content organization and depth")

    if analysis_result.job_match_percentage and analysis_result.job_match_percentage >= 70:
        strengths.append("Excellent alignment with job requirements")

    if len(analysis_result.skill_gaps.matching_skills) >= 5:
        strengths.append("Strong skill alignment with industry requirements")

    if not strengths:
        strengths.append("Resume has potential for improvement with targeted optimization")

    return strengths


def _generate_next_steps(analysis_result: ATSAnalysisResult) -> List[str]:
    """Generate actionable next steps based on analysis"""
    next_steps = []

    # Prioritize based on scores
    if analysis_result.overall_ats_score < 60:
        next_steps.append("Focus on fundamental resume structure and formatting improvements")

    if analysis_result.keyword_score < 70:
        next_steps.append("Optimize keyword usage throughout your resume")

    if analysis_result.job_match_percentage and analysis_result.job_match_percentage < 60:
        next_steps.append("Tailor your resume more closely to the specific job requirements")

    # Add top recommendations as next steps
    for rec in analysis_result.recommendations[:2]:
        if rec.action_items:
            next_steps.append(rec.action_items[0])

    if not next_steps:
        next_steps.append("Continue refining your resume and keep it updated with new skills and experiences")

    return next_steps[:4]  # Limit to 4 actionable steps