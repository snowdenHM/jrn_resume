import logging
import re
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class ATSScorer:
    """Advanced ATS scoring utility with multiple algorithms"""

    def __init__(self):
        self.section_weights = {
            "personal_info": 0.10,
            "professional_summary": 0.15,
            "work_experience": 0.35,
            "education": 0.15,
            "skills": 0.20,
            "certifications": 0.05
        }

        self.formatting_criteria = {
            "consistent_formatting": 15,
            "clear_section_headers": 10,
            "contact_information": 10,
            "chronological_order": 10,
            "readable_fonts": 5,
            "appropriate_length": 10,
            "bullet_points": 5,
            "white_space": 5
        }

        self.content_quality_factors = {
            "quantified_achievements": 25,
            "action_verbs": 15,
            "relevant_keywords": 20,
            "complete_information": 15,
            "no_typos": 10,
            "professional_language": 10,
            "job_relevance": 5
        }

    def calculate_comprehensive_score(
            self,
            resume_content: Dict[str, Any],
            job_description: str = None,
            industry: str = None
    ) -> Dict[str, Any]:
        """Calculate comprehensive ATS score with detailed breakdown"""

        scores = {}

        # 1. Formatting Score
        scores['formatting'] = self._score_formatting(resume_content)

        # 2. Content Quality Score
        scores['content_quality'] = self._score_content_quality(resume_content)

        # 3. Keyword Relevance Score
        scores['keyword_relevance'] = self._score_keyword_relevance(
            resume_content, job_description, industry
        )

        # 4. Section Completeness Score
        scores['section_completeness'] = self._score_section_completeness(resume_content)

        # 5. ATS Compatibility Score
        scores['ats_compatibility'] = self._score_ats_compatibility(resume_content)

        # 6. Industry Alignment Score
        scores['industry_alignment'] = self._score_industry_alignment(resume_content, industry)

        # Calculate weighted overall score
        weights = {
            'formatting': 0.15,
            'content_quality': 0.25,
            'keyword_relevance': 0.25,
            'section_completeness': 0.15,
            'ats_compatibility': 0.10,
            'industry_alignment': 0.10
        }

        overall_score = sum(scores[key] * weights[key] for key in scores.keys())

        return {
            'overall_score': round(overall_score, 1),
            'detailed_scores': scores,
            'score_breakdown': self._generate_score_breakdown(scores),
            'improvement_areas': self._identify_improvement_areas(scores)
        }

    def _score_formatting(self, resume_content: Dict[str, Any]) -> float:
        """Score resume formatting for ATS compatibility"""
        score = 0
        max_score = 100

        # Check section presence and structure
        required_sections = ['personal_info', 'work_experience', 'education', 'skills']
        present_sections = [section for section in required_sections if resume_content.get(section)]
        score += (len(present_sections) / len(required_sections)) * 30

        # Check personal information completeness
        personal_info = resume_content.get('personal_info', {})
        required_personal = ['first_name', 'last_name', 'email', 'phone']
        present_personal = [field for field in required_personal if personal_info.get(field)]
        score += (len(present_personal) / len(required_personal)) * 20

        # Check work experience structure
        work_exp = resume_content.get('work_experience', [])
        if work_exp:
            structured_jobs = 0
            for job in work_exp:
                if (job.get('job_title') and job.get('company') and
                        job.get('start_date') and job.get('responsibilities')):
                    structured_jobs += 1
            score += (structured_jobs / len(work_exp)) * 25

        # Check education structure
        education = resume_content.get('education', [])
        if education:
            structured_edu = 0
            for edu in education:
                if edu.get('degree') and edu.get('institution') and edu.get('graduation_year'):
                    structured_edu += 1
            score += (structured_edu / len(education)) * 15

        # Check skills organization
        skills = resume_content.get('skills', {})
        if skills and isinstance(skills, dict):
            score += 10

        return min(max_score, score)

    def _score_content_quality(self, resume_content: Dict[str, Any]) -> float:
        """Score content quality and depth"""
        score = 0
        max_score = 100

        # Professional summary quality
        summary = resume_content.get('professional_summary', '')
        if summary:
            if len(summary.split()) >= 20:
                score += 15
            elif len(summary.split()) >= 10:
                score += 10
            else:
                score += 5

        # Work experience depth
        work_exp = resume_content.get('work_experience', [])
        if work_exp:
            total_responsibilities = sum(len(job.get('responsibilities', [])) for job in work_exp)
            avg_responsibilities = total_responsibilities / len(work_exp)

            if avg_responsibilities >= 4:
                score += 25
            elif avg_responsibilities >= 3:
                score += 20
            elif avg_responsibilities >= 2:
                score += 15
            else:
                score += 10

        # Check for quantified achievements
        has_numbers = self._check_quantified_achievements(resume_content)
        if has_numbers:
            score += 20

        # Action verbs usage
        action_verb_score = self._score_action_verbs(resume_content)
        score += action_verb_score * 0.15

        # Skills diversity
        skills = resume_content.get('skills', {})
        total_skills = sum(len(skill_list) for skill_list in skills.values()
                           if isinstance(skill_list, list))

        if total_skills >= 15:
            score += 15
        elif total_skills >= 10:
            score += 12
        elif total_skills >= 5:
            score += 8
        else:
            score += 3

        # Additional sections bonus
        bonus_sections = ['certifications', 'projects', 'languages']
        present_bonus = sum(1 for section in bonus_sections if resume_content.get(section))
        score += present_bonus * 5

        return min(max_score, score)

    def _score_keyword_relevance(
            self,
            resume_content: Dict[str, Any],
            job_description: str = None,
            industry: str = None
    ) -> float:
        """Score keyword relevance and density"""
        if not job_description and not industry:
            return 50  # Default score when no reference available

        score = 0
        max_score = 100

        resume_text = self._extract_all_text(resume_content)
        resume_keywords = self._extract_keywords_simple(resume_text)

        if job_description:
            job_keywords = self._extract_keywords_simple(job_description)

            # Calculate keyword overlap
            if job_keywords:
                matched_keywords = set(resume_keywords) & set(job_keywords)
                match_ratio = len(matched_keywords) / len(job_keywords)
                score += match_ratio * 60

        # Industry-specific keyword check
        if industry:
            industry_keywords = self._get_industry_keywords_simple(industry)
            if industry_keywords:
                industry_matched = set(resume_keywords) & set(industry_keywords)
                industry_ratio = len(industry_matched) / len(industry_keywords)
                score += industry_ratio * 40

        # Keyword density check (optimal range)
        keyword_density = len(resume_keywords) / len(resume_text.split()) * 100
        if 3 <= keyword_density <= 8:
            score += 20
        elif 1 <= keyword_density <= 12:
            score += 10

        return min(max_score, score)

    def _score_section_completeness(self, resume_content: Dict[str, Any]) -> float:
        """Score completeness of resume sections"""
        score = 0
        max_score = 100

        # Essential sections (70% of score)
        essential_sections = {
            'personal_info': 20,
            'work_experience': 25,
            'education': 15,
            'skills': 10
        }

        for section, weight in essential_sections.items():
            section_data = resume_content.get(section)
            if section_data:
                if section == 'personal_info':
                    required_fields = ['first_name', 'last_name', 'email', 'phone']
                    present_fields = sum(1 for field in required_fields if section_data.get(field))
                    section_score = (present_fields / len(required_fields)) * weight
                elif section in ['work_experience', 'education']:
                    if isinstance(section_data, list) and len(section_data) > 0:
                        section_score = weight
                    else:
                        section_score = weight * 0.5
                elif section == 'skills':
                    if isinstance(section_data, dict) and any(section_data.values()):
                        section_score = weight
                    else:
                        section_score = weight * 0.5
                else:
                    section_score = weight

                score += section_score

        # Optional sections (30% of score)
        optional_sections = ['professional_summary', 'certifications', 'projects', 'languages']
        present_optional = sum(1 for section in optional_sections if resume_content.get(section))
        score += (present_optional / len(optional_sections)) * 30

        return min(max_score, score)

    def _score_ats_compatibility(self, resume_content: Dict[str, Any]) -> float:
        """Score ATS parsing compatibility"""
        score = 100  # Start with perfect score and deduct for issues

        # Check for ATS-unfriendly elements
        issues = []

        # Check for overly complex formatting indicators
        resume_text = self._extract_all_text(resume_content)

        # Too many special characters
        special_chars = re.findall(r'[^\w\s.,;:()\-/]', resume_text)
        if len(special_chars) > 20:
            score -= 10
            issues.append("Too many special characters")

        # Check section organization
        required_sections = ['personal_info', 'work_experience', 'education']
        for section in required_sections:
            if not resume_content.get(section):
                score -= 15
                issues.append(f"Missing {section} section")

        # Check date formatting consistency
        work_exp = resume_content.get('work_experience', [])
        date_formats = []
        for job in work_exp:
            if job.get('start_date'):
                date_formats.append(job['start_date'])
            if job.get('end_date'):
                date_formats.append(job['end_date'])

        if date_formats:
            # Check if dates follow YYYY-MM pattern
            consistent_dates = all(re.match(r'^\d{4}-\d{2}', date) for date in date_formats)
            if not consistent_dates:
                score -= 10
                issues.append("Inconsistent date formatting")

            # Check for proper contact information
            personal_info = resume_content.get('personal_info', {})
            email = personal_info.get('email', '')
            phone = personal_info.get('phone', '')

            if email and not re.match(r'^[^@]+@[^@]+\.[^@]+', email):
                score -= 5
                issues.append("Invalid email format")

            if phone and len(re.sub(r'\D', '', phone)) < 10:
                score -= 5
                issues.append("Invalid phone format")

        return max(0, score)

    def _score_industry_alignment(self, resume_content: Dict[str, Any], industry: str = None) -> float:
        """Score alignment with industry expectations"""
        if not industry:
            return 50  # Neutral score when industry unknown

        score = 0
        max_score = 100

        resume_text = self._extract_all_text(resume_content).lower()

        # Industry-specific scoring
        if industry.lower() == 'technology':
            score += self._score_tech_alignment(resume_content, resume_text)
        elif industry.lower() == 'healthcare':
            score += self._score_healthcare_alignment(resume_content, resume_text)
        elif industry.lower() == 'finance':
            score += self._score_finance_alignment(resume_content, resume_text)
        else:
            # General professional alignment
            score += self._score_general_alignment(resume_content, resume_text)

        return min(max_score, score)

    def _score_tech_alignment(self, resume_content: Dict[str, Any], resume_text: str) -> float:
        """Score alignment with technology industry"""
        score = 0

        # Technical skills presence
        skills = resume_content.get('skills', {})
        tech_skills = skills.get('technical', []) or skills.get('languages', [])
        if tech_skills and len(tech_skills) >= 5:
            score += 30
        elif tech_skills and len(tech_skills) >= 3:
            score += 20

        # Programming languages
        prog_languages = ['python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'go', 'rust']
        found_languages = [lang for lang in prog_languages if lang in resume_text]
        score += min(20, len(found_languages) * 5)

        # Frameworks and tools
        frameworks = ['react', 'angular', 'django', 'spring', 'node', 'docker', 'kubernetes']
        found_frameworks = [fw for fw in frameworks if fw in resume_text]
        score += min(15, len(found_frameworks) * 3)

        # Projects section
        projects = resume_content.get('projects', [])
        if projects and len(projects) >= 2:
            score += 15
        elif projects:
            score += 10

        # Technical certifications
        certifications = resume_content.get('certifications', [])
        tech_certs = ['aws', 'azure', 'google cloud', 'oracle', 'cisco', 'microsoft']
        found_certs = [cert for cert in certifications
                       if any(tc in str(cert).lower() for tc in tech_certs)]
        score += min(10, len(found_certs) * 5)

        # GitHub/portfolio presence
        personal_info = resume_content.get('personal_info', {})
        if personal_info.get('github_url') or personal_info.get('portfolio_url'):
            score += 10

        return score

    def _score_healthcare_alignment(self, resume_content: Dict[str, Any], resume_text: str) -> float:
        """Score alignment with healthcare industry"""
        score = 0

        # Healthcare keywords
        healthcare_terms = ['patient', 'clinical', 'medical', 'healthcare', 'nursing', 'therapy']
        found_terms = [term for term in healthcare_terms if term in resume_text]
        score += min(30, len(found_terms) * 5)

        # Healthcare certifications
        certifications = resume_content.get('certifications', [])
        healthcare_certs = ['rn', 'lpn', 'cna', 'md', 'np', 'pa', 'cpr', 'bls', 'acls']
        found_certs = [cert for cert in certifications
                       if any(hc in str(cert).lower() for hc in healthcare_certs)]
        score += min(25, len(found_certs) * 8)

        # Clinical experience
        work_exp = resume_content.get('work_experience', [])
        clinical_exp = [job for job in work_exp
                        if any(term in str(job).lower() for term in ['clinical', 'hospital', 'clinic', 'patient'])]
        score += min(25, len(clinical_exp) * 8)

        # Education in healthcare field
        education = resume_content.get('education', [])
        healthcare_degrees = ['nursing', 'medicine', 'health', 'biology', 'psychology']
        healthcare_edu = [edu for edu in education
                          if any(deg in str(edu).lower() for deg in healthcare_degrees)]
        score += min(20, len(healthcare_edu) * 10)

        return score

    def _score_finance_alignment(self, resume_content: Dict[str, Any], resume_text: str) -> float:
        """Score alignment with finance industry"""
        score = 0

        # Finance keywords
        finance_terms = ['financial', 'investment', 'banking', 'accounting', 'analysis', 'risk']
        found_terms = [term for term in finance_terms if term in resume_text]
        score += min(25, len(found_terms) * 4)

        # Financial software/tools
        finance_tools = ['excel', 'bloomberg', 'quickbooks', 'sap', 'oracle financials']
        found_tools = [tool for tool in finance_tools if tool in resume_text]
        score += min(20, len(found_tools) * 5)

        # Quantified achievements (especially important in finance)
        if self._check_quantified_achievements(resume_content):
            score += 25

        # Finance certifications
        certifications = resume_content.get('certifications', [])
        finance_certs = ['cpa', 'cfa', 'frm', 'mba', 'series 7', 'series 66']
        found_certs = [cert for cert in certifications
                       if any(fc in str(cert).lower() for fc in finance_certs)]
        score += min(20, len(found_certs) * 10)

        # Finance education
        education = resume_content.get('education', [])
        finance_degrees = ['finance', 'accounting', 'economics', 'business', 'mba']
        finance_edu = [edu for edu in education
                       if any(deg in str(edu).lower() for deg in finance_degrees)]
        score += min(10, len(finance_edu) * 5)

        return score

    def _score_general_alignment(self, resume_content: Dict[str, Any], resume_text: str) -> float:
        """Score general professional alignment"""
        score = 50  # Base score for any industry

        # Professional language check
        professional_terms = ['managed', 'led', 'developed', 'implemented', 'achieved', 'improved']
        found_terms = [term for term in professional_terms if term in resume_text]
        score += min(20, len(found_terms) * 3)

        # Quantified achievements
        if self._check_quantified_achievements(resume_content):
            score += 15

        # Professional summary
        if resume_content.get('professional_summary'):
            score += 10

        # Multiple work experiences
        work_exp = resume_content.get('work_experience', [])
        if len(work_exp) >= 3:
            score += 5

        return min(100, score)

    def _check_quantified_achievements(self, resume_content: Dict[str, Any]) -> bool:
        """Check if resume contains quantified achievements"""
        work_exp = resume_content.get('work_experience', [])

        for job in work_exp:
            responsibilities = job.get('responsibilities', [])
            for resp in responsibilities:
                # Look for numbers, percentages, dollar amounts
                if re.search(r'\d+[%$]?|\$\d+|increased by|reduced by|improved by', resp.lower()):
                    return True

        return False

    def _score_action_verbs(self, resume_content: Dict[str, Any]) -> float:
        """Score usage of strong action verbs"""
        action_verbs = {
            'achieved', 'administered', 'analyzed', 'built', 'created', 'developed',
            'implemented', 'improved', 'increased', 'led', 'managed', 'organized',
            'reduced', 'streamlined', 'supervised', 'designed', 'executed', 'delivered'
        }

        work_exp = resume_content.get('work_experience', [])
        found_verbs = set()

        for job in work_exp:
            responsibilities = job.get('responsibilities', [])
            for resp in responsibilities:
                words = resp.lower().split()
                if words:
                    first_word = words[0].rstrip('.,!?:;')
                    if first_word in action_verbs:
                        found_verbs.add(first_word)

        return min(100, len(found_verbs) * 10)

    def _extract_all_text(self, resume_content: Dict[str, Any]) -> str:
        """Extract all text from resume for analysis"""
        text_parts = []

        # Personal info
        personal_info = resume_content.get('personal_info', {})
        text_parts.extend([
            personal_info.get('first_name', ''),
            personal_info.get('last_name', '')
        ])

        # Professional summary
        if resume_content.get('professional_summary'):
            text_parts.append(resume_content['professional_summary'])

        # Work experience
        for job in resume_content.get('work_experience', []):
            text_parts.extend([
                job.get('job_title', ''),
                job.get('company', ''),
                ' '.join(job.get('responsibilities', []))
            ])

        # Education
        for edu in resume_content.get('education', []):
            text_parts.extend([
                edu.get('degree', ''),
                edu.get('institution', ''),
                edu.get('field_of_study', '')
            ])

        # Skills
        skills = resume_content.get('skills', {})
        for skill_category in skills.values():
            if isinstance(skill_category, list):
                text_parts.extend(skill_category)

        # Projects
        for project in resume_content.get('projects', []):
            text_parts.extend([
                project.get('name', ''),
                project.get('description', ''),
                ' '.join(project.get('technologies', []))
            ])

        # Certifications
        for cert in resume_content.get('certifications', []):
            text_parts.extend([
                cert.get('name', ''),
                cert.get('issuer', '')
            ])

        return ' '.join(filter(None, text_parts))

    def _extract_keywords_simple(self, text: str) -> List[str]:
        """Simple keyword extraction"""
        if not text:
            return []

        # Clean text and extract meaningful words
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = text.split()

        # Filter out stop words and short words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]

        return keywords

    def _get_industry_keywords_simple(self, industry: str) -> List[str]:
        """Get simple industry keywords"""
        industry_keywords = {
            'technology': ['software', 'development', 'programming', 'coding', 'agile', 'api', 'database'],
            'healthcare': ['patient', 'clinical', 'medical', 'healthcare', 'treatment', 'diagnosis'],
            'finance': ['financial', 'investment', 'banking', 'accounting', 'analysis', 'budget'],
            'marketing': ['marketing', 'campaign', 'brand', 'social', 'digital', 'analytics'],
            'sales': ['sales', 'revenue', 'client', 'customer', 'negotiation', 'target']
        }

        return industry_keywords.get(industry.lower(), [])

    def _generate_score_breakdown(self, scores: Dict[str, float]) -> Dict[str, Any]:
        """Generate detailed score breakdown"""
        breakdown = {}

        for category, score in scores.items():
            if score >= 80:
                level = "Excellent"
                color = "green"
            elif score >= 60:
                level = "Good"
                color = "blue"
            elif score >= 40:
                level = "Fair"
                color = "orange"
            else:
                level = "Needs Improvement"
                color = "red"

            breakdown[category] = {
                "score": round(score, 1),
                "level": level,
                "color": color
            }

        return breakdown

    def _identify_improvement_areas(self, scores: Dict[str, float]) -> List[str]:
        """Identify areas that need improvement"""
        improvement_areas = []

        thresholds = {
            'formatting': 70,
            'content_quality': 65,
            'keyword_relevance': 60,
            'section_completeness': 75,
            'ats_compatibility': 80,
            'industry_alignment': 55
        }

        priority_order = [
            'ats_compatibility',
            'section_completeness',
            'formatting',
            'content_quality',
            'keyword_relevance',
            'industry_alignment'
        ]

        for category in priority_order:
            if scores.get(category, 0) < thresholds[category]:
                improvement_areas.append(category)

        return improvement_areas[:3]  # Return top 3 priority areas
