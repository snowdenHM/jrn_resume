import uuid

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Index, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database.connection import Base


class CoverLetter(Base):
    """Cover letter model for storing user cover letter data"""

    __tablename__ = "cover_letters"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign key to user (from main API)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Optional link to resume
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True, index=True)

    # Cover letter metadata
    title = Column(String(255), nullable=False)
    template_id = Column(String(50), default="professional", nullable=False)

    # Job information
    job_title = Column(String(255), nullable=True)
    company_name = Column(String(255), nullable=True)
    hiring_manager_name = Column(String(255), nullable=True)

    # Cover letter content as structured JSON
    content = Column(JSONB, nullable=False, default={})

    # Version control
    version = Column(Integer, default=1, nullable=False)

    # Status flags
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_template = Column(Boolean, default=False, nullable=False)  # Can be used as template

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

    # Relationship to resume
    resume = relationship("Resume", back_populates="cover_letters")

    # Indexes for performance
    __table_args__ = (
        Index('idx_cover_letters_user_active', 'user_id', 'is_active'),
        Index('idx_cover_letters_company', 'company_name'),
        Index('idx_cover_letters_job_title', 'job_title'),
        Index('idx_cover_letters_created_at', 'created_at'),
        Index('idx_cover_letters_updated_at', 'updated_at'),
    )

    def __repr__(self):
        return f"<CoverLetter(id={self.id}, title='{self.title}', user_id={self.user_id})>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'resume_id': str(self.resume_id) if self.resume_id else None,
            'title': self.title,
            'template_id': self.template_id,
            'job_title': self.job_title,
            'company_name': self.company_name,
            'hiring_manager_name': self.hiring_manager_name,
            'content': self.content,
            'version': self.version,
            'is_active': self.is_active,
            'is_template': self.is_template,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def opening_paragraph(self):
        """Get opening paragraph from content"""
        return self.content.get('opening_paragraph', '')

    @property
    def body_paragraphs(self):
        """Get body paragraphs from content"""
        return self.content.get('body_paragraphs', [])

    @property
    def closing_paragraph(self):
        """Get closing paragraph from content"""
        return self.content.get('closing_paragraph', '')

    def calculate_completeness(self) -> dict:
        """Calculate cover letter completeness percentage"""
        sections = {
            'job_information': bool(self.job_title and self.company_name),
            'opening_paragraph': bool(self.opening_paragraph.strip()),
            'body_paragraphs': bool(self.body_paragraphs and any(p.strip() for p in self.body_paragraphs)),
            'closing_paragraph': bool(self.closing_paragraph.strip()),
            'personal_touch': bool(self.hiring_manager_name),
        }

        completed_sections = sum(1 for completed in sections.values() if completed)
        total_sections = len(sections)
        percentage = int((completed_sections / total_sections) * 100)

        missing_sections = [name for name, completed in sections.items() if not completed]

        return {
            'percentage': percentage,
            'completed_sections': completed_sections,
            'total_sections': total_sections,
            'missing_sections': missing_sections,
            'section_details': sections
        }

    def get_word_count(self) -> int:
        """Calculate word count of cover letter content"""
        try:
            word_count = 0

            # Count opening paragraph
            if self.opening_paragraph:
                word_count += len(self.opening_paragraph.split())

            # Count body paragraphs
            for paragraph in self.body_paragraphs:
                if paragraph:
                    word_count += len(paragraph.split())

            # Count closing paragraph
            if self.closing_paragraph:
                word_count += len(self.closing_paragraph.split())

            return word_count
        except Exception:
            return 0


class CoverLetterTemplate(Base):
    """Template for cover letters to provide structure and examples"""

    __tablename__ = "cover_letter_templates"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Template metadata
    template_id = Column(String(50), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100), default="general")  # general, technology, healthcare, etc.

    # Template content structure
    default_content = Column(JSONB, nullable=False, default={})
    placeholders = Column(JSONB, default={})  # Placeholder text and variables

    # Styling and formatting
    styling = Column(JSONB, default={})

    # Template configuration
    is_premium = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)

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

    def __repr__(self):
        return f"<CoverLetterTemplate(id='{self.template_id}', name='{self.name}')>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': str(self.id),
            'template_id': self.template_id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'default_content': self.default_content,
            'placeholders': self.placeholders,
            'styling': self.styling,
            'is_premium': self.is_premium,
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }