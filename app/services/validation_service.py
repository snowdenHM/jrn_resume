from typing import Dict, List, Any, Optional
import logging

from app.utils.validators import ResumeValidator
from app.schemas.resume import ResumeValidation

logger = logging.getLogger(__name__)


class ValidationService:
    """Service for validating resume content and providing recommendations"""

    def __init__(self):
        self.validator = ResumeValidator()

    def validate_resume_content(self, content: Dict[str, Any]) -> ResumeValidation:
        """Validate complete resume content and return validation results"""
        try:
            is_valid, validation_errors = self.validator.validate_resume_content(content)

            # Calculate completeness
            completeness_data = self._calculate_completeness(content)

            # Generate recommendations
            recommendations = self._generate_recommendations(content, validation_errors)

            # Calculate overall score
            score = self._calculate_resume_score(content, completeness_data['percentage'])

            return ResumeValidation(
                is_valid=is_valid,
                completeness_percentage=completeness_data['percentage'],
                validation_errors=validation_errors,
                recommendations=recommendations,
                missing_required_fields=completeness_data['missing_sections'],
                score=score
            )
        except Exception as e:
            logger.error(f"Error validating resume content: {e}")
            raise

    def _calculate_completeness(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate resume completeness percentage"""
        sections = {
            'personal_info': content.get('personal_info', {}),
            'professional_summary': content.get('professional_summary'),
            'work_experience': content.get('work_experience', []),
            'education': content.get('education', []),
            'skills': content.get('skills', {}),
        }

        optional_sections = {
            'certifications': content.get('certifications', []),
            'projects': content.get('projects', []),
            'languages': content.get('languages', [])
        }

        completed_sections = 0
        total_sections = len(sections)
        missing_sections = []

        # Check required sections
        for section_name, section_data in sections.items():
            if self._is_section_complete(section_data):
                completed_sections += 1
            else:
                missing_sections.append(section_name)

        # Add bonus for optional sections
        optional_completed = 0
        for section_name, section_data in optional_sections.items():
            if self._is_section_complete(section_data):
                optional_completed += 1

        # Base percentage from required sections
        base_percentage = int((completed_sections / total_sections) * 85)

        # Bonus from optional sections (up to 15%)
        bonus_percentage = min(15, int((optional_completed / len(optional_sections)) * 15))

        total_percentage = min(100, base_percentage + bonus_percentage)

        return {
            'percentage': total_percentage,
            'completed_sections': completed_sections,
            'total_sections': total_sections,
            'missing_sections': missing_sections,
            'optional_completed': optional_completed
        }

    def _is_section_complete(self, section_data: Any) -> bool:
        """Check if a section is complete"""
        if not section_data:
            return False

        if isinstance(section_data, list):
            return len(section_data) > 0
        elif isinstance(section_data, dict):
            return len(section_data) > 0
        elif isinstance(section_data, str):
            return section_data.strip() != ""

        return bool(section_data)

    def _generate_recommendations(self, content: Dict[str, Any], validation_errors: List[str]) -> List[str]:
        """Generate recommendations for improving the resume"""
        recommendations = []

        # Basic content recommendations
        if not content.get('professional_summary'):
            recommendations.append("Add a professional summary to highlight your key qualifications")
        elif len(content.get('professional_summary', '')) < 50:
            recommendations.append("Expand your professional summary to better showcase your expertise")

        # Work experience recommendations
        work_exp = content.get('work_experience', [])
        if not work_exp:
            recommendations.append("Add work experience to demonstrate your professional background")
        else:
            for i, job in enumerate(work_exp):
                responsibilities = job.get('responsibilities', [])
                if len(responsibilities) < 3:
                    recommendations.append(
                        f"Add more responsibilities for your {job.get('job_title', 'position')} role")

                # Check for quantifiable achievements
                has_numbers = any(any(char.isdigit() for char in resp) for resp in responsibilities)
                if not has_numbers:
                    recommendations.append(
                        "Include quantifiable achievements in your work experience (numbers, percentages, metrics)")

        # Education recommendations
        education = content.get('education', [])
        if not education:
            recommendations.append("Add your educational background")

        # Skills recommendations
        skills = content.get('skills', {})
        if not skills or sum(len(skill_list) for skill_list in skills.values()) < 5:
            recommendations.append("Add more relevant skills to highlight your technical and soft skills")

        # Optional sections recommendations
        if not content.get('certifications'):
            recommendations.append("Consider adding relevant certifications to strengthen your profile")

        if not content.get('projects'):
            recommendations.append("Add projects to showcase your practical experience and skills")

        if not content.get('languages') and self._appears_multilingual(content):
            recommendations.append("Add language skills if you're multilingual")

        # URL recommendations
        personal_info = content.get('personal_info', {})
        if not personal_info.get('linkedin_url'):
            recommendations.append("Add your LinkedIn profile URL to increase professional visibility")

        if self._appears_technical(content) and not personal_info.get('github_url'):
            recommendations.append("Add your GitHub profile to showcase your coding projects")

        # Format recommendations
        if validation_errors:
            recommendations.append("Fix the validation errors mentioned above to improve resume quality")

        return recommendations[:10]  # Limit to top 10 recommendations

    def _appears_multilingual(self, content: Dict[str, Any]) -> bool:
        """Check if the person appears to be multilingual based on content"""
        # Simple heuristic: check for international experience or non-English names
        personal_info = content.get('personal_info', {})
        work_exp = content.get('work_experience', [])
        education = content.get('education', [])

        # Check for international locations
        international_keywords = ['international', 'global', 'abroad', 'overseas']
        all_text = str(personal_info) + str(work_exp) + str(education)

        return any(keyword in all_text.lower() for keyword in international_keywords)

    def _appears_technical(self, content: Dict[str, Any]) -> bool:
        """Check if the person appears to be in a technical field"""
        technical_keywords = [
            'developer', 'engineer', 'programmer', 'software', 'data',
            'python', 'java', 'javascript', 'react', 'angular', 'node',
            'ml', 'ai', 'machine learning', 'artificial intelligence',
            'devops', 'cloud', 'aws', 'azure', 'docker', 'kubernetes'
        ]

        # Check job titles, skills, and projects
        work_exp = content.get('work_experience', [])
        skills = content.get('skills', {})
        projects = content.get('projects', [])

        all_text = str(work_exp) + str(skills) + str(projects)

        return any(keyword in all_text.lower() for keyword in technical_keywords)

    def _calculate_resume_score(self, content: Dict[str, Any], completeness_percentage: int) -> int:
        """Calculate overall resume score (0-100)"""
        score = completeness_percentage * 0.6  # 60% weight for completeness

        # Quality factors (40% weight)
        quality_score = 0

        # Professional summary quality
        summary = content.get('professional_summary', '')
        if summary:
            if len(summary) >= 100:
                quality_score += 5
            if len(summary.split()) >= 20:
                quality_score += 5

        # Work experience quality
        work_exp = content.get('work_experience', [])
        if work_exp:
            avg_responsibilities = sum(len(job.get('responsibilities', [])) for job in work_exp) / len(work_exp)
            if avg_responsibilities >= 3:
                quality_score += 10

            # Check for quantifiable achievements
            has_metrics = any(
                any(char.isdigit() for char in str(job.get('responsibilities', [])))
                for job in work_exp
            )
            if has_metrics:
                quality_score += 10

        # Skills diversity
        skills = content.get('skills', {})
        total_skills = sum(len(skill_list) for skill_list in skills.values())
        if total_skills >= 10:
            quality_score += 5
        if len(skills.keys()) >= 2:  # Multiple skill categories
            quality_score += 5

        # Additional sections bonus
        optional_sections = ['certifications', 'projects', 'languages']
        for section in optional_sections:
            if content.get(section):
                quality_score += 2

        # Professional links
        personal_info = content.get('personal_info', {})
        if personal_info.get('linkedin_url'):
            quality_score += 3
        if personal_info.get('portfolio_url') or personal_info.get('github_url'):
            quality_score += 2

        # Combine scores
        total_score = min(100, int(score + quality_score * 0.4))

        return total_score

    def validate_section(self, section_type: str, section_data: Any) -> ResumeValidation:
        """Validate a specific resume section"""
        try:
            validation_methods = {
                'personal_info': self.validator.validate_personal_info,
                'work_experience': self.validator.validate_work_experience,
                'education': self.validator.validate_education,
                'skills': self.validator.validate_skills,
                'certifications': self.validator.validate_certifications,
                'projects': self.validator.validate_projects,
                'languages': self.validator.validate_languages,
            }

            if section_type not in validation_methods:
                return ResumeValidation(
                    is_valid=False,
                    completeness_percentage=0,
                    validation_errors=[f"Unknown section type: {section_type}"],
                    recommendations=[],
                    missing_required_fields=[]
                )

            is_valid, errors = validation_methods[section_type](section_data)

            return ResumeValidation(
                is_valid=is_valid,
                completeness_percentage=100 if is_valid else 0,
                validation_errors=errors,
                recommendations=[],
                missing_required_fields=[]
            )
        except Exception as e:
            logger.error(f"Error validating section {section_type}: {e}")
            raise