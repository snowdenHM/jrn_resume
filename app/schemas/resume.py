from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from uuid import UUID
import re


class PersonalInfo(BaseModel):
    """Personal information schema"""
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    email: EmailStr = Field(..., description="Email address")
    phone: str = Field(..., min_length=10, max_length=20, description="Phone number")
    address: Optional[str] = Field(None, max_length=500, description="Address")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    portfolio_url: Optional[str] = Field(None, description="Portfolio website URL")
    github_url: Optional[str] = Field(None, description="GitHub profile URL")

    @validator('phone')
    def validate_phone(cls, v):
        # Remove all non-digits for validation
        digits_only = re.sub(r'\D', '', v)
        if len(digits_only) < 10:
            raise ValueError('Phone number must contain at least 10 digits')
        return v

    @validator('linkedin_url', 'portfolio_url', 'github_url')
    def validate_urls(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v


class WorkExperience(BaseModel):
    """Work experience schema"""
    job_title: str = Field(..., min_length=1, max_length=200, description="Job title")
    company: str = Field(..., min_length=1, max_length=200, description="Company name")
    start_date: str = Field(..., regex=r'^\d{4}-\d{2}$', description="Start date (YYYY-MM)")
    end_date: Optional[str] = Field(None, regex=r'^\d{4}-\d{2}$', description="End date (YYYY-MM) or null for current")
    location: Optional[str] = Field(None, max_length=200, description="Job location")
    responsibilities: List[str] = Field(..., min_items=1, max_items=10, description="Job responsibilities")
    is_current: Optional[bool] = Field(False, description="Is this the current job")

    @validator('responsibilities')
    def validate_responsibilities(cls, v):
        if not v:
            raise ValueError('At least one responsibility is required')
        for resp in v:
            if not resp.strip():
                raise ValueError('Responsibilities cannot be empty')
        return v

    @validator('end_date')
    def validate_end_date(cls, v, values):
        if v and 'start_date' in values:
            if v <= values['start_date']:
                raise ValueError('End date must be after start date')
        return v


class Education(BaseModel):
    """Education schema"""
    degree: str = Field(..., min_length=1, max_length=200, description="Degree name")
    institution: str = Field(..., min_length=1, max_length=200, description="Institution name")
    graduation_year: str = Field(..., regex=r'^\d{4}$', description="Graduation year (YYYY)")
    gpa: Optional[float] = Field(None, ge=0.0, le=4.0, description="GPA (0.0-4.0)")
    location: Optional[str] = Field(None, max_length=200, description="Institution location")
    field_of_study: Optional[str] = Field(None, max_length=200, description="Field of study")
    honors: Optional[str] = Field(None, max_length=500, description="Honors or achievements")


class Certification(BaseModel):
    """Certification schema"""
    name: str = Field(..., min_length=1, max_length=200, description="Certification name")
    issuer: str = Field(..., min_length=1, max_length=200, description="Issuing organization")
    issue_date: str = Field(..., regex=r'^\d{4}-\d{2}$', description="Issue date (YYYY-MM)")
    expiry_date: Optional[str] = Field(None, regex=r'^\d{4}-\d{2}$', description="Expiry date (YYYY-MM)")
    credential_id: Optional[str] = Field(None, max_length=100, description="Credential ID")
    credential_url: Optional[str] = Field(None, description="Credential verification URL")


class Project(BaseModel):
    """Project schema"""
    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: str = Field(..., min_length=10, max_length=1000, description="Project description")
    technologies: List[str] = Field(..., min_items=1, max_items=20, description="Technologies used")
    url: Optional[str] = Field(None, description="Project URL")
    github_url: Optional[str] = Field(None, description="GitHub repository URL")
    start_date: Optional[str] = Field(None, regex=r'^\d{4}-\d{2}$', description="Start date (YYYY-MM)")
    end_date: Optional[str] = Field(None, regex=r'^\d{4}-\d{2}$', description="End date (YYYY-MM)")


class Language(BaseModel):
    """Language schema"""
    language: str = Field(..., min_length=1, max_length=100, description="Language name")
    proficiency: str = Field(..., regex=r'^(Basic|Intermediate|Advanced|Native|Fluent)$',
                             description="Proficiency level")


class Skills(BaseModel):
    """Skills schema"""
    technical: List[str] = Field(default=[], max_items=50, description="Technical skills")
    soft: List[str] = Field(default=[], max_items=20, description="Soft skills")
    languages: List[str] = Field(default=[], max_items=20, description="Programming languages")
    tools: List[str] = Field(default=[], max_items=30, description="Tools and software")


class ResumeContent(BaseModel):
    """Complete resume content schema"""
    personal_info: PersonalInfo
    professional_summary: Optional[str] = Field(None, max_length=1000, description="Professional summary")
    work_experience: List[WorkExperience] = Field(default=[], description="Work experience list")
    education: List[Education] = Field(default=[], description="Education list")
    skills: Skills = Field(default_factory=Skills, description="Skills section")
    certifications: List[Certification] = Field(default=[], description="Certifications list")
    projects: List[Project] = Field(default=[], description="Projects list")
    languages: List[Language] = Field(default=[], description="Languages list")
    additional_sections: Dict[str, Any] = Field(default={}, description="Additional custom sections")


class ResumeCreate(BaseModel):
    """Schema for creating a new resume"""
    title: str = Field(..., min_length=1, max_length=255, description="Resume title")
    content: ResumeContent
    template_id: Optional[str] = Field("professional", max_length=50, description="Template ID")


class ResumeUpdate(BaseModel):
    """Schema for updating an existing resume"""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Resume title")
    content: Optional[ResumeContent] = Field(None, description="Resume content")
    template_id: Optional[str] = Field(None, max_length=50, description="Template ID")


class ResumeResponse(BaseModel):
    """Schema for resume response"""
    id: UUID
    user_id: UUID
    title: str
    template_id: str
    content: ResumeContent
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResumeListItem(BaseModel):
    """Schema for resume list items (without full content)"""
    id: UUID
    title: str
    template_id: str
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    completeness_percentage: Optional[int] = None

    class Config:
        from_attributes = True


class ResumeDuplicate(BaseModel):
    """Schema for duplicating a resume"""
    title: str = Field(..., min_length=1, max_length=255, description="New resume title")


class ResumeValidation(BaseModel):
    """Schema for resume validation results"""
    is_valid: bool
    completeness_percentage: int
    validation_errors: List[str] = []
    recommendations: List[str] = []
    missing_required_fields: List[str] = []
    score: Optional[int] = None


class ResumePreview(BaseModel):
    """Schema for resume preview"""
    id: UUID
    title: str
    preview_html: str
    completeness: Dict[str, Any]


class ResumeVersion(BaseModel):
    """Schema for resume version information"""
    version: int
    created_at: datetime
    changes: Optional[str] = None


class ResumeVersionHistory(BaseModel):
    """Schema for resume version history"""
    current_version: int
    versions: List[ResumeVersion]