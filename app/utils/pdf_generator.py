from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from io import BytesIO
from typing import Dict, List, Any, Optional
import logging
import os
import html
import re

logger = logging.getLogger(__name__)


class ResumePDFGenerator:
    """PDF generator for resume documents with comprehensive error handling and validation"""

    def __init__(self, pagesize=letter):
        self.pagesize = pagesize
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self._validate_fonts()

        # Memory management
        self._temp_files = []

    def _validate_fonts(self):
        """Validate that required fonts are available with fallbacks"""
        try:
            # Test font availability by creating a small document
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            # Check if Helvetica fonts are available (they should be built-in)
            available_fonts = pdfmetrics.getRegisteredFontNames()
            required_fonts = ['Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique']

            missing_fonts = [font for font in required_fonts if font not in available_fonts]
            if missing_fonts:
                logger.warning(f"Some fonts not available: {missing_fonts}. Using fallbacks.")
                # Register fallback fonts if needed
                self._register_fallback_fonts()

        except Exception as e:
            logger.warning(f"Font validation failed: {e}. Using default fonts.")
            self._register_fallback_fonts()

    def _register_fallback_fonts(self):
        """Register fallback fonts if primary fonts are unavailable"""
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            # Try to register basic fonts as fallbacks
            fallback_mappings = {
                'Helvetica': 'Times-Roman',
                'Helvetica-Bold': 'Times-Bold',
                'Helvetica-Oblique': 'Times-Italic'
            }

            for preferred, fallback in fallback_mappings.items():
                if preferred not in pdfmetrics.getRegisteredFontNames():
                    logger.info(f"Using {fallback} as fallback for {preferred}")

        except Exception as e:
            logger.error(f"Error registering fallback fonts: {e}")

    def _setup_custom_styles(self):
        """Setup custom paragraph styles for resume with error handling"""
        try:
            # Main title style
            self.styles.add(ParagraphStyle(
                name='ResumeTitle',
                parent=self.styles['Heading1'],
                fontSize=28,
                spaceAfter=12,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#2E4057'),
                fontName='Helvetica-Bold'
            ))

            # Contact info style
            self.styles.add(ParagraphStyle(
                name='ContactInfo',
                parent=self.styles['Normal'],
                fontSize=12,
                alignment=TA_CENTER,
                spaceAfter=20,
                textColor=colors.HexColor('#555555')
            ))

            # Section title style
            self.styles.add(ParagraphStyle(
                name='SectionTitle',
                parent=self.styles['Heading2'],
                fontSize=16,
                spaceBefore=20,
                spaceAfter=10,
                textColor=colors.HexColor('#2E4057'),
                fontName='Helvetica-Bold',
                borderWidth=1,
                borderColor=colors.HexColor('#2E4057'),
                borderPadding=5,
                backColor=colors.HexColor('#F8F9FA')
            ))

            # Job title style
            self.styles.add(ParagraphStyle(
                name='JobTitle',
                parent=self.styles['Normal'],
                fontSize=14,
                spaceBefore=10,
                spaceAfter=2,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor('#2E4057')
            ))

            # Company/Institution style
            self.styles.add(ParagraphStyle(
                name='CompanyName',
                parent=self.styles['Normal'],
                fontSize=12,
                spaceAfter=2,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor('#666666')
            ))

            # Date style
            self.styles.add(ParagraphStyle(
                name='DateStyle',
                parent=self.styles['Normal'],
                fontSize=10,
                spaceAfter=5,
                textColor=colors.HexColor('#888888'),
                fontName='Helvetica-Oblique'
            ))

            # Bullet point style
            self.styles.add(ParagraphStyle(
                name='BulletPoint',
                parent=self.styles['Normal'],
                fontSize=11,
                leftIndent=20,
                spaceAfter=3,
                bulletIndent=10,
                bulletFontName='Symbol'
            ))

            # Skills style
            self.styles.add(ParagraphStyle(
                name='SkillCategory',
                parent=self.styles['Normal'],
                fontSize=12,
                spaceBefore=5,
                spaceAfter=3,
                fontName='Helvetica-Bold'
            ))

            # Summary style
            self.styles.add(ParagraphStyle(
                name='Summary',
                parent=self.styles['Normal'],
                fontSize=11,
                alignment=TA_JUSTIFY,
                spaceAfter=15,
                leading=14
            ))

        except Exception as e:
            logger.error(f"Error setting up custom styles: {e}")
            # Continue with default styles if custom setup fails

    def generate_resume_pdf(self, resume_content: Dict[str, Any], title: str = "Resume") -> BytesIO:
        """Generate PDF from resume content with comprehensive error handling"""
        buffer = None
        try:
            # Validate input
            if not resume_content:
                raise ValueError("Resume content cannot be empty")

            if not isinstance(resume_content, dict):
                raise ValueError("Resume content must be a dictionary")

            # Validate required sections
            personal_info = resume_content.get('personal_info', {})
            if not personal_info:
                raise ValueError("Resume must contain personal information")

            if not isinstance(personal_info, dict):
                raise ValueError("Personal information must be a dictionary")

            # Create buffer and document
            buffer = BytesIO()

            try:
                doc = SimpleDocTemplate(
                    buffer,
                    pagesize=self.pagesize,
                    rightMargin=0.75 * inch,
                    leftMargin=0.75 * inch,
                    topMargin=0.75 * inch,
                    bottomMargin=0.75 * inch,
                    title=self._sanitize_title(title),
                    author="Resume Builder Service"
                )
            except Exception as e:
                logger.error(f"Error creating document: {e}")
                raise ValueError("Failed to create PDF document")

            # Build PDF content
            story = []

            try:
                # Header section
                self._add_header(story, personal_info)

                # Professional summary
                if resume_content.get('professional_summary'):
                    self._add_professional_summary(story, resume_content['professional_summary'])

                # Work experience
                work_exp = resume_content.get('work_experience', [])
                if work_exp:
                    self._add_work_experience(story, work_exp)

                # Education
                education = resume_content.get('education', [])
                if education:
                    self._add_education(story, education)

                # Skills
                skills = resume_content.get('skills', {})
                if skills:
                    self._add_skills(story, skills)

                # Certifications
                certifications = resume_content.get('certifications', [])
                if certifications:
                    self._add_certifications(story, certifications)

                # Projects
                projects = resume_content.get('projects', [])
                if projects:
                    self._add_projects(story, projects)

                # Languages
                languages = resume_content.get('languages', [])
                if languages:
                    self._add_languages(story, languages)

            except Exception as e:
                logger.error(f"Error building PDF content: {e}")
                raise ValueError(f"Failed to build PDF content: {str(e)}")

            # Build PDF
            try:
                doc.build(story)
                buffer.seek(0)

                # Validate generated PDF
                if buffer.tell() == 0:
                    raise ValueError("Generated PDF is empty")

                logger.info(f"Successfully generated PDF for resume: {title} ({buffer.tell()} bytes)")
                return buffer

            except Exception as e:
                logger.error(f"Error building PDF: {e}")
                raise ValueError(f"Failed to generate PDF: {str(e)}")

        except ValueError:
            if buffer:
                buffer.close()
            raise
        except Exception as e:
            if buffer:
                buffer.close()
            logger.error(f"Unexpected error generating PDF: {e}", exc_info=True)
            raise ValueError(f"PDF generation failed: {str(e)}")

    def _sanitize_title(self, title: str) -> str:
        """Sanitize title for PDF metadata"""
        if not title or not isinstance(title, str):
            return "Resume"

        # Remove or replace problematic characters
        sanitized = ''.join(c for c in title if c.isprintable() and c not in '<>/\\|:*?"')
        return sanitized[:100] if sanitized else "Resume"

    def _add_header(self, story: List, personal_info: Dict[str, Any]):
        """Add header with personal information"""
        try:
            # Full name
            first_name = self._safe_get_string(personal_info, 'first_name')
            last_name = self._safe_get_string(personal_info, 'last_name')

            if not first_name and not last_name:
                full_name = "Name Not Provided"
            else:
                full_name = f"{first_name} {last_name}".strip()

            story.append(Paragraph(self._escape_xml(full_name), self.styles['ResumeTitle']))

            # Contact information
            contact_parts = []
            email = self._safe_get_string(personal_info, 'email')
            phone = self._safe_get_string(personal_info, 'phone')
            address = self._safe_get_string(personal_info, 'address')

            if email:
                contact_parts.append(self._escape_xml(email))
            if phone:
                contact_parts.append(self._escape_xml(phone))
            if address:
                contact_parts.append(self._escape_xml(address))

            if contact_parts:
                contact_info = ' | '.join(contact_parts)
                story.append(Paragraph(contact_info, self.styles['ContactInfo']))

            # Links
            link_parts = []
            linkedin_url = self._safe_get_string(personal_info, 'linkedin_url')
            portfolio_url = self._safe_get_string(personal_info, 'portfolio_url')
            github_url = self._safe_get_string(personal_info, 'github_url')

            if linkedin_url:
                link_parts.append(f"LinkedIn: {self._escape_xml(linkedin_url)}")
            if portfolio_url:
                link_parts.append(f"Portfolio: {self._escape_xml(portfolio_url)}")
            if github_url:
                link_parts.append(f"GitHub: {self._escape_xml(github_url)}")

            if link_parts:
                links_info = ' | '.join(link_parts)
                story.append(Paragraph(links_info, self.styles['ContactInfo']))

        except Exception as e:
            logger.error(f"Error adding header: {e}")
            # Add minimal header if error occurs
            story.append(Paragraph("Resume", self.styles['ResumeTitle']))

    def _add_professional_summary(self, story: List, summary: str):
        """Add professional summary section"""
        try:
            if not summary or not summary.strip():
                return

            story.append(Paragraph("Professional Summary", self.styles['SectionTitle']))
            cleaned_summary = self._escape_xml(self._safe_get_string({'summary': summary}, 'summary'))
            story.append(Paragraph(cleaned_summary, self.styles['Summary']))

        except Exception as e:
            logger.error(f"Error adding professional summary: {e}")

    def _add_work_experience(self, story: List, work_experience: List[Dict[str, Any]]):
        """Add work experience section"""
        try:
            if not work_experience or not isinstance(work_experience, list):
                return

            story.append(Paragraph("Work Experience", self.styles['SectionTitle']))

            for i, job in enumerate(work_experience):
                try:
                    if not isinstance(job, dict):
                        logger.warning(f"Skipping invalid work experience entry at index {i}")
                        continue

                    # Job title
                    job_title = self._safe_get_string(job, 'job_title', 'Position Title')
                    story.append(Paragraph(self._escape_xml(job_title), self.styles['JobTitle']))

                    # Company and location
                    company = self._safe_get_string(job, 'company', 'Company')
                    location = self._safe_get_string(job, 'location')
                    company_info = self._escape_xml(company)
                    if location:
                        company_info += f" - {self._escape_xml(location)}"
                    story.append(Paragraph(company_info, self.styles['CompanyName']))

                    # Dates
                    start_date = self._safe_get_string(job, 'start_date')
                    end_date = self._safe_get_string(job, 'end_date', 'Present')
                    if start_date:
                        date_range = f"{self._escape_xml(start_date)} - {self._escape_xml(end_date)}"
                        story.append(Paragraph(date_range, self.styles['DateStyle']))

                    # Responsibilities
                    responsibilities = job.get('responsibilities', [])
                    if isinstance(responsibilities, list):
                        for responsibility in responsibilities:
                            if responsibility and str(responsibility).strip():
                                bullet_text = f"• {self._escape_xml(str(responsibility).strip())}"
                                story.append(Paragraph(bullet_text, self.styles['BulletPoint']))

                    story.append(Spacer(1, 10))

                except Exception as job_error:
                    logger.error(f"Error processing work experience entry {i}: {job_error}")
                    continue

        except Exception as e:
            logger.error(f"Error adding work experience: {e}")

    def _add_education(self, story: List, education: List[Dict[str, Any]]):
        """Add education section"""
        try:
            if not education or not isinstance(education, list):
                return

            story.append(Paragraph("Education", self.styles['SectionTitle']))

            for i, edu in enumerate(education):
                try:
                    if not isinstance(edu, dict):
                        logger.warning(f"Skipping invalid education entry at index {i}")
                        continue

                    # Degree
                    degree = self._safe_get_string(edu, 'degree', 'Degree')
                    story.append(Paragraph(self._escape_xml(degree), self.styles['JobTitle']))

                    # Institution and location
                    institution = self._safe_get_string(edu, 'institution', 'Institution')
                    location = self._safe_get_string(edu, 'location')
                    institution_info = self._escape_xml(institution)
                    if location:
                        institution_info += f" - {self._escape_xml(location)}"
                    story.append(Paragraph(institution_info, self.styles['CompanyName']))

                    # Graduation year and GPA
                    grad_info = []
                    graduation_year = self._safe_get_string(edu, 'graduation_year')
                    gpa = edu.get('gpa')

                    if graduation_year:
                        grad_info.append(f"Graduated: {self._escape_xml(graduation_year)}")
                    if gpa:
                        grad_info.append(f"GPA: {self._escape_xml(str(gpa))}")

                    if grad_info:
                        story.append(Paragraph(' | '.join(grad_info), self.styles['DateStyle']))

                    # Field of study
                    field_of_study = self._safe_get_string(edu, 'field_of_study')
                    if field_of_study:
                        field_text = f"Field of Study: {self._escape_xml(field_of_study)}"
                        story.append(Paragraph(field_text, self.styles['Normal']))

                    # Honors
                    honors = self._safe_get_string(edu, 'honors')
                    if honors:
                        honors_text = f"Honors: {self._escape_xml(honors)}"
                        story.append(Paragraph(honors_text, self.styles['Normal']))

                    story.append(Spacer(1, 10))

                except Exception as edu_error:
                    logger.error(f"Error processing education entry {i}: {edu_error}")
                    continue

        except Exception as e:
            logger.error(f"Error adding education: {e}")

    def _add_skills(self, story: List, skills: Dict[str, List[str]]):
        """Add skills section"""
        try:
            if not skills or not isinstance(skills, dict) or not any(skills.values()):
                return

            story.append(Paragraph("Skills", self.styles['SectionTitle']))

            for skill_category, skill_list in skills.items():
                try:
                    if skill_list and isinstance(skill_list, list):
                        category_title = str(skill_category).replace('_', ' ').title()
                        story.append(Paragraph(f"{self._escape_xml(category_title)}:", self.styles['SkillCategory']))

                        # Clean and escape skills
                        clean_skills = []
                        for skill in skill_list:
                            if skill and str(skill).strip():
                                clean_skills.append(self._escape_xml(str(skill).strip()))

                        if clean_skills:
                            skills_text = ', '.join(clean_skills)
                            story.append(Paragraph(skills_text, self.styles['Normal']))
                            story.append(Spacer(1, 5))

                except Exception as skill_error:
                    logger.error(f"Error processing skills category {skill_category}: {skill_error}")
                    continue

        except Exception as e:
            logger.error(f"Error adding skills: {e}")

    def _add_certifications(self, story: List, certifications: List[Dict[str, Any]]):
        """Add certifications section"""
        try:
            if not certifications or not isinstance(certifications, list):
                return

            story.append(Paragraph("Certifications", self.styles['SectionTitle']))

            for i, cert in enumerate(certifications):
                try:
                    if not isinstance(cert, dict):
                        logger.warning(f"Skipping invalid certification entry at index {i}")
                        continue

                    # Certification name
                    cert_name = self._safe_get_string(cert, 'name', 'Certification')
                    story.append(Paragraph(self._escape_xml(cert_name), self.styles['JobTitle']))

                    # Issuer
                    issuer = self._safe_get_string(cert, 'issuer')
                    if issuer:
                        story.append(Paragraph(self._escape_xml(issuer), self.styles['CompanyName']))

                    # Dates
                    issue_date = self._safe_get_string(cert, 'issue_date')
                    expiry_date = self._safe_get_string(cert, 'expiry_date')
                    if issue_date:
                        date_text = f"Issued: {self._escape_xml(issue_date)}"
                        if expiry_date:
                            date_text += f" | Expires: {self._escape_xml(expiry_date)}"
                        story.append(Paragraph(date_text, self.styles['DateStyle']))

                    # Credential ID
                    credential_id = self._safe_get_string(cert, 'credential_id')
                    if credential_id:
                        cred_text = f"Credential ID: {self._escape_xml(credential_id)}"
                        story.append(Paragraph(cred_text, self.styles['Normal']))

                    story.append(Spacer(1, 10))

                except Exception as cert_error:
                    logger.error(f"Error processing certification {i}: {cert_error}")
                    continue

        except Exception as e:
            logger.error(f"Error adding certifications: {e}")

    def _add_projects(self, story: List, projects: List[Dict[str, Any]]):
        """Add projects section"""
        try:
            if not projects or not isinstance(projects, list):
                return

            story.append(Paragraph("Projects", self.styles['SectionTitle']))

            for i, project in enumerate(projects):
                try:
                    if not isinstance(project, dict):
                        logger.warning(f"Skipping invalid project entry at index {i}")
                        continue

                    # Project name
                    project_name = self._safe_get_string(project, 'name', 'Project')
                    story.append(Paragraph(self._escape_xml(project_name), self.styles['JobTitle']))

                    # Description
                    description = self._safe_get_string(project, 'description')
                    if description:
                        story.append(Paragraph(self._escape_xml(description), self.styles['Normal']))

                    # Technologies
                    technologies = project.get('technologies', [])
                    if isinstance(technologies, list) and technologies:
                        clean_techs = []
                        for tech in technologies:
                            if tech and str(tech).strip():
                                clean_techs.append(self._escape_xml(str(tech).strip()))

                        if clean_techs:
                            tech_text = f"Technologies: {', '.join(clean_techs)}"
                            story.append(Paragraph(tech_text, self.styles['Normal']))

                    # URLs
                    urls = []
                    url = self._safe_get_string(project, 'url')
                    github_url = self._safe_get_string(project, 'github_url')

                    if url:
                        urls.append(f"Project URL: {self._escape_xml(url)}")
                    if github_url:
                        urls.append(f"GitHub: {self._escape_xml(github_url)}")

                    if urls:
                        story.append(Paragraph(' | '.join(urls), self.styles['DateStyle']))

                    story.append(Spacer(1, 10))

                except Exception as project_error:
                    logger.error(f"Error processing project {i}: {project_error}")
                    continue

        except Exception as e:
            logger.error(f"Error adding projects: {e}")

    def _add_languages(self, story: List, languages: List[Dict[str, Any]]):
        """Add languages section"""
        try:
            if not languages or not isinstance(languages, list):
                return

            story.append(Paragraph("Languages", self.styles['SectionTitle']))

            language_items = []
            for i, lang in enumerate(languages):
                try:
                    if not isinstance(lang, dict):
                        logger.warning(f"Skipping invalid language entry at index {i}")
                        continue

                    language = self._safe_get_string(lang, 'language')
                    proficiency = self._safe_get_string(lang, 'proficiency')

                    if language and proficiency:
                        lang_text = f"{self._escape_xml(language)} ({self._escape_xml(proficiency)})"
                        language_items.append(lang_text)

                except Exception as lang_error:
                    logger.error(f"Error processing language {i}: {lang_error}")
                    continue

            if language_items:
                languages_text = ', '.join(language_items)
                story.append(Paragraph(languages_text, self.styles['Normal']))

            story.append(Spacer(1, 10))

        except Exception as e:
            logger.error(f"Error adding languages: {e}")

    def _safe_get_string(self, data: Dict[str, Any], key: str, default: str = "") -> str:
        """Safely get string value from dictionary"""
        try:
            value = data.get(key, default)
            if value is None:
                return default
            return str(value).strip()
        except Exception as e:
            logger.warning(f"Error getting string value for key '{key}': {e}")
            return default

    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters for ReportLab with enhanced safety"""
        if not text:
            return ""

        try:
            # Convert to string and handle None
            text = str(text) if text is not None else ""

            # Use html.escape for basic escaping
            text = html.escape(text, quote=True)

            # Additional ReportLab-specific escaping
            text = text.replace('\r\n', '<br/>')
            text = text.replace('\n', '<br/>')
            text = text.replace('\r', '<br/>')

            # Remove or replace problematic characters
            text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', text)

            return text
        except Exception as e:
            logger.error(f"Error escaping XML: {e}")
            return str(text) if text else ""

    def estimate_content_length(self, resume_content: Dict[str, Any]) -> int:
        """Estimate the content length to predict PDF pages"""
        try:
            content_length = 0

            # Count text in each section
            sections = [
                resume_content.get('professional_summary', ''),
                str(resume_content.get('work_experience', [])),
                str(resume_content.get('education', [])),
                str(resume_content.get('skills', {})),
                str(resume_content.get('certifications', [])),
                str(resume_content.get('projects', [])),
                str(resume_content.get('languages', []))
            ]

            for section in sections:
                content_length += len(str(section))

            return content_length

        except Exception as e:
            logger.error(f"Error estimating content length: {e}")
            return 1000  # Default estimate

    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            for temp_file in self._temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception as e:
                    logger.error(f"Error removing temp file {temp_file}: {e}")
            self._temp_files.clear()
        except Exception as e:
            logger.error(f"Error during temp file cleanup: {e}")

    def __del__(self):
        """Cleanup when generator is destroyed"""
        try:
            self.cleanup_temp_files()
        except Exception as e:
            logger.error(f"Error in PDF generator destructor: {e}")