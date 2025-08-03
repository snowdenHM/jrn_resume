import uuid

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database.connection import Base


class Resume(Base):
    """Resume model for storing user resume data"""

    __tablename__ = "resumes"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign key to user (from main API)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Resume metadata
    title = Column(String(255), nullable=False)
    template_id = Column(String(50), default="professional", nullable=False)

    # Resume content as JSON
    content = Column(JSONB, nullable=False, default={})

    # Version control
    version = Column(Integer, default=1, nullable=False)

    # Status flags
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    sections = relationship("ResumeSection", back_populates="resume", cascade="all, delete-orphan")
    cover_letters = relationship("CoverLetter", back_populates="resume", cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index('idx_resumes_user_active', 'user_id', 'is_active'),
        Index('idx_resumes_created_at', 'created_at'),
        Index('idx_resumes_updated_at', 'updated_at'),
    )

    def __repr__(self):
        return f"<Resume(id={self.id}, title='{self.title}', user_id={self.user_id})>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'title': self.title,
            'template_id': self.template_id,
            'content': self.content,
            'version': self.version,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def personal_info(self):
        """Get personal info from content"""
        return self.content.get('personal_info', {})

    @property
    def work_experience(self):
        """Get work experience from content"""
        return self.content.get('work_experience', [])

    @property
    def education(self):
        """Get education from content"""
        return self.content.get('education', [])

    @property
    def skills(self):
        """Get skills from content"""
        return self.content.get('skills', {})

    def calculate_completeness(self) -> dict:
        """Calculate resume completeness percentage"""
        sections = {
            'personal_info': self.personal_info,
            'professional_summary': self.content.get('professional_summary'),
            'work_experience': self.work_experience,
            'education': self.education,
            'skills': self.skills,
        }

        completed_sections = 0
        total_sections = len(sections)
        missing_sections = []

        for section_name, section_data in sections.items():
            if section_data:
                if isinstance(section_data, list) and len(section_data) > 0:
                    completed_sections += 1
                elif isinstance(section_data, dict) and len(section_data) > 0:
                    completed_sections += 1
                elif isinstance(section_data, str) and section_data.strip():
                    completed_sections += 1
            else:
                missing_sections.append(section_name)

        percentage = int((completed_sections / total_sections) * 100)

        return {
            'percentage': percentage,
            'completed_sections': completed_sections,
            'total_sections': total_sections,
            'missing_sections': missing_sections
        }