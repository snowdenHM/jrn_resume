from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
import logging

from app.repositories.resume_repository import ResumeRepository
from app.services.validation_service import ValidationService
from app.services.export_service import ExportService
from app.schemas.resume import (
    ResumeCreate, ResumeUpdate, ResumeResponse, ResumeListItem,
    ResumeValidation, ResumePreview, ResumeVersionHistory
)
from app.schemas.response import PaginatedResponse

logger = logging.getLogger(__name__)


class ResumeService:
    """Service layer for resume operations"""

    def __init__(self, db: Session):
        self.repository = ResumeRepository(db)
        self.validation_service = ValidationService()
        self.export_service = ExportService()

    async def create_resume(self, user_id: UUID, resume_data: ResumeCreate) -> ResumeResponse:
        """Create a new resume for user"""
        try:
            logger.info(f"Creating resume for user {user_id}: {resume_data.title}")

            # Validate content
            validation_result = self.validation_service.validate_resume_content(
                resume_data.content.dict()
            )

            if not validation_result.is_valid:
                error_msg = f"Invalid resume content: {', '.join(validation_result.validation_errors)}"
                logger.warning(f"Resume validation failed for user {user_id}: {error_msg}")
                raise ValueError(error_msg)

            # Create resume
            resume = self.repository.create_resume(
                user_id=user_id,
                title=resume_data.title,
                content=resume_data.content.dict(),
                template_id=resume_data.template_id or "professional"
            )

            logger.info(f"Successfully created resume {resume.id} for user {user_id}")
            return ResumeResponse.from_orm(resume)

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creating resume for user {user_id}: {e}")
            raise

    async def get_user_resumes(
            self,
            user_id: UUID,
            page: int = 1,
            size: int = 10,
            is_active: Optional[bool] = None
    ) -> PaginatedResponse[ResumeListItem]:
        """Get paginated list of user's resumes"""
        try:
            logger.info(f"Getting resumes for user {user_id}, page {page}, size {size}")

            # Get resumes
            resumes = self.repository.get_by_user(
                user_id=user_id,
                page=page,
                size=size,
                is_active=is_active
            )

            # Get total count
            total = self.repository.count_by_user(user_id, is_active)

            # Convert to list items with completeness
            resume_items = []
            for resume in resumes:
                completeness = resume.calculate_completeness()

                resume_item = ResumeListItem(
                    id=resume.id,
                    title=resume.title,
                    template_id=resume.template_id,
                    version=resume.version,
                    is_active=resume.is_active,
                    created_at=resume.created_at,
                    updated_at=resume.updated_at,
                    completeness_percentage=completeness['percentage']
                )
                resume_items.append(resume_item)

            return PaginatedResponse.create(
                items=resume_items,
                total=total,
                page=page,
                size=size
            )

        except Exception as e:
            logger.error(f"Error getting resumes for user {user_id}: {e}")
            raise

    async def get_resume(self, resume_id: UUID, user_id: UUID) -> Optional[ResumeResponse]:
        """Get specific resume by ID"""
        try:
            logger.info(f"Getting resume {resume_id} for user {user_id}")

            resume = self.repository.get_by_id_and_user(resume_id, user_id)
            if not resume:
                logger.warning(f"Resume {resume_id} not found for user {user_id}")
                return None

            return ResumeResponse.from_orm(resume)

        except Exception as e:
            logger.error(f"Error getting resume {resume_id} for user {user_id}: {e}")
            raise

    async def update_resume(
            self,
            resume_id: UUID,
            user_id: UUID,
            update_data: ResumeUpdate
    ) -> Optional[ResumeResponse]:
        """Update existing resume"""
        try:
            logger.info(f"Updating resume {resume_id} for user {user_id}")

            # Validate content if provided
            if update_data.content:
                validation_result = self.validation_service.validate_resume_content(
                    update_data.content.dict()
                )

                if not validation_result.is_valid:
                    error_msg = f"Invalid resume content: {', '.join(validation_result.validation_errors)}"
                    logger.warning(f"Resume validation failed: {error_msg}")
                    raise ValueError(error_msg)

            # Prepare update data
            update_dict = {}
            if update_data.title is not None:
                update_dict['title'] = update_data.title
            if update_data.content is not None:
                update_dict['content'] = update_data.content.dict()
            if update_data.template_id is not None:
                update_dict['template_id'] = update_data.template_id

            # Update resume
            resume = self.repository.update_resume(
                resume_id=resume_id,
                user_id=user_id,
                update_data=update_dict
            )

            if not resume:
                logger.warning(f"Resume {resume_id} not found for user {user_id}")
                return None

            logger.info(f"Successfully updated resume {resume_id} for user {user_id}")
            return ResumeResponse.from_orm(resume)

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating resume {resume_id} for user {user_id}: {e}")
            raise

    async def delete_resume(self, resume_id: UUID, user_id: UUID) -> bool:
        """Delete resume"""
        try:
            logger.info(f"Deleting resume {resume_id} for user {user_id}")

            success = self.repository.delete_resume(resume_id, user_id)

            if success:
                logger.info(f"Successfully deleted resume {resume_id} for user {user_id}")
            else:
                logger.warning(f"Resume {resume_id} not found for user {user_id}")

            return success

        except Exception as e:
            logger.error(f"Error deleting resume {resume_id} for user {user_id}: {e}")
            raise

    async def duplicate_resume(
            self,
            resume_id: UUID,
            user_id: UUID,
            new_title: str
    ) -> Optional[ResumeResponse]:
        """Create a copy of existing resume"""
        try:
            logger.info(f"Duplicating resume {resume_id} for user {user_id}")

            duplicated_resume = self.repository.duplicate_resume(
                resume_id=resume_id,
                user_id=user_id,
                new_title=new_title
            )

            if not duplicated_resume:
                logger.warning(f"Resume {resume_id} not found for user {user_id}")
                return None

            logger.info(f"Successfully duplicated resume {resume_id} as {duplicated_resume.id}")
            return ResumeResponse.from_orm(duplicated_resume)

        except Exception as e:
            logger.error(f"Error duplicating resume {resume_id} for user {user_id}: {e}")
            raise

    async def validate_resume(self, resume_id: UUID, user_id: UUID) -> Optional[ResumeValidation]:
        """Validate resume content and return recommendations"""
        try:
            logger.info(f"Validating resume {resume_id} for user {user_id}")

            resume = self.repository.get_by_id_and_user(resume_id, user_id)
            if not resume:
                logger.warning(f"Resume {resume_id} not found for user {user_id}")
                return None

            validation_result = self.validation_service.validate_resume_content(resume.content)

            logger.info(
                f"Resume {resume_id} validation completed: {validation_result.completeness_percentage}% complete")
            return validation_result

        except Exception as e:
            logger.error(f"Error validating resume {resume_id} for user {user_id}: {e}")
            raise

    async def get_resume_preview(self, resume_id: UUID, user_id: UUID) -> Optional[ResumePreview]:
        """Get resume preview with HTML and completeness info"""
        try:
            logger.info(f"Getting preview for resume {resume_id} for user {user_id}")

            resume = self.repository.get_by_id_and_user(resume_id, user_id)
            if not resume:
                logger.warning(f"Resume {resume_id} not found for user {user_id}")
                return None

            # Generate HTML preview (simplified)
            preview_html = self._generate_html_preview(resume.content)

            # Get completeness info
            completeness = resume.calculate_completeness()

            return ResumePreview(
                id=resume.id,
                title=resume.title,
                preview_html=preview_html,
                completeness=completeness
            )

        except Exception as e:
            logger.error(f"Error getting preview for resume {resume_id}: {e}")
            raise

    async def export_resume(
            self,
            resume_id: UUID,
            user_id: UUID,
            export_format: str = "pdf"
    ) -> Optional[Dict[str, Any]]:
        """Export resume to specified format"""
        try:
            logger.info(f"Exporting resume {resume_id} for user {user_id} to {export_format}")

            resume = self.repository.get_by_id_and_user(resume_id, user_id)
            if not resume:
                logger.warning(f"Resume {resume_id} not found for user {user_id}")
                return None

            # Validate export request
            is_valid, error_msg = self.export_service.validate_export_request(
                resume.content, export_format
            )

            if not is_valid:
                logger.warning(f"Export validation failed: {error_msg}")
                raise ValueError(error_msg)

            # Create export job
            export_job = self.export_service.create_export_job(
                resume_content=resume.content,
                title=resume.title,
                export_format=export_format,
                user_id=str(user_id)
            )

            logger.info(f"Created export job {export_job['export_id']} for resume {resume_id}")
            return export_job

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error exporting resume {resume_id}: {e}")
            raise

    async def search_resumes(
            self,
            user_id: UUID,
            search_term: str,
            page: int = 1,
            size: int = 10
    ) -> PaginatedResponse[ResumeListItem]:
        """Search user's resumes"""
        try:
            logger.info(f"Searching resumes for user {user_id} with term: {search_term}")

            resumes = self.repository.search_resumes(
                user_id=user_id,
                search_term=search_term,
                page=page,
                size=size
            )

            # Convert to list items
            resume_items = []
            for resume in resumes:
                completeness = resume.calculate_completeness()

                resume_item = ResumeListItem(
                    id=resume.id,
                    title=resume.title,
                    template_id=resume.template_id,
                    version=resume.version,
                    is_active=resume.is_active,
                    created_at=resume.created_at,
                    updated_at=resume.updated_at,
                    completeness_percentage=completeness['percentage']
                )
                resume_items.append(resume_item)

            # For search, we'll use the actual count as total
            total = len(resumes)

            return PaginatedResponse.create(
                items=resume_items,
                total=total,
                page=page,
                size=size
            )

        except Exception as e:
            logger.error(f"Error searching resumes for user {user_id}: {e}")
            raise

    async def get_user_resume_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get statistics about user's resumes"""
        try:
            logger.info(f"Getting resume statistics for user {user_id}")

            stats = self.repository.get_user_resume_stats(user_id)

            # Add validation statistics for active resumes
            if stats['active_resumes'] > 0:
                active_resumes = self.repository.get_by_user(
                    user_id=user_id,
                    page=1,
                    size=stats['active_resumes'],
                    is_active=True
                )

                total_completeness = 0
                fully_complete_count = 0

                for resume in active_resumes:
                    completeness = resume.calculate_completeness()
                    total_completeness += completeness['percentage']
                    if completeness['percentage'] == 100:
                        fully_complete_count += 1

                stats.update({
                    'average_completeness': round(total_completeness / stats['active_resumes'], 1),
                    'fully_complete_resumes': fully_complete_count
                })
            else:
                stats.update({
                    'average_completeness': 0,
                    'fully_complete_resumes': 0
                })

            return stats

        except Exception as e:
            logger.error(f"Error getting resume stats for user {user_id}: {e}")
            raise

    def _generate_html_preview(self, content: Dict[str, Any]) -> str:
        """Generate HTML preview of resume content"""
        try:
            html_parts = ['<div class="resume-preview">']

            # Personal info
            personal_info = content.get('personal_info', {})
            if personal_info:
                full_name = f"{personal_info.get('first_name', '')} {personal_info.get('last_name', '')}"
                html_parts.append(f'<h1 class="name">{full_name.strip()}</h1>')

                contact_info = []
                if personal_info.get('email'):
                    contact_info.append(personal_info['email'])
                if personal_info.get('phone'):
                    contact_info.append(personal_info['phone'])

                if contact_info:
                    html_parts.append(f'<p class="contact">{" | ".join(contact_info)}</p>')

            # Professional summary
            if content.get('professional_summary'):
                html_parts.append('<h2>Professional Summary</h2>')
                html_parts.append(f'<p>{content["professional_summary"]}</p>')

            # Work experience
            work_exp = content.get('work_experience', [])
            if work_exp:
                html_parts.append('<h2>Work Experience</h2>')
                for job in work_exp:
                    html_parts.append(f'<h3>{job.get("job_title", "")} at {job.get("company", "")}</h3>')

                    dates = f"{job.get('start_date', '')} - {job.get('end_date', 'Present')}"
                    html_parts.append(f'<p class="dates">{dates}</p>')

                    responsibilities = job.get('responsibilities', [])
                    if responsibilities:
                        html_parts.append('<ul>')
                        for resp in responsibilities[:3]:  # Show first 3
                            html_parts.append(f'<li>{resp}</li>')
                        html_parts.append('</ul>')

            # Education
            education = content.get('education', [])
            if education:
                html_parts.append('<h2>Education</h2>')
                for edu in education:
                    html_parts.append(f'<h3>{edu.get("degree", "")} - {edu.get("institution", "")}</h3>')
                    if edu.get('graduation_year'):
                        html_parts.append(f'<p class="dates">{edu["graduation_year"]}</p>')

            # Skills
            skills = content.get('skills', {})
            if skills:
                html_parts.append('<h2>Skills</h2>')
                for category, skill_list in skills.items():
                    if skill_list:
                        category_name = category.replace('_', ' ').title()
                        skills_text = ', '.join(skill_list)
                        html_parts.append(f'<p><strong>{category_name}:</strong> {skills_text}</p>')

            html_parts.append('</div>')

            return ''.join(html_parts)

        except Exception as e:
            logger.error(f"Error generating HTML preview: {e}")
            return '<div class="resume-preview"><p>Preview not available</p></div>'