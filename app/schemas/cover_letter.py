from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class CoverLetterContent(BaseModel):
    """Cover letter content schema"""
    opening_paragraph: str = Field(..., min_length=10, max_length=1000, description="Opening paragraph")
    body_paragraphs: List[str] = Field(..., min_items=1, max_items=5, description="Body paragraphs")
    closing_paragraph: str = Field(..., min_length=10, max_length=500, description="Closing paragraph")

    # Optional additional content
    signature: Optional[str] = Field(None, max_length=100, description="Signature line")
    postscript: Optional[str] = Field(None, max_length=200, description="P.S. section")

    @validator('body_paragraphs')
    def validate_body_paragraphs(cls, v):
        if not v:
            raise ValueError('At least one body paragraph is required')
        for i, paragraph in enumerate(v):
            if not paragraph.strip():
                raise ValueError(f'Body paragraph {i + 1} cannot be empty')
            if len(paragraph) > 1500:
                raise ValueError(f'Body paragraph {i + 1} is too long (max 1500 characters)')
        return v


class CoverLetterCreate(BaseModel):
    """Schema for creating a new cover letter"""
    title: str = Field(..., min_length=1, max_length=255, description="Cover letter title")
    job_title: Optional[str] = Field(None, max_length=255, description="Job title")
    company_name: Optional[str] = Field(None, max_length=255, description="Company name")
    hiring_manager_name: Optional[str] = Field(None, max_length=255, description="Hiring manager name")
    content: CoverLetterContent
    template_id: Optional[str] = Field("professional", max_length=50, description="Template ID")
    resume_id: Optional[UUID] = Field(None, description="Associated resume ID")


class CoverLetterUpdate(BaseModel):
    """Schema for updating an existing cover letter"""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Cover letter title")
    job_title: Optional[str] = Field(None, max_length=255, description="Job title")
    company_name: Optional[str] = Field(None, max_length=255, description="Company name")
    hiring_manager_name: Optional[str] = Field(None, max_length=255, description="Hiring manager name")
    content: Optional[CoverLetterContent] = Field(None, description="Cover letter content")
    template_id: Optional[str] = Field(None, max_length=50, description="Template ID")
    resume_id: Optional[UUID] = Field(None, description="Associated resume ID")


class CoverLetterResponse(BaseModel):
    """Schema for cover letter response"""
    id: UUID
    user_id: UUID
    resume_id: Optional[UUID]
    title: str
    job_title: Optional[str]
    company_name: Optional[str]
    hiring_manager_name: Optional[str]
    template_id: str
    content: CoverLetterContent
    version: int
    is_active: bool
    is_template: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CoverLetterListItem(BaseModel):
    """Schema for cover letter list items (without full content)"""
    id: UUID
    title: str
    job_title: Optional[str]
    company_name: Optional[str]
    template_id: str
    version: int
    is_active: bool
    is_template: bool
    created_at: datetime
    updated_at: datetime
    completeness_percentage: Optional[int] = None
    word_count: Optional[int] = None

    class Config:
        from_attributes = True


class CoverLetterDuplicate(BaseModel):
    """Schema for duplicating a cover letter"""
    title: str = Field(..., min_length=1, max_length=255, description="New cover letter title")
    job_title: Optional[str] = Field(None, max_length=255, description="New job title")
    company_name: Optional[str] = Field(None, max_length=255, description="New company name")


class CoverLetterValidation(BaseModel):
    """Schema for cover letter validation results"""
    is_valid: bool
    completeness_percentage: int
    validation_errors: List[str] = []
    recommendations: List[str] = []
    word_count: int
    optimal_word_range: Dict[str, int] = Field(default={"min": 250, "max": 400})
    score: Optional[int] = None


class CoverLetterPreview(BaseModel):
    """Schema for cover letter preview"""
    id: UUID
    title: str
    preview_html: str
    completeness: Dict[str, Any]
    word_count: int


class CoverLetterFromResume(BaseModel):
    """Schema for generating cover letter from resume"""
    resume_id: UUID = Field(..., description="Resume ID to base cover letter on")
    job_title: str = Field(..., min_length=1, max_length=255, description="Job title")
    company_name: str = Field(..., min_length=1, max_length=255, description="Company name")
    job_description: Optional[str] = Field(None, max_length=5000, description="Job description for customization")
    hiring_manager_name: Optional[str] = Field(None, max_length=255, description="Hiring manager name")
    template_id: Optional[str] = Field("professional", description="Template to use")
    title: Optional[str] = Field(None, description="Cover letter title")


class CoverLetterAnalysis(BaseModel):
    """Schema for cover letter analysis results"""
    word_count: int
    paragraph_count: int
    sentence_count: int
    reading_level: str
    tone_analysis: Dict[str, Any]
    keyword_density: Dict[str, float]
    suggestions: List[str]
    strengths: List[str]
    areas_for_improvement: List[str]


class CoverLetterTemplate(BaseModel):
    """Schema for cover letter template"""
    template_id: str
    name: str
    description: Optional[str]
    category: str
    is_premium: bool
    preview_content: Dict[str, Any]
    placeholders: Dict[str, str]


class CoverLetterAIRequest(BaseModel):
    """Schema for AI-powered cover letter generation"""
    job_title: str = Field(..., min_length=1, max_length=255)
    company_name: str = Field(..., min_length=1, max_length=255)
    job_description: Optional[str] = Field(None, max_length=5000)
    user_background: Optional[str] = Field(None, max_length=1000, description="Brief user background")
    tone: Optional[str] = Field("professional", description="Tone: professional, enthusiastic, creative")
    key_skills: Optional[List[str]] = Field(None, max_items=10, description="Key skills to highlight")
    resume_id: Optional[UUID] = Field(None, description="Resume to reference")


class CoverLetterOptimization(BaseModel):
    """Schema for cover letter optimization suggestions"""
    current_score: int = Field(..., ge=0, le=100)
    suggestions: List[Dict[str, Any]]
    improved_content: Optional[Dict[str, str]] = None
    before_after_comparison: Optional[Dict[str, Any]] = None