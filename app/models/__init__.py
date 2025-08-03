# Fixed app/models/__init__.py - Resolves circular import issues

# Import all models first
from app.models.resume import Resume
from app.models.section import ResumeSection, SectionTemplate
from app.models.ats_analysis import (
    ATSAnalysis,
    ATSScoreHistory,
    ATSBenchmark,
    ATSKeywordTracking,
    ATSAnalysisSession
)
from app.models.cover_letter import CoverLetter, CoverLetterTemplate

# Import relationship after models are defined
from sqlalchemy.orm import relationship


# Set up relationships after all models are imported to avoid circular imports
def setup_relationships():
    """Setup model relationships after all models are loaded"""
    # Resume -> ResumeSection relationship
    if not hasattr(Resume, 'sections'):
        Resume.sections = relationship("ResumeSection", back_populates="resume", cascade="all, delete-orphan")

    # ResumeSection -> Resume relationship
    if not hasattr(ResumeSection, 'resume'):
        ResumeSection.resume = relationship("Resume", back_populates="sections")

    # Resume -> CoverLetter relationship
    if not hasattr(Resume, 'cover_letters'):
        Resume.cover_letters = relationship("CoverLetter", back_populates="resume", cascade="all, delete-orphan")

    # CoverLetter -> Resume relationship
    if not hasattr(CoverLetter, 'resume'):
        CoverLetter.resume = relationship("Resume", back_populates="cover_letters")


# Call setup function
setup_relationships()

__all__ = [
    "Resume",
    "ResumeSection",
    "SectionTemplate",
    "ATSAnalysis",
    "ATSScoreHistory",
    "ATSBenchmark",
    "ATSKeywordTracking",
    "ATSAnalysisSession",
    "CoverLetter",
    "CoverLetterTemplate",
    "setup_relationships"
]