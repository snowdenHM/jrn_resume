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

logger = logging.getLogger(__name__)


class ResumePDFGenerator:
    """PDF generator for resume documents"""

    def __init__(self, pagesize=letter):
        self.pagesize = pagesize
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles for resume"""

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

    def generate_resume_pdf(self, resume_content: Dict[str, Any], title: str = "Resume") -> BytesIO:
        """Generate PDF from resume content"""
        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=self.pagesize,
                rightMargin=0.75 * inch,
                leftMargin=0.75 * inch,
                topMargin=0.75 * inch,
                bottomMargin=0.75 * inch,
                title=title
            )

            # Build PDF content
            story = []

            # Header section
            self._add_header(story, resume_content.get('personal_info', {}))

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

            # Build PDF
            doc.build(story)
            buffer.seek(0)

            logger.info(f"Successfully generated PDF for resume: {title}")
            return buffer

        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            raise

    def _add_header(self, story: List, personal_info: Dict[str, Any]):
        """Add header with personal information"""
        # Full name
        full_name = f"{personal_info.get('first_name', '')} {personal_info.get('last_name', '')}"
        story.append(Paragraph(full_name.strip(), self.styles['ResumeTitle']))

        # Contact information
        contact_parts = []
        if personal_info.get('email'):
            contact_parts.append(personal_info['email'])
        if personal_info.get('phone'):
            contact_parts.append(personal_info['phone'])
        if personal_info.get('address'):
            contact_parts.append(personal_info['address'])

        if contact_parts:
            contact_info = ' | '.join(contact_parts)
            story.append(Paragraph(contact_info, self.styles['ContactInfo']))

        # Links
        link_parts = []
        if personal_info.get('linkedin_url'):
            link_parts.append(f"LinkedIn: {personal_info['linkedin_url']}")
        if personal_info.get('portfolio_url'):
            link_parts.append(f"Portfolio: {personal_info['portfolio_url']}")
        if personal_info.get('github_url'):
            link_parts.append(f"GitHub: {personal_info['github_url']}")

        if link_parts:
            links_info = ' | '.join(link_parts)
            story.append(Paragraph(links_info, self.styles['ContactInfo']))

    def _add_professional_summary(self, story: List, summary: str):
        """Add professional summary section"""
        story.append(Paragraph("Professional Summary", self.styles['SectionTitle']))
        story.append(Paragraph(summary, self.styles['Summary']))

    def _add_work_experience(self, story: List, work_experience: List[Dict[str, Any]]):
        """Add work experience section"""
        story.append(Paragraph("Work Experience", self.styles['SectionTitle']))

        for job in work_experience:
            # Job title
            job_title = job.get('job_title', '')
            story.append(Paragraph(job_title, self.styles['JobTitle']))

            # Company and location
            company_info = job.get('company', '')
            if job.get('location'):
                company_info += f" - {job['location']}"
            story.append(Paragraph(company_info, self.styles['CompanyName']))

            # Dates
            start_date = job.get('start_date', '')
            end_date = job.get('end_date', 'Present')
            if start_date:
                date_range = f"{start_date} - {end_date}"
                story.append(Paragraph(date_range, self.styles['DateStyle']))

            # Responsibilities
            responsibilities = job.get('responsibilities', [])
            for responsibility in responsibilities:
                bullet_text = f"• {responsibility}"
                story.append(Paragraph(bullet_text, self.styles['BulletPoint']))

            story.append(Spacer(1, 10))

    def _add_education(self, story: List, education: List[Dict[str, Any]]):
        """Add education section"""
        story.append(Paragraph("Education", self.styles['SectionTitle']))

        for edu in education:
            # Degree
            degree = edu.get('degree', '')
            story.append(Paragraph(degree, self.styles['JobTitle']))

            # Institution and location
            institution_info = edu.get('institution', '')
            if edu.get('location'):
                institution_info += f" - {edu['location']}"
            story.append(Paragraph(institution_info, self.styles['CompanyName']))

            # Graduation year and GPA
            grad_info = []
            if edu.get('graduation_year'):
                grad_info.append(f"Graduated: {edu['graduation_year']}")
            if edu.get('gpa'):
                grad_info.append(f"GPA: {edu['gpa']}")

            if grad_info:
                story.append(Paragraph(' | '.join(grad_info), self.styles['DateStyle']))

            # Field of study
            if edu.get('field_of_study'):
                story.append(Paragraph(f"Field of Study: {edu['field_of_study']}", self.styles['Normal']))

            # Honors
            if edu.get('honors'):
                story.append(Paragraph(f"Honors: {edu['honors']}", self.styles['Normal']))

            story.append(Spacer(1, 10))

    def _add_skills(self, story: List, skills: Dict[str, List[str]]):
        """Add skills section"""
        story.append(Paragraph("Skills", self.styles['SectionTitle']))

        for skill_category, skill_list in skills.items():
            if skill_list:
                category_title = skill_category.replace('_', ' ').title()
                story.append(Paragraph(f"{category_title}:", self.styles['SkillCategory']))

                skills_text = ', '.join(skill_list)
                story.append(Paragraph(skills_text, self.styles['Normal']))
                story.append(Spacer(1, 5))

    def _add_certifications(self, story: List, certifications: List[Dict[str, Any]]):
        """Add certifications section"""
        story.append(Paragraph("Certifications", self.styles['SectionTitle']))

        for cert in certifications:
            # Certification name
            cert_name = cert.get('name', '')
            story.append(Paragraph(cert_name, self.styles['JobTitle']))

            # Issuer
            issuer = cert.get('issuer', '')
            story.append(Paragraph(issuer, self.styles['CompanyName']))

            # Dates
            issue_date = cert.get('issue_date', '')
            expiry_date = cert.get('expiry_date')
            if issue_date:
                date_text = f"Issued: {issue_date}"
                if expiry_date:
                    date_text += f" | Expires: {expiry_date}"
                story.append(Paragraph(date_text, self.styles['DateStyle']))

            # Credential ID
            if cert.get('credential_id'):
                story.append(Paragraph(f"Credential ID: {cert['credential_id']}", self.styles['Normal']))

            story.append(Spacer(1, 10))

    def _add_projects(self, story: List, projects: List[Dict[str, Any]]):
        """Add projects section"""
        story.append(Paragraph("Projects", self.styles['SectionTitle']))

        for project in projects:
            # Project name
            project_name = project.get('name', '')
            story.append(Paragraph(project_name, self.styles['JobTitle']))

            # Description
            description = project.get('description', '')
            story.append(Paragraph(description, self.styles['Normal']))

            # Technologies
            technologies = project.get('technologies', [])
            if technologies:
                tech_text = f"Technologies: {', '.join(technologies)}"
                story.append(Paragraph(tech_text, self.styles['Normal']))

            # URLs
            urls = []
            if project.get('url'):
                urls.append(f"Project URL: {project['url']}")
            if project.get('github_url'):
                urls.append(f"GitHub: {project['github_url']}")

            if urls:
                story.append(Paragraph(' | '.join(urls), self.styles['DateStyle']))

            story.append(Spacer(1, 10))

    def _add_languages(self, story: List, languages: List[Dict[str, Any]]):
        """Add languages section"""
        story.append(Paragraph("Languages", self.styles['SectionTitle']))

        language_items = []
        for lang in languages:
            language = lang.get('language', '')
            proficiency = lang.get('proficiency', '')
            if language and proficiency:
                language_items.append(f"{language} ({proficiency})")

        if language_items:
            languages_text = ', '.join(language_items)
            story.append(Paragraph(languages_text, self.styles['Normal']))

        story.append(Spacer(1, 10))