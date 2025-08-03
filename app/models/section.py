from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database.connection import Base


class ResumeSection(Base):
    """
    Resume section model for granular control of resume sections.
    This is optional and provides more detailed control over individual sections.
    """

    __tablename__ = "resume_sections"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign key to resume
    resume_id = Column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Section metadata
    section_type = Column(String(50), nullable=False)  # e.g., 'work_experience', 'education'
    section_title = Column(String(255))  # Optional custom title

    # Section content as JSON
    content = Column(JSONB, nullable=False, default={})

    # Display order
    order_index = Column(Integer, default=0, nullable=False)

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

    # Indexes for performance
    __table_args__ = (
        Index('idx_sections_resume_order', 'resume_id', 'order_index'),
        Index('idx_sections_type', 'section_type'),
    )

    def __repr__(self):
        return f"<ResumeSection(id={self.id}, type='{self.section_type}', resume_id={self.resume_id})>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': str(self.id),
            'resume_id': str(self.resume_id),
            'section_type': self.section_type,
            'section_title': self.section_title,
            'content': self.content,
            'order_index': self.order_index,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SectionTemplate(Base):
    """
    Template for resume sections to provide structure and validation
    """

    __tablename__ = "section_templates"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Template metadata
    section_type = Column(String(50), nullable=False, unique=True)
    display_name = Column(String(255), nullable=False)
    description = Column(String(500))

    # Template structure and validation rules
    schema = Column(JSONB, nullable=False, default={})
    default_content = Column(JSONB, nullable=False, default={})

    # Display configuration
    is_required = Column(Boolean, default=False)
    is_multiple = Column(Boolean, default=False)  # Can have multiple instances
    display_order = Column(Integer, default=0)

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
        return f"<SectionTemplate(type='{self.section_type}', name='{self.display_name}')>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': str(self.id),
            'section_type': self.section_type,
            'display_name': self.display_name,
            'description': self.description,
            'schema': self.schema,
            'default_content': self.default_content,
            'is_required': self.is_required,
            'is_multiple': self.is_multiple,
            'display_order': self.display_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }