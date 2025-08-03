from typing import Dict, List, Any, Optional, Tuple
import re
import logging
from datetime import datetime

from app.schemas.ats import ATSOptimizationSuggestion, ATSBenchmark
from app.utils.ats_keywords import ATSKeywordMatcher
from app.services.ats_analysis_service import ATSAnalysisService

logger = logging.getLogger(__name__)


class ATSEnhancementService:
    """Service for generating specific ATS optimization suggestions and enhancements"""

    def __init__(self):
        self.keyword_matcher = ATSKeywordMatcher()
        self.analysis_service = ATSAnalysisService()

        # Enhancement templates for different scenarios
        self.enhancement_templates = self._load_enhancement_templates()

    def _load_enhancement_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load templates for different types of enhancements"""
        return {
            "professional_summary": {
                "weak_patterns": [
                    r"^I am a",
                    r"^My name is",
                    r"^Looking for",
                    r"^Seeking"
                ],
                "improvement_phrases": [
                    "Results-driven {role} with {years}+ years of experience",
                    "Accomplished {role} specializing in {specialization}",
                    "Dynamic {role} with proven expertise in {key_skills}",
                    "Strategic {role} with a track record of {achievements}"
                ]
            },
            "work_experience": {
                "weak_starters": [
                    "responsible for",
                    "duties included",
                    "worked on",
                    "helped with",
                    "assisted in"
                ],
                "strong_starters": [
                    "Led", "Developed", "Implemented", "Achieved", "Improved",
                    "Optimized", "Streamlined", "Delivered", "Managed", "Created",
                    "Increased", "Reduced", "Enhanced", "Established", "Coordinated"
                ]
            },
            "skills_organization": {
                "categories": {
                    "technical": ["Programming Languages", "Technical Skills", "Technologies"],
                    "tools": ["Tools & Platforms", "Software", "Applications"],
                    "soft": ["Core Competencies", "Professional Skills", "Key Strengths"],
                    "certifications": ["Certifications", "Credentials", "Professional Licenses"]
                }
            }
        }

    async def generate_optimization_suggestions(
            self,
            resume_content: Dict[str, Any],
            job_description: Optional[str] = None,
            target_industry: Optional[str] = None,
            max_suggestions: int = 10
    ) -> List[ATSOptimizationSuggestion]:
        """Generate specific optimization suggestions with before/after examples"""

        suggestions = []

        try:
            # 1. Professional Summary Optimization
            summary_suggestions = await self._optimize_professional_summary(
                resume_content, job_description, target_industry
            )
            suggestions.extend(summary_suggestions)

            # 2. Work Experience Optimization
            experience_suggestions = await self._optimize_work_experience(
                resume_content, job_description, target_industry
            )
            suggestions.extend(experience_suggestions)

            # 3. Skills Section Optimization
            skills_suggestions = await self._optimize_skills_section(
                resume_content, job_description, target_industry
            )
            suggestions.extend(skills_suggestions)

            # 4. Keyword Integration Suggestions
            keyword_suggestions = await self._suggest_keyword_integration(
                resume_content, job_description, target_industry
            )
            suggestions.extend(keyword_suggestions)

            # 5. Formatting and Structure Suggestions
            formatting_suggestions = await self._suggest_formatting_improvements(
                resume_content
            )
            suggestions.extend(formatting_suggestions)

            # Sort by impact and limit results
            suggestions.sort(key=lambda x: self._calculate_suggestion_impact(x), reverse=True)

            return suggestions[:max_suggestions]

        except Exception as e:
            logger.error(f"Error generating optimization suggestions: {e}")
            raise

    async def _optimize_professional_summary(
            self,
            resume_content: Dict[str, Any],
            job_description: Optional[str] = None,
            target_industry: Optional[str] = None
    ) -> List[ATSOptimizationSuggestion]:
        """Generate professional summary optimization suggestions"""

        suggestions = []
        current_summary = resume_content.get('professional_summary', '')

        if not current_summary:
            # Suggest adding a professional summary
            work_exp = resume_content.get('work_experience', [])
            skills = resume_content.get('skills', {})

            if work_exp:
                most_recent_job = work_exp[0] if work_exp else {}
                job_title = most_recent_job.get('job_title', 'Professional')

                # Calculate years of experience
                years_exp = min(len(work_exp), 10)  # Cap at 10 years for summary

                # Get top skills
                all_skills = []
                for skill_category in skills.values():
                    if isinstance(skill_category, list):
                        all_skills.extend(skill_category[:3])  # Top 3 from each category

                top_skills = ', '.join(all_skills[:4]) if all_skills else 'key technologies'

                suggested_summary = (
                    f"Results-driven {job_title} with {years_exp}+ years of experience "
                    f"specializing in {top_skills}. Proven track record of delivering "
                    f"high-quality solutions and driving technical innovation."
                )

                suggestions.append(ATSOptimizationSuggestion(
                    section="professional_summary",
                    current_text="[No professional summary]",
                    suggested_text=suggested_summary,
                    improvement_reason="Adding a professional summary increases ATS keyword matching and provides hiring managers with a quick overview of your qualifications",
                    keywords_added=["results-driven", "experience", "specializing", "proven track record"]
                ))
        else:
            # Optimize existing summary
            weak_patterns = self.enhancement_templates["professional_summary"]["weak_patterns"]

            for pattern in weak_patterns:
                if re.search(pattern, current_summary, re.IGNORECASE):
                    # Extract key information
                    work_exp = resume_content.get('work_experience', [])
                    if work_exp:
                        job_title = work_exp[0].get('job_title', 'Professional')
                        years_exp = len(work_exp)

                        improved_start = f"Accomplished {job_title} with {years_exp}+ years of experience"
                        improved_summary = re.sub(pattern, improved_start, current_summary, flags=re.IGNORECASE)

                        suggestions.append(ATSOptimizationSuggestion(
                            section="professional_summary",
                            current_text=current_summary,
                            suggested_text=improved_summary,
                            improvement_reason="Starting with accomplishments and specific experience makes the summary more ATS-friendly and impactful",
                            keywords_added=["accomplished", "experience"]
                        ))
                        break

            # Check for missing keywords from job description
            if job_description:
                job_keywords = self.keyword_matcher.extract_keywords(job_description)
                summary_keywords = self.keyword_matcher.extract_keywords(current_summary)
                missing_keywords = [kw for kw in job_keywords[:5] if kw not in summary_keywords]

                if missing_keywords:
                    enhanced_summary = current_summary + f" Expertise includes {', '.join(missing_keywords[:3])}."

                    suggestions.append(ATSOptimizationSuggestion(
                        section="professional_summary",
                        current_text=current_summary,
                        suggested_text=enhanced_summary,
                        improvement_reason="Adding relevant keywords from the job description improves ATS matching",
                        keywords_added=missing_keywords[:3]
                    ))

        return suggestions

    async def _optimize_work_experience(
            self,
            resume_content: Dict[str, Any],
            job_description: Optional[str] = None,
            target_industry: Optional[str] = None
    ) -> List[ATSOptimizationSuggestion]:
        """Generate work experience optimization suggestions"""

        suggestions = []
        work_exp = resume_content.get('work_experience', [])

        weak_starters = self.enhancement_templates["work_experience"]["weak_starters"]
        strong_starters = self.enhancement_templates["work_experience"]["strong_starters"]

        for job_idx, job in enumerate(work_exp):
            responsibilities = job.get('responsibilities', [])

            for resp_idx, responsibility in enumerate(responsibilities):
                # Check for weak bullet point starters
                for weak_starter in weak_starters:
                    if responsibility.lower().startswith(weak_starter):
                        # Suggest stronger action verb
                        import random
                        strong_verb = random.choice(strong_starters)

                        # Extract the main action from the responsibility
                        main_action = responsibility[len(weak_starter):].strip()
                        improved_resp = f"{strong_verb} {main_action}"

                        suggestions.append(ATSOptimizationSuggestion(
                            section="work_experience",
                            current_text=responsibility,
                            suggested_text=improved_resp,
                            improvement_reason="Using strong action verbs at the start of bullet points makes achievements more impactful and ATS-friendly",
                            keywords_added=[strong_verb.lower()]
                        ))
                        break

                # Check for missing quantifiable metrics
                if not re.search(r'\d+[%$]?|\$\d+|increased|decreased|improved|reduced', responsibility.lower()):
                    # Suggest adding metrics (example)
                    if "managed" in responsibility.lower():
                        improved_resp = responsibility + " (team of X people, budget of $X)"
                        suggestions.append(ATSOptimizationSuggestion(
                            section="work_experience",
                            current_text=responsibility,
                            suggested_text=improved_resp,
                            improvement_reason="Adding quantifiable metrics makes achievements more credible and ATS-friendly",
                            keywords_added=["managed", "team", "budget"]
                        ))
                    elif "project" in responsibility.lower():
                        improved_resp = responsibility + " resulting in X% improvement"
                        suggestions.append(ATSOptimizationSuggestion(
                            section="work_experience",
                            current_text=responsibility,
                            suggested_text=improved_resp,
                            improvement_reason="Quantifying project outcomes demonstrates measurable impact",
                            keywords_added=["improvement", "results"]
                        ))

        return suggestions[:3]  # Limit to top 3 work experience suggestions

    async def _optimize_skills_section(
            self,
            resume_content: Dict[str, Any],
            job_description: Optional[str] = None,
            target_industry: Optional[str] = None
    ) -> List[ATSOptimizationSuggestion]:
        """Generate skills section optimization suggestions"""

        suggestions = []
        skills = resume_content.get('skills', {})

        # Check if skills are properly categorized
        if isinstance(skills, list) or not skills:
            # Suggest organizing skills into categories
            all_skills = skills if isinstance(skills, list) else []

            # Categorize skills automatically
            categorized_skills = {
                "Technical Skills": [],
                "Programming Languages": [],
                "Tools & Platforms": [],
                "Core Competencies": []
            }

            programming_keywords = ["python", "java", "javascript", "c++", "c#", "ruby", "go", "rust"]
            tool_keywords = ["excel", "salesforce", "jira", "confluence", "git", "docker", "kubernetes"]

            for skill in all_skills:
                skill_lower = skill.lower()
                if any(prog in skill_lower for prog in programming_keywords):
                    categorized_skills["Programming Languages"].append(skill)
                elif any(tool in skill_lower for tool in tool_keywords):
                    categorized_skills["Tools & Platforms"].append(skill)
                else:
                    categorized_skills["Technical Skills"].append(skill)

            # Remove empty categories
            categorized_skills = {k: v for k, v in categorized_skills.items() if v}

            suggestions.append(ATSOptimizationSuggestion(
                section="skills",
                current_text="Unorganized skills list",
                suggested_text=f"Organized into categories: {', '.join(categorized_skills.keys())}",
                improvement_reason="Organizing skills into clear categories improves ATS parsing and readability",
                keywords_added=list(categorized_skills.keys())
            ))

        # Check for missing industry-relevant skills
        if target_industry:
            industry_skills = self.keyword_matcher.get_industry_skills(target_industry)
            current_skills = []
            for skill_list in skills.values() if isinstance(skills, dict) else [skills]:
                if isinstance(skill_list, list):
                    current_skills.extend([s.lower() for s in skill_list])

            missing_skills = [skill for skill in industry_skills[:10]
                              if skill.lower() not in current_skills][:5]

            if missing_skills:
                suggestions.append(ATSOptimizationSuggestion(
                    section="skills",
                    current_text="Current skills list",
                    suggested_text=f"Add relevant {target_industry} skills: {', '.join(missing_skills)}",
                    improvement_reason=f"Adding industry-relevant skills improves ATS matching for {target_industry} positions",
                    keywords_added=missing_skills
                ))

        return suggestions

    async def _suggest_keyword_integration(
            self,
            resume_content: Dict[str, Any],
            job_description: Optional[str] = None,
            target_industry: Optional[str] = None
    ) -> List[ATSOptimizationSuggestion]:
        """Suggest natural keyword integration throughout resume"""

        suggestions = []

        if job_description:
            job_keywords = self.keyword_matcher.extract_keywords(job_description)
            resume_text = self._extract_resume_text(resume_content)
            resume_keywords = self.keyword_matcher.extract_keywords(resume_text)

            missing_keywords = [kw for kw in job_keywords[:10] if kw not in resume_keywords]

            if missing_keywords:
                # Suggest integrating keywords into different sections
                for keyword in missing_keywords[:3]:
                    # Suggest adding to professional summary
                    current_summary = resume_content.get('professional_summary', '')
                    if current_summary and keyword not in current_summary.lower():
                        enhanced_summary = current_summary + f" Experienced with {keyword}."

                        suggestions.append(ATSOptimizationSuggestion(
                            section="professional_summary",
                            current_text=current_summary,
                            suggested_text=enhanced_summary,
                            improvement_reason="Naturally integrating job-relevant keywords improves ATS matching",
                            keywords_added=[keyword]
                        ))

        return suggestions[:2]  # Limit keyword integration suggestions

    async def _suggest_formatting_improvements(
            self,
            resume_content: Dict[str, Any]
    ) -> List[ATSOptimizationSuggestion]:
        """Suggest formatting improvements for better ATS parsing"""

        suggestions = []

        # Check for consistent date formatting
        work_exp = resume_content.get('work_experience', [])
        date_formats = []

        for job in work_exp:
            if job.get('start_date'):
                date_formats.append(job['start_date'])
            if job.get('end_date'):
                date_formats.append(job['end_date'])

        if date_formats:
            # Check if all dates follow YYYY-MM pattern
            inconsistent_dates = [date for date in date_formats if not re.match(r'^\d{4}-\d{2}', date)]

            if inconsistent_dates:
                suggestions.append(ATSOptimizationSuggestion(
                    section="work_experience",
                    current_text=f"Inconsistent date formats: {', '.join(inconsistent_dates[:2])}",
                    suggested_text="Use consistent YYYY-MM format (e.g., 2023-01)",
                    improvement_reason="Consistent date formatting improves ATS parsing accuracy",
                    keywords_added=[]
                ))

            # Check for missing contact information
            personal_info = resume_content.get('personal_info', {})
            missing_contact = []

            required_fields = ['first_name', 'last_name', 'email', 'phone']
            for field in required_fields:
                if not personal_info.get(field):
                    missing_contact.append(field.replace('_', ' ').title())

            if missing_contact:
                suggestions.append(ATSOptimizationSuggestion(
                    section="personal_info",
                    current_text="Incomplete contact information",
                    suggested_text=f"Add missing fields: {', '.join(missing_contact)}",
                    improvement_reason="Complete contact information is essential for ATS systems and recruiters",
                    keywords_added=[]
                ))

        return suggestions

    def _calculate_suggestion_impact(self, suggestion: ATSOptimizationSuggestion) -> int:
        """Calculate the potential impact of a suggestion (higher = more important)"""
        impact_scores = {
            "professional_summary": 85,
            "work_experience": 75,
            "skills": 70,
            "personal_info": 90,
            "education": 60
        }

        base_score = impact_scores.get(suggestion.section, 50)

        # Bonus for keyword additions
        keyword_bonus = len(suggestion.keywords_added) * 5

        # Bonus for critical fixes (missing contact info, etc.)
        if "missing" in suggestion.improvement_reason.lower():
            base_score += 20

        return base_score + keyword_bonus

    def _extract_resume_text(self, resume_content: Dict[str, Any]) -> str:
        """Extract all text from resume for analysis"""
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

        # Skills
        skills = resume_content.get('skills', {})
        for skill_category in skills.values():
            if isinstance(skill_category, list):
                text_parts.extend(skill_category)

        return ' '.join(filter(None, text_parts))

    async def get_ats_benchmarks(
            self,
            industry: Optional[str] = None,
            role_level: Optional[str] = None
    ) -> List[ATSBenchmark]:
        """Get ATS benchmarks for industries and role levels"""

        # This would typically come from database, but providing static data for now
        benchmarks = [
            ATSBenchmark(
                industry="Technology",
                role_level="Entry",
                average_ats_score=72,
                top_keywords=["programming", "software development", "agile", "git", "testing"],
                recommended_sections=["Technical Skills", "Projects", "Education", "Certifications"],
                optimal_length_words={"min": 400, "max": 700}
            ),
            ATSBenchmark(
                industry="Technology",
                role_level="Senior",
                average_ats_score=78,
                top_keywords=["leadership", "architecture", "mentoring", "strategy", "scalability"],
                recommended_sections=["Leadership Experience", "Technical Skills", "Key Achievements"],
                optimal_length_words={"min": 600, "max": 900}
            ),
            ATSBenchmark(
                industry="Healthcare",
                role_level="Entry",
                average_ats_score=68,
                top_keywords=["patient care", "clinical", "medical terminology", "healthcare"],
                recommended_sections=["Clinical Experience", "Certifications", "Education"],
                optimal_length_words={"min": 400, "max": 650}
            ),
            ATSBenchmark(
                industry="Finance",
                role_level="Mid",
                average_ats_score=75,
                top_keywords=["financial analysis", "excel", "risk management", "compliance"],
                recommended_sections=["Financial Experience", "Certifications", "Quantifiable Results"],
                optimal_length_words={"min": 500, "max": 750}
            )
        ]

        # Filter based on parameters
        if industry:
            benchmarks = [b for b in benchmarks if b.industry.lower() == industry.lower()]

        if role_level:
            benchmarks = [b for b in benchmarks if b.role_level.lower() == role_level.lower()]

        return benchmarks