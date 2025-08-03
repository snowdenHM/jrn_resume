from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
import logging
import re

from app.repositories.cover_letter_repository import CoverLetterRepository
from app.services.cover_letter_validation_service import CoverLetterValidationService
from app.services.export_service import ExportService
from app.services.resume_service import ResumeService
from app.schemas.cover_letter import (
    CoverLetterCreate, CoverLetterUpdate, CoverLetterResponse, CoverLetterListItem,
    CoverLetterValidation, CoverLetterPreview, CoverLetterFromResume, CoverLetterAIRequest
)
from app.schemas.response import PaginatedResponse

logger = logging.getLogger(__name__)


class CoverLetterService:
    """Service layer for cover letter operations"""

    def __init__(self, db: Session):
        self.repository = CoverLetterRepository(db)
        self.validation_service = CoverLetterValidationService()
        self.export_service = ExportService()
        self.resume_service = ResumeService(db)
        self.db = db

    async def create_cover_letter(self, user_id: UUID, cover_letter_data: CoverLetterCreate) -> CoverLetterResponse:
        """Create a new cover letter for user"""
        try:
            logger.info(f"Creating cover letter for user {user_id}: {cover_letter_data.title}")

            # Validate resume association if provided
            if cover_letter_data.resume_id:
                resume = await self.resume_service.get_resume(cover_letter_data.resume_id, user_id)
                if not resume:
                    raise ValueError(f"Resume {cover_letter_data.resume_id} not found")

            # Validate content
            validation_result = self.validation_service.validate_cover_letter_content(
                cover_letter_data.content.dict()
            )

            if not validation_result.is_valid:
                error_msg = f"Invalid cover letter content: {', '.join(validation_result.validation_errors)}"
                logger.warning(f"Cover letter validation failed for user {user_id}: {error_msg}")
                raise ValueError(error_msg)

            # Create cover letter
            cover_letter = self.repository.create_cover_letter(
                user_id=user_id,
                title=cover_letter_data.title,
                job_title=cover_letter_data.job_title,
                company_name=cover_letter_data.company_name,
                hiring_manager_name=cover_letter_data.hiring_manager_name,
                content=cover_letter_data.content.dict(),
                template_id=cover_letter_data.template_id or "professional",
                resume_id=cover_letter_data.resume_id
            )

            logger.info(f"Successfully created cover letter {cover_letter.id} for user {user_id}")
            return self._convert_to_response(cover_letter)

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creating cover letter for user {user_id}: {e}")
            raise

    async def get_user_cover_letters(
            self,
            user_id: UUID,
            page: int = 1,
            size: int = 10,
            is_active: Optional[bool] = None,
            company_name: Optional[str] = None
    ) -> PaginatedResponse[CoverLetterListItem]:
        """Get paginated list of user's cover letters"""
        try:
            logger.info(f"Getting cover letters for user {user_id}, page {page}, size {size}")

            # Get cover letters
            cover_letters = self.repository.get_by_user(
                user_id=user_id,
                page=page,
                size=size,
                is_active=is_active,
                company_name=company_name
            )

            # Get total count
            total = self.repository.count_by_user(user_id, is_active, company_name)

            # Convert to list items with completeness and word count
            cover_letter_items = []
            for cover_letter in cover_letters:
                try:
                    completeness = cover_letter.calculate_completeness()
                    word_count = cover_letter.get_word_count()

                    cover_letter_item = CoverLetterListItem(
                        id=cover_letter.id,
                        title=cover_letter.title,
                        job_title=cover_letter.job_title,
                        company_name=cover_letter.company_name,
                        template_id=cover_letter.template_id,
                        version=cover_letter.version,
                        is_active=cover_letter.is_active,
                        is_template=cover_letter.is_template,
                        created_at=cover_letter.created_at,
                        updated_at=cover_letter.updated_at,
                        completeness_percentage=completeness['percentage'],
                        word_count=word_count
                    )
                    cover_letter_items.append(cover_letter_item)
                except Exception as e:
                    logger.error(f"Error processing cover letter {cover_letter.id}: {e}")

            return PaginatedResponse.create(
                items=cover_letter_items,
                total=total,
                page=page,
                size=size
            )

        except Exception as e:
            logger.error(f"Error getting cover letters for user {user_id}: {e}")
            raise

    async def get_cover_letter(self, cover_letter_id: UUID, user_id: UUID) -> Optional[CoverLetterResponse]:
        """Get specific cover letter by ID"""
        try:
            logger.info(f"Getting cover letter {cover_letter_id} for user {user_id}")

            cover_letter = self.repository.get_by_id_and_user(cover_letter_id, user_id)
            if not cover_letter:
                logger.warning(f"Cover letter {cover_letter_id} not found for user {user_id}")
                return None

            return self._convert_to_response(cover_letter)

        except Exception as e:
            logger.error(f"Error getting cover letter {cover_letter_id} for user {user_id}: {e}")
            raise

    async def update_cover_letter(
            self,
            cover_letter_id: UUID,
            user_id: UUID,
            update_data: CoverLetterUpdate
    ) -> Optional[CoverLetterResponse]:
        """Update existing cover letter"""
        try:
            logger.info(f"Updating cover letter {cover_letter_id} for user {user_id}")

            # Validate resume association if provided
            if update_data.resume_id:
                resume = await self.resume_service.get_resume(update_data.resume_id, user_id)
                if not resume:
                    raise ValueError(f"Resume {update_data.resume_id} not found")

            # Validate content if provided
            if update_data.content:
                validation_result = self.validation_service.validate_cover_letter_content(
                    update_data.content.dict()
                )

                if not validation_result.is_valid:
                    error_msg = f"Invalid cover letter content: {', '.join(validation_result.validation_errors)}"
                    logger.warning(f"Cover letter validation failed: {error_msg}")
                    raise ValueError(error_msg)

            # Prepare update data
            update_dict = {}
            for field in ['title', 'job_title', 'company_name', 'hiring_manager_name', 'template_id', 'resume_id']:
                value = getattr(update_data, field, None)
                if value is not None:
                    update_dict[field] = value

            if update_data.content is not None:
                update_dict['content'] = update_data.content.dict()

            # Update cover letter
            cover_letter = self.repository.update_cover_letter(
                cover_letter_id=cover_letter_id,
                user_id=user_id,
                update_data=update_dict
            )

            if not cover_letter:
                logger.warning(f"Cover letter {cover_letter_id} not found for user {user_id}")
                return None

            logger.info(f"Successfully updated cover letter {cover_letter_id} for user {user_id}")
            return self._convert_to_response(cover_letter)

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating cover letter {cover_letter_id} for user {user_id}: {e}")
            raise

    async def delete_cover_letter(self, cover_letter_id: UUID, user_id: UUID) -> bool:
        """Delete cover letter"""
        try:
            logger.info(f"Deleting cover letter {cover_letter_id} for user {user_id}")

            success = self.repository.delete_cover_letter(cover_letter_id, user_id)

            if success:
                logger.info(f"Successfully deleted cover letter {cover_letter_id} for user {user_id}")
            else:
                logger.warning(f"Cover letter {cover_letter_id} not found for user {user_id}")

            return success

        except Exception as e:
            logger.error(f"Error deleting cover letter {cover_letter_id} for user {user_id}: {e}")
            raise

    async def generate_from_resume(
            self,
            user_id: UUID,
            request_data: CoverLetterFromResume
    ) -> CoverLetterResponse:
        """Generate cover letter from resume data"""
        try:
            logger.info(f"Generating cover letter from resume {request_data.resume_id} for user {user_id}")

            # Get resume
            resume = await self.resume_service.get_resume(request_data.resume_id, user_id)
            if not resume:
                raise ValueError(f"Resume {request_data.resume_id} not found")

            # Extract relevant information from resume
            personal_info = resume.content.personal_info
            work_experience = resume.content.work_experience
            skills = resume.content.skills
            professional_summary = resume.content.professional_summary

            # Generate AI-powered content
            ai_service = CoverLetterAIService()
            generated_content = await ai_service.generate_from_resume(
                resume_data={
                    "personal_info": personal_info.dict(),
                    "work_experience": [exp.dict() for exp in work_experience],
                    "skills": skills.dict(),
                    "professional_summary": professional_summary
                },
                job_title=request_data.job_title,
                company_name=request_data.company_name,
                job_description=request_data.job_description,
                hiring_manager_name=request_data.hiring_manager_name
            )

            # Create cover letter
            title = request_data.title or f"Cover Letter - {request_data.job_title} at {request_data.company_name}"

            cover_letter_data = CoverLetterCreate(
                title=title,
                job_title=request_data.job_title,
                company_name=request_data.company_name,
                hiring_manager_name=request_data.hiring_manager_name,
                content=generated_content,
                template_id=request_data.template_id,
                resume_id=request_data.resume_id
            )

            return await self.create_cover_letter(user_id, cover_letter_data)

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error generating cover letter from resume: {e}")
            raise

    async def generate_ai_cover_letter(
            self,
            user_id: UUID,
            request_data: CoverLetterAIRequest
    ) -> CoverLetterResponse:
        """Generate cover letter using AI"""
        try:
            logger.info(f"Generating AI cover letter for user {user_id}, job: {request_data.job_title}")

            # Get resume data if provided
            resume_data = None
            if request_data.resume_id:
                resume = await self.resume_service.get_resume(request_data.resume_id, user_id)
                if resume:
                    resume_data = {
                        "personal_info": resume.content.personal_info.dict(),
                        "work_experience": [exp.dict() for exp in resume.content.work_experience],
                        "skills": resume.content.skills.dict(),
                        "professional_summary": resume.content.professional_summary
                    }

            # Generate AI content
            ai_service = CoverLetterAIService()
            generated_content = await ai_service.generate_ai_content(
                job_title=request_data.job_title,
                company_name=request_data.company_name,
                job_description=request_data.job_description,
                user_background=request_data.user_background,
                tone=request_data.tone,
                key_skills=request_data.key_skills,
                resume_data=resume_data
            )

            # Create cover letter
            title = f"AI Generated - {request_data.job_title} at {request_data.company_name}"

            cover_letter_data = CoverLetterCreate(
                title=title,
                job_title=request_data.job_title,
                company_name=request_data.company_name,
                content=generated_content,
                template_id="professional",
                resume_id=request_data.resume_id
            )

            return await self.create_cover_letter(user_id, cover_letter_data)

        except Exception as e:
            logger.error(f"Error generating AI cover letter: {e}")
            raise

    async def validate_cover_letter(self, cover_letter_id: UUID, user_id: UUID) -> Optional[CoverLetterValidation]:
        """Validate cover letter content and return recommendations"""
        try:
            logger.info(f"Validating cover letter {cover_letter_id} for user {user_id}")

            cover_letter = self.repository.get_by_id_and_user(cover_letter_id, user_id)
            if not cover_letter:
                logger.warning(f"Cover letter {cover_letter_id} not found for user {user_id}")
                return None

            validation_result = self.validation_service.validate_cover_letter_content(cover_letter.content)
            validation_result.word_count = cover_letter.get_word_count()

            logger.info(
                f"Cover letter {cover_letter_id} validation completed: {validation_result.completeness_percentage}% complete")
            return validation_result

        except Exception as e:
            logger.error(f"Error validating cover letter {cover_letter_id} for user {user_id}: {e}")
            raise

    async def get_cover_letter_preview(self, cover_letter_id: UUID, user_id: UUID) -> Optional[CoverLetterPreview]:
        """Get cover letter preview with HTML and completeness info"""
        try:
            logger.info(f"Getting preview for cover letter {cover_letter_id} for user {user_id}")

            cover_letter = self.repository.get_by_id_and_user(cover_letter_id, user_id)
            if not cover_letter:
                logger.warning(f"Cover letter {cover_letter_id} not found for user {user_id}")
                return None

            # Generate HTML preview
            preview_html = self._generate_html_preview(cover_letter)

            # Get completeness info
            completeness = cover_letter.calculate_completeness()
            word_count = cover_letter.get_word_count()

            return CoverLetterPreview(
                id=cover_letter.id,
                title=cover_letter.title,
                preview_html=preview_html,
                completeness=completeness,
                word_count=word_count
            )

        except Exception as e:
            logger.error(f"Error getting preview for cover letter {cover_letter_id}: {e}")
            raise

    def _convert_to_response(self, cover_letter) -> CoverLetterResponse:
        """Convert cover letter model to response schema"""
        try:
            from app.schemas.cover_letter import CoverLetterContent

            # Parse content into structured format
            content_dict = cover_letter.content

            # Create CoverLetterContent object with proper validation
            cover_letter_content = CoverLetterContent(
                opening_paragraph=content_dict.get('opening_paragraph', ''),
                body_paragraphs=content_dict.get('body_paragraphs', []),
                closing_paragraph=content_dict.get('closing_paragraph', ''),
                signature=content_dict.get('signature'),
                postscript=content_dict.get('postscript')
            )

            return CoverLetterResponse(
                id=cover_letter.id,
                user_id=cover_letter.user_id,
                resume_id=cover_letter.resume_id,
                title=cover_letter.title,
                job_title=cover_letter.job_title,
                company_name=cover_letter.company_name,
                hiring_manager_name=cover_letter.hiring_manager_name,
                template_id=cover_letter.template_id,
                content=cover_letter_content,
                version=cover_letter.version,
                is_active=cover_letter.is_active,
                is_template=cover_letter.is_template,
                created_at=cover_letter.created_at,
                updated_at=cover_letter.updated_at
            )
        except Exception as e:
            logger.error(f"Error converting cover letter to response: {e}")
            raise

    def _generate_html_preview(self, cover_letter) -> str:
        """Generate HTML preview of cover letter content"""
        try:
            html_parts = [
                '<div class="cover-letter-preview" style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6;">']

            # Header with job information
            if cover_letter.job_title or cover_letter.company_name:
                html_parts.append('<div class="header" style="margin-bottom: 30px; text-align: center;">')
                if cover_letter.job_title:
                    html_parts.append(
                        f'<h2 style="color: #2E4057; margin-bottom: 5px;">Application for {cover_letter.job_title}</h2>')
                if cover_letter.company_name:
                    html_parts.append(f'<h3 style="color: #666; margin-top: 0;">at {cover_letter.company_name}</h3>')
                html_parts.append('</div>')

            # Date and recipient
            html_parts.append('<div class="date-recipient" style="margin-bottom: 30px;">')
            html_parts.append(
                f'<p style="margin-bottom: 10px;"><strong>Date:</strong> {cover_letter.created_at.strftime("%B %d, %Y")}</p>')

            if cover_letter.hiring_manager_name:
                html_parts.append(
                    f'<p style="margin-bottom: 5px;"><strong>Dear {cover_letter.hiring_manager_name},</strong></p>')
            elif cover_letter.company_name:
                html_parts.append(
                    f'<p style="margin-bottom: 5px;"><strong>Dear {cover_letter.company_name} Hiring Team,</strong></p>')
            else:
                html_parts.append('<p style="margin-bottom: 5px;"><strong>Dear Hiring Manager,</strong></p>')
            html_parts.append('</div>')

            # Opening paragraph
            opening = cover_letter.content.get('opening_paragraph', '')
            if opening:
                html_parts.append(f'<p style="margin-bottom: 20px; text-align: justify;">{opening}</p>')

            # Body paragraphs
            body_paragraphs = cover_letter.content.get('body_paragraphs', [])
            for paragraph in body_paragraphs:
                if paragraph.strip():
                    html_parts.append(f'<p style="margin-bottom: 20px; text-align: justify;">{paragraph}</p>')

            # Closing paragraph
            closing = cover_letter.content.get('closing_paragraph', '')
            if closing:
                html_parts.append(f'<p style="margin-bottom: 20px; text-align: justify;">{closing}</p>')

            # Signature
            html_parts.append('<div class="signature" style="margin-top: 30px;">')
            html_parts.append('<p style="margin-bottom: 5px;">Sincerely,</p>')

            signature = cover_letter.content.get('signature')
            if signature:
                html_parts.append(f'<p style="margin-bottom: 0; font-weight: bold;">{signature}</p>')
            else:
                html_parts.append('<p style="margin-bottom: 0; font-weight: bold;">[Your Name]</p>')
            html_parts.append('</div>')

            # Postscript
            postscript = cover_letter.content.get('postscript')
            if postscript:
                html_parts.append(
                    f'<div class="postscript" style="margin-top: 20px;"><p><strong>P.S.</strong> {postscript}</p></div>')

            html_parts.append('</div>')

            return ''.join(html_parts)

        except Exception as e:
            logger.error(f"Error generating HTML preview: {e}")
            return f'<div class="cover-letter-preview" style="padding: 20px; color: #666;"><p>Preview generation failed: {str(e)}</p></div>'


# AI Service for Cover Letter Generation
class CoverLetterAIService:
    """AI-powered cover letter generation service"""

    def __init__(self):
        self.templates = self._load_ai_templates()

    def _load_ai_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load AI generation templates"""
        return {
            "professional": {
                "opening_templates": [
                    "I am writing to express my strong interest in the {job_title} position at {company_name}. With my background in {relevant_field} and {years_experience} years of experience, I am confident I would be a valuable addition to your team.",
                    "I am excited to apply for the {job_title} role at {company_name}. My experience in {relevant_field} and passion for {industry} make me an ideal candidate for this position.",
                    "Having followed {company_name}'s work in {industry}, I am thrilled to apply for the {job_title} position. My {key_qualification} and proven track record in {relevant_area} align perfectly with your requirements."
                ],
                "body_templates": [
                    "In my previous role as {previous_role}, I successfully {achievement}. This experience has equipped me with {relevant_skills} that directly apply to the {job_title} position.",
                    "My background includes {relevant_experience}, where I {specific_accomplishment}. I am particularly drawn to {company_name} because of {company_reason}.",
                    "Throughout my career, I have developed expertise in {skill_areas}. At {previous_company}, I {quantifiable_achievement}, which demonstrates my ability to {relevant_capability}."
                ],
                "closing_templates": [
                    "I would welcome the opportunity to discuss how my {key_strengths} can contribute to {company_name}'s continued success. Thank you for considering my application.",
                    "I am eager to bring my {expertise} to {company_name} and contribute to {specific_goal}. I look forward to hearing from you soon.",
                    "Thank you for your time and consideration. I would be delighted to discuss how my experience in {relevant_area} can benefit your team."
                ]
            },
            "enthusiastic": {
                "opening_templates": [
                    "I am absolutely thrilled to apply for the {job_title} position at {company_name}! Your company's innovative approach to {industry} aligns perfectly with my passion and expertise.",
                    "When I discovered the {job_title} opening at {company_name}, I knew I had to apply immediately. Your commitment to {company_value} resonates deeply with my professional values.",
                    "I couldn't be more excited about the opportunity to join {company_name} as a {job_title}. Your reputation for {company_strength} makes this my dream position!"
                ]
            },
            "creative": {
                "opening_templates": [
                    "Imagine a {job_title} who combines {skill1} with {skill2} to create {innovative_solution}. That's exactly what I bring to {company_name}.",
                    "While scrolling through your latest {company_project}, I couldn't help but think: 'This is where I belong.' The {job_title} position is the perfect canvas for my {creative_skills}.",
                    "They say the best {job_title}s think outside the box. I prefer to redesign the box entirely, which is why {company_name} caught my attention."
                ]
            }
        }

    async def generate_from_resume(
            self,
            resume_data: Dict[str, Any],
            job_title: str,
            company_name: str,
            job_description: Optional[str] = None,
            hiring_manager_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate cover letter content from resume data"""
        try:
            # Extract key information from resume
            personal_info = resume_data.get('personal_info', {})
            work_experience = resume_data.get('work_experience', [])
            skills = resume_data.get('skills', {})

            # Get most recent job
            recent_job = work_experience[0] if work_experience else {}

            # Extract relevant skills
            all_skills = []
            for skill_category in skills.values():
                if isinstance(skill_category, list):
                    all_skills.extend(skill_category)

            # Generate opening paragraph
            opening = self._generate_opening_from_resume(
                job_title, company_name, recent_job, all_skills[:5]
            )

            # Generate body paragraphs
            body_paragraphs = self._generate_body_from_resume(
                work_experience, skills, job_title, company_name, job_description
            )

            # Generate closing paragraph
            closing = self._generate_closing_from_resume(
                job_title, company_name, all_skills[:3]
            )

            return {
                "opening_paragraph": opening,
                "body_paragraphs": body_paragraphs,
                "closing_paragraph": closing,
                "signature": f"{personal_info.get('first_name', '')} {personal_info.get('last_name', '')}".strip() or "[Your Name]"
            }

        except Exception as e:
            logger.error(f"Error generating cover letter from resume: {e}")
            raise

    async def generate_ai_content(
            self,
            job_title: str,
            company_name: str,
            job_description: Optional[str] = None,
            user_background: Optional[str] = None,
            tone: str = "professional",
            key_skills: Optional[List[str]] = None,
            resume_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate cover letter content using AI"""
        try:
            # Select appropriate templates based on tone
            templates = self.templates.get(tone, self.templates["professional"])

            # Generate content based on available data
            if resume_data:
                return await self.generate_from_resume(
                    resume_data, job_title, company_name, job_description
                )

            # Generate from scratch using templates
            opening = self._generate_ai_opening(
                job_title, company_name, templates, user_background, key_skills
            )

            body_paragraphs = self._generate_ai_body(
                job_title, company_name, job_description, user_background, key_skills, templates
            )

            closing = self._generate_ai_closing(
                job_title, company_name, templates, key_skills
            )

            return {
                "opening_paragraph": opening,
                "body_paragraphs": body_paragraphs,
                "closing_paragraph": closing
            }

        except Exception as e:
            logger.error(f"Error generating AI cover letter content: {e}")
            raise

    def _generate_opening_from_resume(self, job_title: str, company_name: str, recent_job: Dict,
                                      skills: List[str]) -> str:
        """Generate opening paragraph from resume data"""
        previous_role = recent_job.get('job_title', 'my previous role')
        relevant_skills = ', '.join(skills[:3]) if skills else 'my diverse skill set'

        return f"I am writing to express my strong interest in the {job_title} position at {company_name}. With my experience as {previous_role} and expertise in {relevant_skills}, I am confident I would be a valuable addition to your team."

    def _generate_body_from_resume(self, work_experience: List[Dict], skills: Dict, job_title: str, company_name: str,
                                   job_description: Optional[str]) -> List[str]:
        """Generate body paragraphs from resume data"""
        paragraphs = []

        # First body paragraph - experience
        if work_experience:
            recent_job = work_experience[0]
            job_title_prev = recent_job.get('job_title', 'my previous role')
            company_prev = recent_job.get('company', 'my previous company')
            responsibilities = recent_job.get('responsibilities', [])

            key_achievement = responsibilities[0] if responsibilities else "delivered excellent results"

            paragraphs.append(
                f"In my role as {job_title_prev} at {company_prev}, I {key_achievement.lower()}. "
                f"This experience has given me a deep understanding of the skills required for the {job_title} position, "
                f"and I am excited about the opportunity to bring this expertise to {company_name}."
            )

        # Second body paragraph - skills and company fit
        all_skills = []
        for skill_category in skills.values():
            if isinstance(skill_category, list):
                all_skills.extend(skill_category[:2])

        key_skills_text = ', '.join(all_skills[:4]) if all_skills else 'problem-solving and analytical thinking'

        paragraphs.append(
            f"My core competencies include {key_skills_text}, which align well with the requirements for this role. "
            f"I am particularly drawn to {company_name} because of your reputation for innovation and excellence in the industry. "
            f"I believe my background and passion for continuous learning would enable me to make meaningful contributions to your team."
        )

        return paragraphs

    def _generate_closing_from_resume(self, job_title: str, company_name: str, key_skills: List[str]) -> str:
        """Generate closing paragraph from resume data"""
        skills_text = ', '.join(key_skills) if key_skills else 'my diverse skill set'

        return f"I would welcome the opportunity to discuss how my experience and {skills_text} can contribute to {company_name}'s continued success. Thank you for considering my application, and I look forward to hearing from you soon."

    def _generate_ai_opening(self, job_title: str, company_name: str, templates: Dict, user_background: Optional[str],
                             key_skills: Optional[List[str]]) -> str:
        """Generate AI opening paragraph"""
        template = templates["opening_templates"][0]  # Use first template for simplicity

        # Simple template variable replacement
        relevant_field = self._infer_field_from_job_title(job_title)

        return template.format(
            job_title=job_title,
            company_name=company_name,
            relevant_field=relevant_field,
            years_experience="several",
            industry=self._infer_industry_from_job_title(job_title),
            key_qualification=key_skills[0] if key_skills else "strong qualifications"
        )

    def _generate_ai_body(self, job_title: str, company_name: str, job_description: Optional[str],
                          user_background: Optional[str], key_skills: Optional[List[str]], templates: Dict) -> List[
        str]:
        """Generate AI body paragraphs"""
        paragraphs = []

        # Experience paragraph
        if user_background:
            paragraphs.append(
                f"My background in {user_background} has equipped me with the skills necessary for the {job_title} role. "
                f"I am particularly excited about the opportunity to apply my expertise at {company_name} and contribute to your team's success."
            )
        else:
            skills_text = ', '.join(key_skills[:3]) if key_skills else 'diverse professional skills'
            paragraphs.append(
                f"Throughout my career, I have developed strong expertise in {skills_text}. "
                f"I am drawn to {company_name} because of your commitment to excellence and innovation in the industry."
            )

        # Skills and motivation paragraph
        motivation_text = "making a meaningful impact" if not job_description else "contributing to the specific goals outlined in your job posting"
        paragraphs.append(
            f"What excites me most about this opportunity is the chance to combine my technical skills with my passion for {motivation_text}. "
            f"I believe my proactive approach and commitment to continuous learning would make me a valuable addition to your {job_title} team."
        )

        return paragraphs

    def _generate_ai_closing(self, job_title: str, company_name: str, templates: Dict,
                             key_skills: Optional[List[str]]) -> str:
        """Generate AI closing paragraph"""
        expertise = ', '.join(key_skills[:2]) if key_skills else 'my experience'

        return f"I would be thrilled to discuss how my {expertise} can contribute to {company_name}'s continued growth and success. Thank you for your time and consideration, and I look forward to the opportunity to speak with you further about the {job_title} position."

    def _infer_field_from_job_title(self, job_title: str) -> str:
        """Infer relevant field from job title"""
        job_lower = job_title.lower()

        if any(term in job_lower for term in ['engineer', 'developer', 'programmer', 'software']):
            return "software development"
        elif any(term in job_lower for term in ['manager', 'director', 'lead']):
            return "leadership and management"
        elif any(term in job_lower for term in ['analyst', 'data', 'research']):
            return "data analysis"
        elif any(term in job_lower for term in ['marketing', 'sales', 'business']):
            return "business development"
        elif any(term in job_lower for term in ['design', 'creative', 'ui', 'ux']):
            return "design and user experience"
        else:
            return "the relevant field"

    def _infer_industry_from_job_title(self, job_title: str) -> str:
        """Infer industry from job title"""
        job_lower = job_title.lower()

        if any(term in job_lower for term in ['software', 'tech', 'engineer', 'developer']):
            return "technology"
        elif any(term in job_lower for term in ['healthcare', 'medical', 'nurse', 'doctor']):
            return "healthcare"
        elif any(term in job_lower for term in ['finance', 'accounting', 'bank']):
            return "finance"
        elif any(term in job_lower for term in ['education', 'teacher', 'professor']):
            return "education"
        elif any(term in job_lower for term in ['marketing', 'advertising', 'brand']):
            return "marketing"
        else:
            return "your industry"