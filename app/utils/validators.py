from typing import Dict, List, Any, Optional, Tuple
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ResumeValidator:
    """Validator class for resume content and structure"""

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))

    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format"""
        # Remove all non-digits
        digits_only = re.sub(r'\D', '', phone)
        return len(digits_only) >= 10

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format"""
        if not url:
            return True  # Optional field

        url_pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
        return bool(re.match(url_pattern, url))

    @staticmethod
    def validate_date_format(date_str: str) -> bool:
        """Validate YYYY-MM date format"""
        if not date_str:
            return True  # Optional field

        try:
            datetime.strptime(date_str, '%Y-%m')
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_year_format(year_str: str) -> bool:
        """Validate YYYY year format"""
        if not year_str:
            return False

        try:
            year = int(year_str)
            current_year = datetime.now().year
            return 1900 <= year <= current_year + 10
        except ValueError:
            return False

    @staticmethod
    def validate_gpa(gpa: Optional[float]) -> bool:
        """Validate GPA value"""
        if gpa is None:
            return True  # Optional field

        return 0.0 <= gpa <= 4.0

    @staticmethod
    def validate_personal_info(personal_info: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate personal information section"""
        errors = []

        # Required fields
        required_fields = ['first_name', 'last_name', 'email', 'phone']
        for field in required_fields:
            if not personal_info.get(field):
                errors.append(f"Personal info: {field} is required")

        # Email validation
        if personal_info.get('email') and not ResumeValidator.validate_email(personal_info['email']):
            errors.append("Personal info: Invalid email format")

        # Phone validation
        if personal_info.get('phone') and not ResumeValidator.validate_phone(personal_info['phone']):
            errors.append("Personal info: Invalid phone number format")

        # URL validations
        url_fields = ['linkedin_url', 'portfolio_url', 'github_url']
        for field in url_fields:
            if personal_info.get(field) and not ResumeValidator.validate_url(personal_info[field]):
                errors.append(f"Personal info: Invalid {field} format")

        return len(errors) == 0, errors

    @staticmethod
    def validate_work_experience(work_experience: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate work experience section"""
        errors = []

        for i, job in enumerate(work_experience):
            # Required fields
            required_fields = ['job_title', 'company', 'start_date', 'responsibilities']
            for field in required_fields:
                if not job.get(field):
                    errors.append(f"Work experience #{i + 1}: {field} is required")

            # Date validations
            if job.get('start_date') and not ResumeValidator.validate_date_format(job['start_date']):
                errors.append(f"Work experience #{i + 1}: Invalid start_date format (use YYYY-MM)")

            if job.get('end_date') and not ResumeValidator.validate_date_format(job['end_date']):
                errors.append(f"Work experience #{i + 1}: Invalid end_date format (use YYYY-MM)")

            # End date should be after start date
            if job.get('start_date') and job.get('end_date'):
                if job['end_date'] <= job['start_date']:
                    errors.append(f"Work experience #{i + 1}: End date must be after start date")

            # Responsibilities validation
            responsibilities = job.get('responsibilities', [])
            if not isinstance(responsibilities, list) or len(responsibilities) == 0:
                errors.append(f"Work experience #{i + 1}: At least one responsibility is required")
            elif any(not resp.strip() for resp in responsibilities):
                errors.append(f"Work experience #{i + 1}: Responsibilities cannot be empty")

        return len(errors) == 0, errors

    @staticmethod
    def validate_education(education: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate education section"""
        errors = []

        for i, edu in enumerate(education):
            # Required fields
            required_fields = ['degree', 'institution', 'graduation_year']
            for field in required_fields:
                if not edu.get(field):
                    errors.append(f"Education #{i + 1}: {field} is required")

            # Year validation
            if edu.get('graduation_year') and not ResumeValidator.validate_year_format(edu['graduation_year']):
                errors.append(f"Education #{i + 1}: Invalid graduation_year format (use YYYY)")

            # GPA validation
            if not ResumeValidator.validate_gpa(edu.get('gpa')):
                errors.append(f"Education #{i + 1}: GPA must be between 0.0 and 4.0")

        return len(errors) == 0, errors

    @staticmethod
    def validate_certifications(certifications: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate certifications section"""
        errors = []

        for i, cert in enumerate(certifications):
            # Required fields
            required_fields = ['name', 'issuer', 'issue_date']
            for field in required_fields:
                if not cert.get(field):
                    errors.append(f"Certification #{i + 1}: {field} is required")

            # Date validations
            if cert.get('issue_date') and not ResumeValidator.validate_date_format(cert['issue_date']):
                errors.append(f"Certification #{i + 1}: Invalid issue_date format (use YYYY-MM)")

            if cert.get('expiry_date') and not ResumeValidator.validate_date_format(cert['expiry_date']):
                errors.append(f"Certification #{i + 1}: Invalid expiry_date format (use YYYY-MM)")

            # URL validation
            if cert.get('credential_url') and not ResumeValidator.validate_url(cert['credential_url']):
                errors.append(f"Certification #{i + 1}: Invalid credential_url format")

        return len(errors) == 0, errors

    @staticmethod
    def validate_projects(projects: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate projects section"""
        errors = []

        for i, project in enumerate(projects):
            # Required fields
            required_fields = ['name', 'description', 'technologies']
            for field in required_fields:
                if not project.get(field):
                    errors.append(f"Project #{i + 1}: {field} is required")

            # Technologies validation
            technologies = project.get('technologies', [])
            if not isinstance(technologies, list) or len(technologies) == 0:
                errors.append(f"Project #{i + 1}: At least one technology is required")

            # URL validations
            url_fields = ['url', 'github_url']
            for field in url_fields:
                if project.get(field) and not ResumeValidator.validate_url(project[field]):
                    errors.append(f"Project #{i + 1}: Invalid {field} format")

            # Date validations
            date_fields = ['start_date', 'end_date']
            for field in date_fields:
                if project.get(field) and not ResumeValidator.validate_date_format(project[field]):
                    errors.append(f"Project #{i + 1}: Invalid {field} format (use YYYY-MM)")

        return len(errors) == 0, errors

    @staticmethod
    def validate_languages(languages: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate languages section"""
        errors = []
        valid_proficiencies = ['Basic', 'Intermediate', 'Advanced', 'Native', 'Fluent']

        for i, lang in enumerate(languages):
            # Required fields
            if not lang.get('language'):
                errors.append(f"Language #{i + 1}: language is required")

            if not lang.get('proficiency'):
                errors.append(f"Language #{i + 1}: proficiency is required")
            elif lang['proficiency'] not in valid_proficiencies:
                errors.append(f"Language #{i + 1}: proficiency must be one of {valid_proficiencies}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_skills(skills: Dict[str, List[str]]) -> Tuple[bool, List[str]]:
        """Validate skills section"""
        errors = []

        # Check if skills is a dictionary
        if not isinstance(skills, dict):
            errors.append("Skills: must be a dictionary")
            return False, errors

        # Validate each skill category
        for category, skill_list in skills.items():
            if not isinstance(skill_list, list):
                errors.append(f"Skills: {category} must be a list")
            elif any(not skill.strip() for skill in skill_list):
                errors.append(f"Skills: {category} cannot contain empty skills")

        return len(errors) == 0, errors

    @staticmethod
    def validate_resume_content(content: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate complete resume content"""
        all_errors = []

        # Validate personal info
        personal_info = content.get('personal_info', {})
        is_valid, errors = ResumeValidator.validate_personal_info(personal_info)
        all_errors.extend(errors)

        # Validate work experience
        work_experience = content.get('work_experience', [])
        is_valid, errors = ResumeValidator.validate_work_experience(work_experience)
        all_errors.extend(errors)

        # Validate education
        education = content.get('education', [])
        is_valid, errors = ResumeValidator.validate_education(education)
        all_errors.extend(errors)

        # Validate skills
        skills = content.get('skills', {})
        is_valid, errors = ResumeValidator.validate_skills(skills)
        all_errors.extend(errors)

        # Validate certifications
        certifications = content.get('certifications', [])
        if certifications:
            is_valid, errors = ResumeValidator.validate_certifications(certifications)
            all_errors.extend(errors)

        # Validate projects
        projects = content.get('projects', [])
        if projects:
            is_valid, errors = ResumeValidator.validate_projects(projects)
            all_errors.extend(errors)

        # Validate languages
        languages = content.get('languages', [])
        if languages:
            is_valid, errors = ResumeValidator.validate_languages(languages)
            all_errors.extend(errors)

        return len(all_errors) == 0, all_errors