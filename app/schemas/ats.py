from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class PriorityLevel(str, Enum):
    """Priority levels for recommendations"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendationCategory(str, Enum):
    """Categories for ATS recommendations"""
    FORMATTING = "formatting"
    KEYWORDS = "keywords"
    CONTENT = "content"
    READABILITY = "readability"
    JOB_MATCH = "job_match"
    SKILLS = "skills"


class KeywordAnalysis(BaseModel):
    """Keyword analysis results"""
    score: int = Field(..., ge=0, le=100, description="Keyword optimization score")
    total_keywords: int = Field(..., ge=0, description="Total keywords found in resume")
    industry_keywords: List[str] = Field(default=[], description="Industry-specific keywords")
    job_keywords: List[str] = Field(default=[], description="Keywords from job description")
    matched_keywords: List[str] = Field(default=[], description="Keywords that match job requirements")
    missing_keywords: List[str] = Field(default=[], description="Important keywords missing from resume")
    keyword_density: float = Field(..., ge=0, description="Keyword density percentage")
    job_match_percentage: Optional[float] = Field(None, ge=0, le=100,
                                                  description="Percentage match with job description")


class SkillGapAnalysis(BaseModel):
    """Analysis of skill gaps compared to requirements"""
    current_skills: List[str] = Field(..., description="Skills currently listed in resume")
    required_skills: List[str] = Field(..., description="Skills required for target role/industry")
    missing_skills: List[str] = Field(..., description="Skills missing from resume")
    matching_skills: List[str] = Field(..., description="Skills that match requirements")
    critical_missing: List[str] = Field(default=[], description="Critical skills that are missing")
    important_missing: List[str] = Field(default=[], description="Important skills that are missing")
    nice_to_have_missing: List[str] = Field(default=[], description="Nice-to-have skills that are missing")
    skill_match_percentage: float = Field(..., ge=0, le=100, description="Percentage of required skills present")


class ATSRecommendation(BaseModel):
    """Individual ATS improvement recommendation"""
    category: RecommendationCategory = Field(..., description="Category of recommendation")
    priority: PriorityLevel = Field(..., description="Priority level")
    title: str = Field(..., min_length=1, max_length=200, description="Recommendation title")
    description: str = Field(..., min_length=1, max_length=1000, description="Detailed description")
    impact: str = Field(..., description="Expected impact of implementing this recommendation")
    action_items: List[str] = Field(..., min_items=1, description="Specific action items to implement")


class IndustryInsights(BaseModel):
    """Industry-specific insights and benchmarks"""
    industry: str = Field(..., description="Target industry")
    benchmarks: Dict[str, Any] = Field(default={}, description="Industry benchmarks")
    trends: List[str] = Field(default=[], description="Current industry trends")
    recommendations: List[str] = Field(default=[], description="Industry-specific recommendations")


class ATSAnalysisResult(BaseModel):
    """Complete ATS analysis result"""
    overall_ats_score: int = Field(..., ge=0, le=100, description="Overall ATS compatibility score")
    formatting_score: int = Field(..., ge=0, le=100, description="Resume formatting score")
    keyword_score: int = Field(..., ge=0, le=100, description="Keyword optimization score")
    content_structure_score: int = Field(..., ge=0, le=100, description="Content structure and quality score")
    readability_score: int = Field(..., ge=0, le=100, description="Resume readability score")

    keyword_analysis: KeywordAnalysis = Field(..., description="Detailed keyword analysis")
    skill_gaps: SkillGapAnalysis = Field(..., description="Skill gap analysis")
    recommendations: List[ATSRecommendation] = Field(..., description="Prioritized improvement recommendations")
    industry_insights: Dict[str, Any] = Field(default={}, description="Industry-specific insights")

    analysis_timestamp: datetime = Field(..., description="When the analysis was performed")
    job_match_percentage: Optional[float] = Field(None, ge=0, le=100, description="Overall job match percentage")


class ATSAnalysisRequest(BaseModel):
    """Request for ATS analysis"""
    job_description: Optional[str] = Field(None, max_length=10000, description="Job description to analyze against")
    target_industry: Optional[str] = Field(None, max_length=100, description="Target industry for analysis")
    include_skill_gaps: bool = Field(True, description="Whether to include skill gap analysis")
    include_recommendations: bool = Field(True, description="Whether to include improvement recommendations")


class ATSScoreHistory(BaseModel):
    """Historical ATS scores for tracking improvement"""
    resume_id: str = Field(..., description="Resume ID")
    scores: List[Dict[str, Any]] = Field(..., description="Historical scores with timestamps")
    improvement_trend: str = Field(..., description="Overall improvement trend")
    last_analysis_date: datetime = Field(..., description="Date of last analysis")


class ATSComparisonResult(BaseModel):
    """Result of comparing resume against multiple job descriptions"""
    resume_id: str = Field(..., description="Resume ID")
    job_comparisons: List[Dict[str, Any]] = Field(..., description="Comparison results for each job")
    best_match_job: Optional[str] = Field(None, description="Job ID with best match")
    average_match_percentage: float = Field(..., ge=0, le=100, description="Average match across all jobs")
    recommendations_summary: List[str] = Field(..., description="Summary of key recommendations")


class ATSBenchmark(BaseModel):
    """ATS benchmarks for different industries and roles"""
    industry: str = Field(..., description="Industry name")
    role_level: str = Field(..., description="Role level (entry, mid, senior, executive)")
    average_ats_score: int = Field(..., ge=0, le=100, description="Average ATS score for this category")
    top_keywords: List[str] = Field(..., description="Most important keywords for this category")
    recommended_sections: List[str] = Field(..., description="Recommended resume sections")
    optimal_length_words: Dict[str, int] = Field(..., description="Optimal resume length range")


class ATSOptimizationSuggestion(BaseModel):
    """Specific optimization suggestion with before/after examples"""
    section: str = Field(..., description="Resume section to optimize")
    current_text: str = Field(..., description="Current text in resume")
    suggested_text: str = Field(..., description="Suggested improved text")
    improvement_reason: str = Field(..., description="Why this improvement helps ATS scoring")
    keywords_added: List[str] = Field(default=[], description="Keywords that would be added")


class ATSAnalysisConfig(BaseModel):
    """Configuration for ATS analysis"""
    include_job_match: bool = Field(True, description="Include job description matching")
    include_industry_analysis: bool = Field(True, description="Include industry-specific analysis")
    include_skill_gaps: bool = Field(True, description="Include skill gap analysis")
    include_optimization_suggestions: bool = Field(True, description="Include specific text optimization suggestions")
    strictness_level: str = Field("medium", description="Analysis strictness (low, medium, high)")
    focus_areas: List[str] = Field(default=[], description="Specific areas to focus analysis on")