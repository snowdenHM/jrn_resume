from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from uuid import UUID
from datetime import datetime, timedelta
import json
import logging

from app.repositories.base import BaseRepository
from app.models.ats_analysis import ATSAnalysis, ATSScoreHistory
from app.schemas.ats import ATSAnalysisResult, ATSScoreHistory as ATSScoreHistorySchema

logger = logging.getLogger(__name__)


class ATSRepository(BaseRepository[ATSAnalysis]):
    """Repository for ATS analysis data"""

    def __init__(self, db: Session):
        super().__init__(db, ATSAnalysis)

    async def save_analysis_result(
            self,
            resume_id: UUID,
            user_id: UUID,
            analysis_result: ATSAnalysisResult
    ) -> ATSAnalysis:
        """Save ATS analysis result to database"""
        try:
            # Create analysis record
            analysis_data = {
                "resume_id": resume_id,
                "user_id": user_id,
                "overall_ats_score": analysis_result.overall_ats_score,
                "formatting_score": analysis_result.formatting_score,
                "keyword_score": analysis_result.keyword_score,
                "content_structure_score": analysis_result.content_structure_score,
                "readability_score": analysis_result.readability_score,
                "job_match_percentage": analysis_result.job_match_percentage,
                "analysis_data": analysis_result.dict(),
                "analysis_timestamp": analysis_result.analysis_timestamp
            }

            analysis = self.create(**analysis_data)

            # Update score history
            await self._update_score_history(resume_id, analysis_result.overall_ats_score)

            logger.info(f"Saved ATS analysis for resume {resume_id}")
            return analysis

        except Exception as e:
            logger.error(f"Error saving ATS analysis: {e}")
            raise

    async def get_latest_analysis(self, resume_id: UUID, user_id: UUID) -> Optional[ATSAnalysis]:
        """Get the most recent ATS analysis for a resume"""
        try:
            return self.db.query(ATSAnalysis).filter(
                and_(
                    ATSAnalysis.resume_id == resume_id,
                    ATSAnalysis.user_id == user_id
                )
            ).order_by(desc(ATSAnalysis.created_at)).first()

        except Exception as e:
            logger.error(f"Error getting latest analysis: {e}")
            raise

    async def get_analysis_history(
            self,
            resume_id: UUID,
            user_id: UUID,
            limit: int = 10
    ) -> List[ATSAnalysis]:
        """Get analysis history for a resume"""
        try:
            return self.db.query(ATSAnalysis).filter(
                and_(
                    ATSAnalysis.resume_id == resume_id,
                    ATSAnalysis.user_id == user_id
                )
            ).order_by(desc(ATSAnalysis.created_at)).limit(limit).all()

        except Exception as e:
            logger.error(f"Error getting analysis history: {e}")
            raise

    async def get_score_history(self, resume_id: UUID, limit: int = 10) -> ATSScoreHistorySchema:
        """Get score history for trending analysis"""
        try:
            # Get score history record
            score_history = self.db.query(ATSScoreHistory).filter(
                ATSScoreHistory.resume_id == resume_id
            ).first()

            if not score_history:
                # Create empty history if none exists
                return ATSScoreHistorySchema(
                    resume_id=str(resume_id),
                    scores=[],
                    improvement_trend="neutral",
                    last_analysis_date=datetime.utcnow()
                )

            # Parse scores and limit results
            scores = json.loads(score_history.scores_json) if score_history.scores_json else []
            limited_scores = scores[-limit:] if limit else scores

            # Calculate improvement trend
            trend = self._calculate_improvement_trend(limited_scores)

            return ATSScoreHistorySchema(
                resume_id=str(resume_id),
                scores=limited_scores,
                improvement_trend=trend,
                last_analysis_date=score_history.last_analysis_date
            )

        except Exception as e:
            logger.error(f"Error getting score history: {e}")
            raise

    async def _update_score_history(self, resume_id: UUID, new_score: int):
        """Update score history with new score"""
        try:
            # Get existing score history
            score_history = self.db.query(ATSScoreHistory).filter(
                ATSScoreHistory.resume_id == resume_id
            ).first()

            new_score_entry = {
                "score": new_score,
                "timestamp": datetime.utcnow().isoformat(),
                "date": datetime.utcnow().strftime("%Y-%m-%d")
            }

            if score_history:
                # Update existing history
                existing_scores = json.loads(score_history.scores_json) if score_history.scores_json else []
                existing_scores.append(new_score_entry)

                # Keep only last 50 scores to prevent unlimited growth
                if len(existing_scores) > 50:
                    existing_scores = existing_scores[-50:]

                score_history.scores_json = json.dumps(existing_scores)
                score_history.last_analysis_date = datetime.utcnow()
                score_history.total_analyses += 1

                self.db.commit()
            else:
                # Create new score history
                new_history = ATSScoreHistory(
                    resume_id=resume_id,
                    scores_json=json.dumps([new_score_entry]),
                    last_analysis_date=datetime.utcnow(),
                    total_analyses=1
                )

                self.db.add(new_history)
                self.db.commit()

        except Exception as e:
            logger.error(f"Error updating score history: {e}")
            self.db.rollback()
            raise

    def _calculate_improvement_trend(self, scores: List[Dict[str, Any]]) -> str:
        """Calculate improvement trend from score history"""
        if len(scores) < 2:
            return "neutral"

        # Get last 5 scores for trend calculation
        recent_scores = scores[-5:]
        score_values = [entry["score"] for entry in recent_scores]

        # Calculate trend using linear regression slope
        n = len(score_values)
        if n < 2:
            return "neutral"

        x_values = list(range(n))
        x_mean = sum(x_values) / n
        y_mean = sum(score_values) / n

        numerator = sum((x_values[i] - x_mean) * (score_values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "neutral"

        slope = numerator / denominator

        # Determine trend based on slope
        if slope > 2:
            return "improving"
        elif slope < -2:
            return "declining"
        else:
            return "stable"

    async def get_user_ats_statistics(self, user_id: UUID) -> Dict[str, Any]:
        """Get comprehensive ATS statistics for a user"""
        try:
            # Get all analyses for user
            analyses = self.db.query(ATSAnalysis).filter(
                ATSAnalysis.user_id == user_id
            ).order_by(desc(ATSAnalysis.created_at)).all()

            if not analyses:
                return {
                    "total_analyses": 0,
                    "average_score": 0,
                    "highest_score": 0,
                    "lowest_score": 0,
                    "improvement_over_time": 0,
                    "last_analysis_date": None
                }

            scores = [analysis.overall_ats_score for analysis in analyses]

            # Calculate statistics
            stats = {
                "total_analyses": len(analyses),
                "average_score": round(sum(scores) / len(scores), 1),
                "highest_score": max(scores),
                "lowest_score": min(scores),
                "last_analysis_date": analyses[0].created_at,
                "analyses_this_month": len([
                    a for a in analyses
                    if a.created_at >= datetime.utcnow() - timedelta(days=30)
                ])
            }

            # Calculate improvement over time
            if len(scores) >= 2:
                first_score = scores[-1]  # Oldest
                last_score = scores[0]  # Newest
                stats["improvement_over_time"] = last_score - first_score
            else:
                stats["improvement_over_time"] = 0

            return stats

        except Exception as e:
            logger.error(f"Error getting user ATS statistics: {e}")
            raise

    async def get_industry_benchmarks(self, industry: str = None) -> List[Dict[str, Any]]:
        """Get ATS score benchmarks by industry"""
        try:
            # This would typically come from a separate benchmarks table
            # For now, return static benchmarks
            benchmarks = [
                {
                    "industry": "Technology",
                    "role_level": "Entry",
                    "average_ats_score": 72,
                    "top_keywords": ["programming", "software development", "agile", "git"],
                    "recommended_sections": ["technical_skills", "projects", "education"],
                    "optimal_length_words": {"min": 400, "max": 700}
                },
                {
                    "industry": "Technology",
                    "role_level": "Senior",
                    "average_ats_score": 78,
                    "top_keywords": ["leadership", "architecture", "mentoring", "strategy"],
                    "recommended_sections": ["leadership_experience", "technical_skills", "achievements"],
                    "optimal_length_words": {"min": 600, "max": 900}
                },
                {
                    "industry": "Healthcare",
                    "role_level": "Entry",
                    "average_ats_score": 68,
                    "top_keywords": ["patient care", "clinical", "medical", "healthcare"],
                    "recommended_sections": ["clinical_experience", "certifications", "education"],
                    "optimal_length_words": {"min": 400, "max": 650}
                },
                {
                    "industry": "Finance",
                    "role_level": "Mid",
                    "average_ats_score": 75,
                    "top_keywords": ["financial analysis", "excel", "risk management", "compliance"],
                    "recommended_sections": ["quantifiable_achievements", "certifications", "education"],
                    "optimal_length_words": {"min": 500, "max": 750}
                }
            ]

            if industry:
                benchmarks = [b for b in benchmarks if b["industry"].lower() == industry.lower()]

            return benchmarks

        except Exception as e:
            logger.error(f"Error getting industry benchmarks: {e}")
            raise

    async def delete_old_analyses(self, days_old: int = 90):
        """Clean up old analysis records"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            deleted_count = self.db.query(ATSAnalysis).filter(
                ATSAnalysis.created_at < cutoff_date
            ).delete()

            self.db.commit()

            logger.info(f"Deleted {deleted_count} old ATS analysis records")
            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting old analyses: {e}")
            self.db.rollback()
            raise