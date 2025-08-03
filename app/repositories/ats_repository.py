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
            # Prepare analysis data with proper JSON serialization
            analysis_data = self._serialize_analysis_result(analysis_result)

            # Create analysis record
            analysis_record = {
                "resume_id": resume_id,
                "user_id": user_id,
                "overall_ats_score": analysis_result.overall_ats_score,
                "formatting_score": analysis_result.formatting_score,
                "keyword_score": analysis_result.keyword_score,
                "content_structure_score": analysis_result.content_structure_score,
                "readability_score": analysis_result.readability_score,
                "job_match_percentage": analysis_result.job_match_percentage,
                "target_industry": getattr(analysis_result, 'target_industry', None),
                "analysis_data": analysis_data,
                "analysis_timestamp": analysis_result.analysis_timestamp,
                "recommendations_count": len(analysis_result.recommendations),
                "critical_issues_count": self._count_critical_issues(analysis_result)
            }

            analysis = self.create(**analysis_record)

            # Update score history
            await self._update_score_history(resume_id, analysis_result.overall_ats_score)

            logger.info(f"Saved ATS analysis for resume {resume_id}")
            return analysis

        except Exception as e:
            logger.error(f"Error saving ATS analysis: {e}")
            self.db.rollback()
            raise

    def _serialize_analysis_result(self, analysis_result: ATSAnalysisResult) -> Dict[str, Any]:
        """Serialize analysis result to JSON-compatible format"""
        try:
            # Convert Pydantic model to dict and handle datetime serialization
            result_dict = analysis_result.dict()

            # Convert datetime to ISO string
            if 'analysis_timestamp' in result_dict:
                timestamp = result_dict['analysis_timestamp']
                if isinstance(timestamp, datetime):
                    result_dict['analysis_timestamp'] = timestamp.isoformat()

            return result_dict
        except Exception as e:
            logger.error(f"Error serializing analysis result: {e}")
            # Return minimal data if serialization fails
            return {
                "overall_ats_score": analysis_result.overall_ats_score,
                "analysis_timestamp": analysis_result.analysis_timestamp.isoformat(),
                "error": "Serialization failed"
            }

    def _count_critical_issues(self, analysis_result: ATSAnalysisResult) -> int:
        """Count critical issues in analysis result"""
        try:
            critical_count = 0

            # Count high priority recommendations
            for recommendation in analysis_result.recommendations:
                if recommendation.priority == "high":
                    critical_count += 1

            # Count missing critical skills
            if hasattr(analysis_result.skill_gaps, 'critical_missing'):
                critical_count += len(analysis_result.skill_gaps.critical_missing)

            # Count low scores as critical issues
            if analysis_result.overall_ats_score < 50:
                critical_count += 1

            return critical_count
        except Exception as e:
            logger.error(f"Error counting critical issues: {e}")
            return 0

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
            try:
                scores = json.loads(score_history.scores_json) if score_history.scores_json else []
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing score history JSON: {e}")
                scores = []

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
                try:
                    existing_scores = json.loads(score_history.scores_json) if score_history.scores_json else []
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in score history for resume {resume_id}, resetting")
                    existing_scores = []

                existing_scores.append(new_score_entry)

                # Keep only last 50 scores to prevent unlimited growth
                if len(existing_scores) > 50:
                    existing_scores = existing_scores[-50:]

                # Update statistics
                scores_only = [entry["score"] for entry in existing_scores]

                score_history.scores_json = json.dumps(existing_scores)
                score_history.last_analysis_date = datetime.utcnow()
                score_history.total_analyses += 1
                score_history.best_score = max(scores_only)
                score_history.worst_score = min(scores_only)
                score_history.average_score = sum(scores_only) / len(scores_only)
                score_history.improvement_trend = self._calculate_improvement_trend(existing_scores)

                self.db.commit()
            else:
                # Create new score history
                new_history = ATSScoreHistory(
                    resume_id=resume_id,
                    scores_json=json.dumps([new_score_entry]),
                    last_analysis_date=datetime.utcnow(),
                    total_analyses=1,
                    best_score=new_score,
                    worst_score=new_score,
                    average_score=float(new_score),
                    improvement_trend="neutral"
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

        try:
            # Get last 5 scores for trend calculation
            recent_scores = scores[-5:]
            score_values = [entry["score"] for entry in recent_scores if "score" in entry]

            if len(score_values) < 2:
                return "neutral"

            # Calculate trend using linear regression slope
            n = len(score_values)
            x_values = list(range(n))
            x_mean = sum(x_values) / n
            y_mean = sum(score_values) / n

            numerator = sum((x_values[i] - x_mean) * (score_values[i] - y_mean) for i in range(n))
            denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

            if denominator == 0:
                return "stable"

            slope = numerator / denominator

            # Determine trend based on slope
            if slope > 2:
                return "improving"
            elif slope < -2:
                return "declining"
            else:
                return "stable"
        except Exception as e:
            logger.error(f"Error calculating improvement trend: {e}")
            return "neutral"

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
                    "last_analysis_date": None,
                    "analyses_this_month": 0,
                    "critical_issues_total": 0
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
                ]),
                "critical_issues_total": sum(a.critical_issues_count or 0 for a in analyses)
            }

            # Calculate improvement over time
            if len(scores) >= 2:
                first_score = scores[-1]  # Oldest
                last_score = scores[0]  # Newest
                stats["improvement_over_time"] = last_score - first_score
            else:
                stats["improvement_over_time"] = 0

            # Add score distribution
            score_ranges = {
                "excellent": len([s for s in scores if s >= 80]),
                "good": len([s for s in scores if 60 <= s < 80]),
                "fair": len([s for s in scores if 40 <= s < 60]),
                "poor": len([s for s in scores if s < 40])
            }
            stats["score_distribution"] = score_ranges

            return stats

        except Exception as e:
            logger.error(f"Error getting user ATS statistics: {e}")
            raise

    async def get_industry_benchmarks(self, industry: str = None) -> List[Dict[str, Any]]:
        """Get ATS score benchmarks by industry"""
        try:
            # This would typically come from a separate benchmarks table
            # For now, return static benchmarks with industry filtering
            all_benchmarks = [
                {
                    "industry": "Technology",
                    "role_level": "Entry",
                    "average_ats_score": 72,
                    "percentile_75": 82,
                    "percentile_90": 89,
                    "top_keywords": ["programming", "software development", "agile", "git"],
                    "recommended_sections": ["technical_skills", "projects", "education"],
                    "optimal_length_words": {"min": 400, "max": 700},
                    "sample_size": 1250
                },
                {
                    "industry": "Technology",
                    "role_level": "Senior",
                    "average_ats_score": 78,
                    "percentile_75": 87,
                    "percentile_90": 93,
                    "top_keywords": ["leadership", "architecture", "mentoring", "strategy"],
                    "recommended_sections": ["leadership_experience", "technical_skills", "achievements"],
                    "optimal_length_words": {"min": 600, "max": 900},
                    "sample_size": 890
                },
                {
                    "industry": "Healthcare",
                    "role_level": "Entry",
                    "average_ats_score": 68,
                    "percentile_75": 79,
                    "percentile_90": 86,
                    "top_keywords": ["patient care", "clinical", "medical", "healthcare"],
                    "recommended_sections": ["clinical_experience", "certifications", "education"],
                    "optimal_length_words": {"min": 400, "max": 650},
                    "sample_size": 743
                },
                {
                    "industry": "Finance",
                    "role_level": "Mid",
                    "average_ats_score": 75,
                    "percentile_75": 84,
                    "percentile_90": 91,
                    "top_keywords": ["financial analysis", "excel", "risk management", "compliance"],
                    "recommended_sections": ["quantifiable_achievements", "certifications", "education"],
                    "optimal_length_words": {"min": 500, "max": 750},
                    "sample_size": 567
                }
            ]

            if industry:
                benchmarks = [b for b in all_benchmarks if b["industry"].lower() == industry.lower()]
            else:
                benchmarks = all_benchmarks

            return benchmarks

        except Exception as e:
            logger.error(f"Error getting industry benchmarks: {e}")
            raise

    async def delete_old_analyses(self, days_old: int = 90) -> int:
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

    async def get_analyses_by_score_range(
            self,
            user_id: UUID,
            min_score: int = 0,
            max_score: int = 100,
            limit: int = 10
    ) -> List[ATSAnalysis]:
        """Get analyses within a specific score range"""
        try:
            return self.db.query(ATSAnalysis).filter(
                and_(
                    ATSAnalysis.user_id == user_id,
                    ATSAnalysis.overall_ats_score >= min_score,
                    ATSAnalysis.overall_ats_score <= max_score
                )
            ).order_by(desc(ATSAnalysis.overall_ats_score)).limit(limit).all()

        except Exception as e:
            logger.error(f"Error getting analyses by score range: {e}")
            raise

    async def get_top_performing_resumes(
            self,
            user_id: UUID,
            limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get user's top performing resumes based on ATS scores"""
        try:
            # Get latest analysis for each resume
            subquery = self.db.query(
                ATSAnalysis.resume_id,
                func.max(ATSAnalysis.created_at).label('latest_date')
            ).filter(
                ATSAnalysis.user_id == user_id
            ).group_by(ATSAnalysis.resume_id).subquery()

            # Get the actual latest analyses
            latest_analyses = self.db.query(ATSAnalysis).join(
                subquery,
                and_(
                    ATSAnalysis.resume_id == subquery.c.resume_id,
                    ATSAnalysis.created_at == subquery.c.latest_date
                )
            ).order_by(desc(ATSAnalysis.overall_ats_score)).limit(limit).all()

            return [
                {
                    "resume_id": str(analysis.resume_id),
                    "overall_ats_score": analysis.overall_ats_score,
                    "keyword_score": analysis.keyword_score,
                    "formatting_score": analysis.formatting_score,
                    "analysis_date": analysis.created_at,
                    "target_industry": analysis.target_industry
                }
                for analysis in latest_analyses
            ]

        except Exception as e:
            logger.error(f"Error getting top performing resumes: {e}")
            raise

    async def get_improvement_suggestions_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get statistics about improvement suggestions"""
        try:
            analyses = self.db.query(ATSAnalysis).filter(
                ATSAnalysis.user_id == user_id
            ).all()

            if not analyses:
                return {"total_suggestions": 0, "common_issues": []}

            total_suggestions = sum(a.recommendations_count or 0 for a in analyses)
            total_critical_issues = sum(a.critical_issues_count or 0 for a in analyses)

            # Calculate average scores by category
            avg_formatting = sum(a.formatting_score for a in analyses) / len(analyses)
            avg_keyword = sum(a.keyword_score for a in analyses) / len(analyses)
            avg_content = sum(a.content_structure_score for a in analyses) / len(analyses)
            avg_readability = sum(a.readability_score for a in analyses) / len(analyses)

            # Identify common weak areas
            weak_areas = []
            if avg_formatting < 70:
                weak_areas.append("formatting")
            if avg_keyword < 70:
                weak_areas.append("keywords")
            if avg_content < 70:
                weak_areas.append("content_structure")
            if avg_readability < 70:
                weak_areas.append("readability")

            return {
                "total_suggestions": total_suggestions,
                "total_critical_issues": total_critical_issues,
                "average_suggestions_per_analysis": round(total_suggestions / len(analyses), 1),
                "common_weak_areas": weak_areas,
                "category_averages": {
                    "formatting": round(avg_formatting, 1),
                    "keywords": round(avg_keyword, 1),
                    "content_structure": round(avg_content, 1),
                    "readability": round(avg_readability, 1)
                }
            }

        except Exception as e:
            logger.error(f"Error getting improvement suggestions stats: {e}")
            raise