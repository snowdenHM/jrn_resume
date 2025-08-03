from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database.connection import Base


class ATSAnalysis(Base):
    """Model for storing ATS analysis results"""

    __tablename__ = "ats_analyses"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign keys
    resume_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # ATS Scores
    overall_ats_score = Column(Integer, nullable=False)
    formatting_score = Column(Integer, nullable=False)
    keyword_score = Column(Integer, nullable=False)
    content_structure_score = Column(Integer, nullable=False)
    readability_score = Column(Integer, nullable=False)

    # Job matching
    job_match_percentage = Column(Float, nullable=True)
    target_industry = Column(String(100), nullable=True)

    # Analysis metadata
    analysis_data = Column(JSONB, nullable=False, default={})
    recommendations_count = Column(Integer, default=0)
    critical_issues_count = Column(Integer, default=0)

    # Timestamps
    analysis_timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Indexes for performance
    __table_args__ = (
        Index('idx_ats_user_resume', 'user_id', 'resume_id'),
        Index('idx_ats_score_range', 'overall_ats_score'),
        Index('idx_ats_analysis_date', 'analysis_timestamp'),
        Index('idx_ats_industry', 'target_industry'),
    )

    def __repr__(self):
        return f"<ATSAnalysis(id={self.id}, resume_id={self.resume_id}, score={self.overall_ats_score})>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': str(self.id),
            'resume_id': str(self.resume_id),
            'user_id': str(self.user_id),
            'overall_ats_score': self.overall_ats_score,
            'formatting_score': self.formatting_score,
            'keyword_score': self.keyword_score,
            'content_structure_score': self.content_structure_score,
            'readability_score': self.readability_score,
            'job_match_percentage': self.job_match_percentage,
            'target_industry': self.target_industry,
            'analysis_data': self.analysis_data,
            'recommendations_count': self.recommendations_count,
            'critical_issues_count': self.critical_issues_count,
            'analysis_timestamp': self.analysis_timestamp.isoformat() if self.analysis_timestamp else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ATSScoreHistory(Base):
    """Model for tracking ATS score history over time"""

    __tablename__ = "ats_score_history"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Resume reference
    resume_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)

    # Score history data
    scores_json = Column(Text, nullable=False, default='[]')  # JSON array of score entries
    last_analysis_date = Column(DateTime(timezone=True), nullable=False)
    total_analyses = Column(Integer, default=0, nullable=False)

    # Trend analysis
    improvement_trend = Column(String(20), default='neutral')  # improving, declining, stable, neutral
    best_score = Column(Integer, default=0)
    worst_score = Column(Integer, default=0)
    average_score = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ATSScoreHistory(resume_id={self.resume_id}, total_analyses={self.total_analyses})>"


class ATSBenchmark(Base):
    """Model for storing ATS benchmarks by industry and role level"""

    __tablename__ = "ats_benchmarks"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Benchmark criteria
    industry = Column(String(100), nullable=False, index=True)
    role_level = Column(String(50), nullable=False, index=True)  # entry, mid, senior, executive
    job_category = Column(String(100), nullable=True)

    # Benchmark scores
    average_ats_score = Column(Integer, nullable=False)
    percentile_25 = Column(Integer, nullable=False)
    percentile_50 = Column(Integer, nullable=False)
    percentile_75 = Column(Integer, nullable=False)
    percentile_90 = Column(Integer, nullable=False)

    # Benchmark data
    top_keywords = Column(JSONB, default=[])
    recommended_sections = Column(JSONB, default=[])
    optimal_length_range = Column(JSONB, default={})
    common_mistakes = Column(JSONB, default=[])

    # Sample size and confidence
    sample_size = Column(Integer, default=0)
    last_updated = Column(DateTime(timezone=True), nullable=False)
    confidence_level = Column(Float, default=0.95)

    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_benchmark_industry_role', 'industry', 'role_level'),
        Index('idx_benchmark_active', 'is_active'),
    )

    def __repr__(self):
        return f"<ATSBenchmark(industry={self.industry}, role_level={self.role_level}, avg_score={self.average_ats_score})>"


class ATSKeywordTracking(Base):
    """Model for tracking keyword performance and trends"""

    __tablename__ = "ats_keyword_tracking"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Keyword info
    keyword = Column(String(200), nullable=False, index=True)
    industry = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False)  # technical, soft_skill, certification, etc.

    # Tracking metrics
    frequency_score = Column(Integer, default=0)  # How often it appears in job postings
    importance_weight = Column(Float, default=1.0)  # Relative importance (1.0 = normal)
    trend_direction = Column(String(20), default='stable')  # rising, falling, stable

    # Usage statistics
    resumes_containing = Column(Integer, default=0)
    job_postings_containing = Column(Integer, default=0)
    success_correlation = Column(Float, default=0.0)  # Correlation with high ATS scores

    # Metadata
    is_active = Column(Boolean, default=True)
    last_analyzed = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_keyword_industry_category', 'industry', 'category'),
        Index('idx_keyword_frequency', 'frequency_score'),
        Index('idx_keyword_importance', 'importance_weight'),
    )

    def __repr__(self):
        return f"<ATSKeywordTracking(keyword={self.keyword}, industry={self.industry}, frequency={self.frequency_score})>"


class ATSAnalysisSession(Base):
    """Model for tracking analysis sessions and user interactions"""

    __tablename__ = "ats_analysis_sessions"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Session info
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    session_token = Column(String(255), nullable=False, unique=True)

    # Analysis context
    resumes_analyzed = Column(JSONB, default=[])  # List of resume IDs
    job_descriptions_used = Column(Integer, default=0)
    industries_analyzed = Column(JSONB, default=[])

    # Session metrics
    total_analyses = Column(Integer, default=0)
    recommendations_generated = Column(Integer, default=0)
    optimizations_applied = Column(Integer, default=0)

    # Session status
    is_active = Column(Boolean, default=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<ATSAnalysisSession(user_id={self.user_id}, total_analyses={self.total_analyses})>"