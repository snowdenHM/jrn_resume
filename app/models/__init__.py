# Import all models to ensure they are registered with SQLAlchemy
from app.models.resume import Resume
from app.models.section import ResumeSection, SectionTemplate
from app.models.ats_analysis import (
    ATSAnalysis,
    ATSScoreHistory,
    ATSBenchmark,
    ATSKeywordTracking,
    ATSAnalysisSession
)

# Set up the relationship between Resume and ResumeSection
# This avoids circular import issues
ResumeSection.resume = relationship("Resume", back_populates="sections")

__all__ = [
    "Resume",
    "ResumeSection",
    "SectionTemplate",
    "ATSAnalysis",
    "ATSScoreHistory",
    "ATSBenchmark",
    "ATSKeywordTracking",
    "ATSAnalysisSession"
]