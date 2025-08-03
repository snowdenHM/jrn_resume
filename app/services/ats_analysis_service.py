from typing import Dict, List, Any, Optional, Tuple
import re
import logging
from datetime import datetime
from collections import Counter
import math

from app.schemas.ats import ATSAnalysisResult, ATSRecommendation, KeywordAnalysis, SkillGapAnalysis
from app.utils.ats_keywords import ATSKeywordMatcher
from app.utils.ats_scoring import ATSScorer

logger = logging.getLogger(__name__)


class ATSAnalysisService:
    """Service for analyzing resumes for ATS compatibility and scoring"""

    def __init__(self):
        self.keyword_matcher = ATSKeywordMatcher()
        self.scorer = ATSScorer()
        self.min_resume_length = 200
        self.optimal_resume_length = 600
        self.max_resume_length = 1000

    async def analyze_resume(
            self,
            resume_content: Dict[str, Any],
            job_description: Optional[str] = None,
            target_industry: Optional[str] = None
    ) -> ATSAnalysisResult:
        """Comprehensive ATS analysis of resume content"""
        try:
            logger.info("Starting ATS analysis for resume")

            # Extract text content from resume
            resume_text = self._extract_resume_text(resume_content)

            # Perform various analyses
            formatting_score = self._analyze_formatting(resume_content)
            keyword_analysis = await self._analyze_keywords(resume_content, job_description, target_industry)
            content_analysis = self._analyze_content_structure(resume_content)
            readability_score = self._analyze_readability(resume_text)

            # Calculate overall ATS score
            overall_score = self._calculate_overall_ats_score(
                formatting_score, keyword_analysis, content_analysis, readability_score
            )

            # Generate recommendations
            recommendations = self._generate_ats_recommendations(
                resume_content, formatting_score, keyword_analysis,
                content_analysis, readability_score, job_description
            )

            # Skill gap analysis
            skill_gaps = await self._analyze_skill_gaps(
                resume_content, job_description, target_industry
            )

            # Industry-specific insights
            industry_insights = self._get_industry_insights(target_industry, resume_content)

            result = ATSAnalysisResult(
                overall_ats_score=overall_score,
                formatting_score=formatting_score['score'],
                keyword_score=keyword_analysis.score,
                content_structure_score=content_analysis['score'],
                readability_score=readability_score,
                keyword_analysis=keyword_analysis,
                skill_gaps=skill_gaps,
                recommendations=recommendations,
                industry_insights=industry_insights,
                analysis_timestamp=datetime.utcnow(),
                job_match_percentage=keyword_analysis.job_match_percentage if job_description else None
            )

            logger.info(f"ATS analysis completed. Overall score: {overall_score}")
            return result

        except Exception as e:
            logger.error(f"Error in ATS analysis: {e}")
            raise

    def _extract_resume_text(self, resume_content: Dict[str, Any]) -> str:
        """Extract all text content from resume for analysis"""
        text_parts = []

        # Personal info
        personal_info = resume_content.get('personal_info', {})
        text_parts.append(f"{personal_info.get('first_name', '')} {personal_info.get('last_name', '')}")

        # Professional summary
        if resume_content.get('professional_summary'):
            text_parts.append(resume_content['professional_summary'])

        # Work experience
        for job in resume_content.get('work_experience', []):
            text_parts.append(job.get('job_title', ''))
            text_parts.append(job.get('company', ''))
            text_parts.extend(job.get('responsibilities', []))

        # Education
        for edu in resume_content.get('education', []):
            text_parts.append(edu.get('degree', ''))
            text_parts.append(edu.get('institution', ''))
            text_parts.append(edu.get('field_of_study', ''))

        # Skills
        skills = resume_content.get('skills', {})
        for skill_category in skills.values():
            if isinstance(skill_category, list):
                text_parts.extend(skill_category)

        # Projects
        for project in resume_content.get('projects', []):
            text_parts.append(project.get('name', ''))
            text_parts.append(project.get('description', ''))
            text_parts.extend(project.get('technologies', []))

        # Certifications
        for cert in resume_content.get('certifications', []):
            text_parts.append(cert.get('name', ''))
            text_parts.append(cert.get('issuer', ''))

        return ' '.join(filter(None, text_parts))

    def _analyze_formatting(self, resume_content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze resume formatting for ATS compatibility"""
        score = 100
        issues = []
        recommendations = []

        # Check for required sections
        required_sections = ['personal_info', 'work_experience', 'education', 'skills']
        missing_sections = [section for section in required_sections
                            if not resume_content.get(section)]

        if missing_sections:
            score -= len(missing_sections) * 15
            issues.extend([f"Missing {section.replace('_', ' ').title()} section"
                           for section in missing_sections])

        # Check personal info completeness
        personal_info = resume_content.get('personal_info', {})
        required_personal_fields = ['first_name', 'last_name', 'email', 'phone']
        missing_personal = [field for field in required_personal_fields
                            if not personal_info.get(field)]

        if missing_personal:
            score -= len(missing_personal) * 5
            issues.extend([f"Missing {field.replace('_', ' ')}" for field in missing_personal])

        # Check for professional summary
        if not resume_content.get('professional_summary'):
            score -= 10
            issues.append("Missing professional summary")
            recommendations.append("Add a professional summary to highlight your key qualifications")

        # Check work experience structure
        work_exp = resume_content.get('work_experience', [])
        for i, job in enumerate(work_exp):
            if not job.get('job_title'):
                score -= 5
                issues.append(f"Work experience {i + 1}: Missing job title")
            if not job.get('company'):
                score -= 5
                issues.append(f"Work experience {i + 1}: Missing company name")
            if not job.get('responsibilities'):
                score -= 5
                issues.append(f"Work experience {i + 1}: Missing responsibilities")

        # Check for consistent date formatting
        date_formats = []
        for job in work_exp:
            if job.get('start_date'):
                date_formats.append(job['start_date'])
            if job.get('end_date'):
                date_formats.append(job['end_date'])

        # Simple date format consistency check
        if date_formats and len(set(len(date) for date in date_formats)) > 1:
            score -= 5
            issues.append("Inconsistent date formatting")
            recommendations.append("Use consistent date format (YYYY-MM) throughout resume")

        return {
            'score': max(0, score),
            'issues': issues,
            'recommendations': recommendations
        }

    async def _analyze_keywords(
            self,
            resume_content: Dict[str, Any],
            job_description: Optional[str] = None,
            target_industry: Optional[str] = None
    ) -> KeywordAnalysis:
        """Analyze keyword density and relevance"""
        resume_text = self._extract_resume_text(resume_content).lower()

        # Extract keywords from resume
        resume_keywords = self.keyword_matcher.extract_keywords(resume_text)

        # Industry-specific keywords
        industry_keywords = self.keyword_matcher.get_industry_keywords(target_industry) if target_industry else []

        # Job description analysis
        job_keywords = []
        job_match_percentage = None
        missing_keywords = []

        if job_description:
            job_keywords = self.keyword_matcher.extract_keywords(job_description.lower())

            # Calculate job match percentage
            matched_keywords = set(resume_keywords) & set(job_keywords)
            job_match_percentage = (len(matched_keywords) / len(job_keywords) * 100) if job_keywords else 0

            # Find missing important keywords
            missing_keywords = [kw for kw in job_keywords if kw not in resume_keywords][:10]

        # Calculate keyword score
        keyword_score = self._calculate_keyword_score(
            resume_keywords, job_keywords, industry_keywords, resume_text
        )

        return KeywordAnalysis(
            score=keyword_score,
            total_keywords=len(resume_keywords),
            industry_keywords=industry_keywords,
            job_keywords=job_keywords,
            matched_keywords=list(set(resume_keywords) & set(job_keywords)) if job_keywords else [],
            missing_keywords=missing_keywords,
            keyword_density=len(resume_keywords) / len(resume_text.split()) * 100,
            job_match_percentage=job_match_percentage
        )

    def _calculate_keyword_score(
            self,
            resume_keywords: List[str],
            job_keywords: List[str],
            industry_keywords: List[str],
            resume_text: str
    ) -> int:
        """Calculate keyword relevance score"""
        score = 0

        # Base score for having keywords
        if resume_keywords:
            score += min(50, len(resume_keywords) * 2)

        # Job match bonus
        if job_keywords:
            matched = set(resume_keywords) & set(job_keywords)
            match_ratio = len(matched) / len(job_keywords)
            score += int(match_ratio * 30)

        # Industry relevance bonus
        if industry_keywords:
            industry_matched = set(resume_keywords) & set(industry_keywords)
            industry_ratio = len(industry_matched) / len(industry_keywords)
            score += int(industry_ratio * 20)

        # Keyword density check (not too sparse, not too dense)
        word_count = len(resume_text.split())
        keyword_density = len(resume_keywords) / word_count * 100

        if 2 <= keyword_density <= 8:  # Optimal range
            score += 10
        elif keyword_density > 15:  # Too dense (keyword stuffing)
            score -= 10

        return min(100, max(0, score))

    def _analyze_content_structure(self, resume_content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze content structure and organization"""
        score = 100
        issues = []
        recommendations = []

        # Check resume length
        resume_text = self._extract_resume_text(resume_content)
        word_count = len(resume_text.split())

        if word_count < self.min_resume_length:
            score -= 20
            issues.append("Resume too short - may lack sufficient detail")
            recommendations.append(
                f"Expand resume content. Aim for {self.optimal_resume_length}-{self.max_resume_length} words")
        elif word_count > self.max_resume_length:
            score -= 10
            issues.append("Resume too long - may be overwhelming for recruiters")
            recommendations.append("Consider condensing content to focus on most relevant information")

        # Check work experience depth
        work_exp = resume_content.get('work_experience', [])
        if work_exp:
            avg_responsibilities = sum(len(job.get('responsibilities', [])) for job in work_exp) / len(work_exp)
            if avg_responsibilities < 2:
                score -= 15
                issues.append("Work experience lacks detail")
                recommendations.append("Add more specific responsibilities and achievements for each role")

        # Check for quantifiable achievements
        has_numbers = any(
            any(re.search(r'\d+', resp) for resp in job.get('responsibilities', []))
            for job in work_exp
        )
        if not has_numbers:
            score -= 15
            issues.append("Missing quantifiable achievements")
            recommendations.append("Include specific numbers, percentages, and metrics in your achievements")

        # Check skills organization
        skills = resume_content.get('skills', {})
        total_skills = sum(len(skill_list) for skill_list in skills.values() if isinstance(skill_list, list))

        if total_skills < 5:
            score -= 10
            issues.append("Limited skills listed")
            recommendations.append("Add more relevant technical and soft skills")
        elif total_skills > 30:
            score -= 5
            issues.append("Too many skills listed")
            recommendations.append("Focus on most relevant skills for your target role")

        # Check for action verbs in work experience
        action_verbs = {
            'achieved', 'administered', 'analyzed', 'built', 'created', 'developed',
            'implemented', 'improved', 'increased', 'led', 'managed', 'organized',
            'reduced', 'streamlined', 'supervised', 'designed', 'executed', 'delivered'
        }

        responsibilities_text = ' '.join([
            resp.lower() for job in work_exp
            for resp in job.get('responsibilities', [])
        ])

        used_action_verbs = [verb for verb in action_verbs if verb in responsibilities_text]
        if len(used_action_verbs) < 3:
            score -= 10
            issues.append("Limited use of strong action verbs")
            recommendations.append("Use more powerful action verbs to describe your accomplishments")

        return {
            'score': max(0, score),
            'word_count': word_count,
            'issues': issues,
            'recommendations': recommendations,
            'action_verbs_used': used_action_verbs
        }

    def _analyze_readability(self, resume_text: str) -> int:
        """Analyze resume readability and clarity"""
        if not resume_text:
            return 0

        sentences = re.split(r'[.!?]+', resume_text)
        sentences = [s.strip() for s in sentences if s.strip()]

        words = resume_text.split()

        if not sentences or not words:
            return 0

        # Calculate average sentence length
        avg_sentence_length = len(words) / len(sentences)

        # Calculate average word length
        avg_word_length = sum(len(word) for word in words) / len(words)

        # Simple readability score (higher is better for resumes)
        # Optimal: 10-20 words per sentence, 4-6 characters per word
        sentence_score = 100 - abs(avg_sentence_length - 15) * 2
        word_score = 100 - abs(avg_word_length - 5) * 10

        readability_score = (sentence_score + word_score) / 2

        return max(0, min(100, int(readability_score)))

    def _calculate_overall_ats_score(
            self,
            formatting_score: Dict[str, Any],
            keyword_analysis: KeywordAnalysis,
            content_analysis: Dict[str, Any],
            readability_score: int
    ) -> int:
        """Calculate weighted overall ATS score"""

        # Weighted scoring
        weights = {
            'formatting': 0.25,  # 25% - Basic structure and completeness
            'keywords': 0.35,  # 35% - Keyword relevance and density
            'content': 0.25,  # 25% - Content quality and structure
            'readability': 0.15  # 15% - Readability and clarity
        }

        overall_score = (
                formatting_score['score'] * weights['formatting'] +
                keyword_analysis.score * weights['keywords'] +
                content_analysis['score'] * weights['content'] +
                readability_score * weights['readability']
        )

        return int(overall_score)

    async def _analyze_skill_gaps(
            self,
            resume_content: Dict[str, Any],
            job_description: Optional[str] = None,
            target_industry: Optional[str] = None
    ) -> SkillGapAnalysis:
        """Analyze skill gaps compared to job requirements or industry standards"""

        current_skills = set()
        skills_section = resume_content.get('skills', {})

        # Extract all skills from resume
        for skill_category in skills_section.values():
            if isinstance(skill_category, list):
                current_skills.update([skill.lower() for skill in skill_category])

        # Get required skills from job description or industry
        required_skills = set()
        if job_description:
            required_skills.update(self.keyword_matcher.extract_skills_from_text(job_description))

        if target_industry:
            industry_skills = self.keyword_matcher.get_industry_skills(target_industry)
            required_skills.update(industry_skills)

        # Calculate gaps
        missing_skills = list(required_skills - current_skills)
        matching_skills = list(required_skills & current_skills)

        # Prioritize missing skills
        critical_missing = []
        important_missing = []
        nice_to_have_missing = []

        skill_priorities = self.keyword_matcher.get_skill_priorities(target_industry)

        for skill in missing_skills:
            if skill in skill_priorities.get('critical', []):
                critical_missing.append(skill)
            elif skill in skill_priorities.get('important', []):
                important_missing.append(skill)
            else:
                nice_to_have_missing.append(skill)

        # Calculate skill match percentage
        skill_match_percentage = (
            len(matching_skills) / len(required_skills) * 100
            if required_skills else 100
        )

        return SkillGapAnalysis(
            current_skills=list(current_skills),
            required_skills=list(required_skills),
            missing_skills=missing_skills,
            matching_skills=matching_skills,
            critical_missing=critical_missing,
            important_missing=important_missing,
            nice_to_have_missing=nice_to_have_missing,
            skill_match_percentage=skill_match_percentage
        )

    def _generate_ats_recommendations(
            self,
            resume_content: Dict[str, Any],
            formatting_score: Dict[str, Any],
            keyword_analysis: KeywordAnalysis,
            content_analysis: Dict[str, Any],
            readability_score: int,
            job_description: Optional[str] = None
    ) -> List[ATSRecommendation]:
        """Generate prioritized ATS improvement recommendations"""

        recommendations = []

        # High priority recommendations
        if formatting_score['score'] < 80:
            for issue in formatting_score['issues'][:3]:
                recommendations.append(ATSRecommendation(
                    category="formatting",
                    priority="high",
                    title="Fix Resume Structure",
                    description=issue,
                    impact="Improves ATS parsing accuracy",
                    action_items=[f"Address: {issue}"]
                ))

        if keyword_analysis.score < 70:
            recommendations.append(ATSRecommendation(
                category="keywords",
                priority="high",
                title="Improve Keyword Optimization",
                description="Your resume lacks relevant keywords for ATS systems",
                impact="Increases chances of passing initial ATS screening",
                action_items=[
                    "Add industry-specific keywords naturally throughout your resume",
                    "Include skill keywords in your experience descriptions",
                    "Optimize your professional summary with relevant terms"
                ]
            ))

        # Medium priority recommendations
        if keyword_analysis.job_match_percentage and keyword_analysis.job_match_percentage < 60:
            recommendations.append(ATSRecommendation(
                category="job_match",
                priority="medium",
                title="Improve Job Description Alignment",
                description=f"Only {keyword_analysis.job_match_percentage:.1f}% match with job requirements",
                impact="Better alignment with specific job requirements",
                action_items=[
                    f"Add these missing keywords: {', '.join(keyword_analysis.missing_keywords[:5])}",
                    "Tailor your experience descriptions to match job requirements",
                    "Include relevant skills mentioned in the job posting"
                ]
            ))

        if content_analysis['word_count'] < self.min_resume_length:
            recommendations.append(ATSRecommendation(
                category="content",
                priority="medium",
                title="Expand Resume Content",
                description="Resume is too brief and may lack sufficient detail",
                impact="Provides more context for ATS keyword matching",
                action_items=[
                    "Add more specific responsibilities and achievements",
                    "Include quantifiable results and metrics",
                    "Expand on technical skills and tools used"
                ]
            ))

        # Low priority recommendations
        if readability_score < 70:
            recommendations.append(ATSRecommendation(
                category="readability",
                priority="low",
                title="Improve Resume Clarity",
                description="Resume could be clearer and more readable",
                impact="Better human reviewer experience after ATS screening",
                action_items=[
                    "Use shorter, clearer sentences",
                    "Organize information in logical sections",
                    "Use consistent formatting throughout"
                ]
            ))

        if len(content_analysis.get('action_verbs_used', [])) < 5:
            recommendations.append(ATSRecommendation(
                category="content",
                priority="low",
                title="Use Stronger Action Verbs",
                description="Limited use of powerful action verbs in experience descriptions",
                impact="Makes achievements more impactful and ATS-friendly",
                action_items=[
                    "Start bullet points with strong action verbs",
                    "Use verbs like 'achieved', 'implemented', 'developed', 'led'",
                    "Avoid passive voice and weak language"
                ]
            ))

        return recommendations[:10]  # Limit to top 10 recommendations

    def _get_industry_insights(
            self,
            target_industry: Optional[str],
            resume_content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get industry-specific insights and benchmarks"""

        if not target_industry:
            return {}

        insights = {
            "industry": target_industry,
            "benchmarks": {},
            "trends": [],
            "recommendations": []
        }

        # Industry-specific benchmarks and insights
        industry_data = {
            "technology": {
                "avg_ats_score": 75,
                "key_sections": ["technical_skills", "projects", "certifications"],
                "trending_skills": ["AI/ML", "Cloud Computing", "DevOps", "Cybersecurity"],
                "typical_resume_length": "600-800 words"
            },
            "healthcare": {
                "avg_ats_score": 70,
                "key_sections": ["certifications", "clinical_experience", "education"],
                "trending_skills": ["Telemedicine", "Electronic Health Records", "Patient Care"],
                "typical_resume_length": "500-700 words"
            },
            "finance": {
                "avg_ats_score": 72,
                "key_sections": ["quantifiable_achievements", "certifications", "software_skills"],
                "trending_skills": ["Financial Modeling", "Risk Management", "Compliance"],
                "typical_resume_length": "550-750 words"
            }
        }

        industry_info = industry_data.get(target_industry.lower(), {})

        if industry_info:
            insights["benchmarks"] = {
                "average_ats_score": industry_info["avg_ats_score"],
                "recommended_length": industry_info["typical_resume_length"]
            }

            insights["trends"] = industry_info["trending_skills"]

            # Generate industry-specific recommendations
            current_skills = set()
            skills_section = resume_content.get('skills', {})
            for skill_list in skills_section.values():
                if isinstance(skill_list, list):
                    current_skills.update([s.lower() for s in skill_list])

            missing_trending = [
                skill for skill in industry_info["trending_skills"]
                if skill.lower() not in current_skills
            ]

            if missing_trending:
                insights["recommendations"].append(
                    f"Consider adding trending {target_industry} skills: {', '.join(missing_trending[:3])}"
                )

        return insights