import re
from typing import List, Dict, Set, Any
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class ATSKeywordMatcher:
    """Utility class for ATS keyword extraction and matching"""

    def __init__(self):
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'through',
            'is', 'was', 'are', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'can', 'must', 'shall', 'this', 'that', 'these', 'those', 'i', 'you',
            'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }

        self.technical_keywords = self._load_technical_keywords()
        self.industry_keywords = self._load_industry_keywords()
        self.skill_priorities = self._load_skill_priorities()
        self.action_verbs = self._load_action_verbs()

    def _load_technical_keywords(self) -> Dict[str, List[str]]:
        """Load comprehensive technical keywords by category"""
        return {
            "programming_languages": [
                "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "php", "go", "rust",
                "swift", "kotlin", "scala", "r", "matlab", "sql", "html", "css", "dart", "perl"
            ],
            "frameworks": [
                "react", "angular", "vue", "django", "flask", "spring", "express", "nodejs", "laravel",
                "rails", "asp.net", "bootstrap", "jquery", "ember", "backbone", "next.js", "nuxt.js"
            ],
            "databases": [
                "mysql", "postgresql", "mongodb", "redis", "cassandra", "elasticsearch", "dynamodb",
                "oracle", "sqlite", "mariadb", "couchdb", "neo4j", "influxdb", "snowflake"
            ],
            "cloud_platforms": [
                "aws", "azure", "gcp", "google cloud", "amazon web services", "microsoft azure",
                "digitalocean", "heroku", "vercel", "netlify", "cloudflare", "oracle cloud"
            ],
            "devops_tools": [
                "docker", "kubernetes", "jenkins", "gitlab", "github", "terraform", "ansible",
                "chef", "puppet", "vagrant", "circleci", "travis ci", "bamboo", "octopus deploy"
            ],
            "data_science": [
                "machine learning", "artificial intelligence", "deep learning", "neural networks",
                "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras", "spark",
                "hadoop", "tableau", "power bi", "excel", "statistics", "data analysis"
            ],
            "security": [
                "cybersecurity", "information security", "penetration testing", "vulnerability assessment",
                "encryption", "firewall", "antivirus", "malware", "phishing", "ssl", "tls", "oauth"
            ],
            "mobile": [
                "ios", "android", "react native", "flutter", "xamarin", "cordova", "phonegap",
                "swift", "objective-c", "java", "kotlin", "mobile development"
            ],
            "testing": [
                "unit testing", "integration testing", "automated testing", "selenium", "cypress",
                "jest", "mocha", "pytest", "junit", "testng", "cucumber", "postman"
            ]
        }

    def _load_industry_keywords(self) -> Dict[str, List[str]]:
        """Load industry-specific keywords"""
        return {
            "technology": [
                "software development", "agile", "scrum", "devops", "microservices", "api", "rest",
                "graphql", "cloud computing", "serverless", "containerization", "ci/cd", "git",
                "version control", "code review", "technical documentation", "system architecture",
                "scalability", "performance optimization", "debugging", "troubleshooting"
            ],
            "healthcare": [
                "patient care", "clinical experience", "medical records", "hipaa", "ehr", "emr",
                "healthcare", "nursing", "pharmacy", "radiology", "laboratory", "diagnosis",
                "treatment", "medication", "surgery", "rehabilitation", "telemedicine",
                "medical devices", "clinical trials", "healthcare administration"
            ],
            "finance": [
                "financial analysis", "investment", "portfolio management", "risk management",
                "compliance", "audit", "accounting", "budgeting", "forecasting", "valuation",
                "derivatives", "securities", "banking", "insurance", "fintech", "blockchain",
                "cryptocurrency", "trading", "wealth management", "financial modeling"
            ],
            "marketing": [
                "digital marketing", "seo", "sem", "social media", "content marketing", "email marketing",
                "ppc", "analytics", "conversion optimization", "brand management", "campaign management",
                "market research", "customer acquisition", "lead generation", "crm", "marketing automation"
            ],
            "sales": [
                "sales development", "lead generation", "prospecting", "closing", "negotiation",
                "relationship building", "crm", "pipeline management", "quota attainment",
                "customer retention", "upselling", "cross-selling", "territory management",
                "account management", "sales forecasting", "sales training"
            ],
            "education": [
                "curriculum development", "lesson planning", "classroom management", "student assessment",
                "educational technology", "learning management systems", "pedagogy", "instructional design",
                "differentiated instruction", "special education", "esl", "standardized testing",
                "parent communication", "professional development"
            ],
            "manufacturing": [
                "lean manufacturing", "six sigma", "quality control", "supply chain", "inventory management",
                "production planning", "process improvement", "safety protocols", "equipment maintenance",
                "iso standards", "continuous improvement", "waste reduction", "efficiency optimization"
            ],
            "consulting": [
                "client management", "project management", "stakeholder engagement", "business analysis",
                "process improvement", "change management", "strategic planning", "problem solving",
                "presentation skills", "client relations", "proposal writing", "requirement gathering"
            ]
        }

    def _load_skill_priorities(self) -> Dict[str, Dict[str, List[str]]]:
        """Load skill priorities by industry"""
        return {
            "technology": {
                "critical": ["programming", "software development", "problem solving", "debugging"],
                "important": ["version control", "testing", "agile", "collaboration"],
                "nice_to_have": ["devops", "cloud", "machine learning", "mobile development"]
            },
            "healthcare": {
                "critical": ["patient care", "clinical skills", "medical knowledge", "communication"],
                "important": ["teamwork", "attention to detail", "empathy", "time management"],
                "nice_to_have": ["technology skills", "research", "leadership", "teaching"]
            },
            "finance": {
                "critical": ["financial analysis", "excel", "analytical thinking", "attention to detail"],
                "important": ["communication", "teamwork", "time management", "presentation skills"],
                "nice_to_have": ["programming", "data visualization", "project management", "leadership"]
            }
        }

    def _load_action_verbs(self) -> Set[str]:
        """Load powerful action verbs for resume optimization"""
        return {
            "achieved", "administered", "analyzed", "applied", "approved", "arranged", "assembled",
            "assisted", "built", "calculated", "collaborated", "collected", "communicated", "completed",
            "composed", "conceived", "conducted", "constructed", "consulted", "contributed", "controlled",
            "coordinated", "created", "decreased", "delivered", "demonstrated", "designed", "developed",
            "devised", "directed", "discovered", "drafted", "earned", "edited", "eliminated", "enabled",
            "encouraged", "established", "evaluated", "examined", "executed", "expanded", "expedited",
            "facilitated", "founded", "generated", "guided", "headed", "identified", "implemented",
            "improved", "increased", "initiated", "innovated", "inspected", "installed", "instituted",
            "integrated", "introduced", "invented", "investigated", "launched", "led", "maintained",
            "managed", "maximized", "mentored", "minimized", "monitored", "negotiated", "operated",
            "optimized", "organized", "originated", "participated", "performed", "planned", "prepared",
            "presented", "processed", "produced", "programmed", "proposed", "provided", "published",
            "recommended", "reduced", "researched", "resolved", "restored", "restructured", "revised",
            "saved", "scheduled", "selected", "simplified", "solved", "streamlined", "strengthened",
            "structured", "supervised", "supported", "surpassed", "systematized", "trained", "transformed",
            "upgraded", "utilized", "validated", "volunteered"
        }

    def extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text"""
        if not text:
            return []

        # Clean and normalize text
        text = re.sub(r'[^\w\s-]', ' ', text.lower())
        text = re.sub(r'\s+', ' ', text.strip())

        # Extract phrases and single words
        keywords = set()

        # Extract multi-word technical terms
        for category, terms in self.technical_keywords.items():
            for term in terms:
                if term in text:
                    keywords.add(term)

        # Extract single meaningful words
        words = text.split()
        for word in words:
            if (len(word) > 2 and
                    word not in self.stop_words and
                    not word.isdigit() and
                    re.match(r'^[a-zA-Z-]+$', word)):
                keywords.add(word)

        # Extract bigrams and trigrams for compound terms
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i + 1]}"
            if self._is_relevant_phrase(bigram):
                keywords.add(bigram)

        for i in range(len(words) - 2):
            trigram = f"{words[i]} {words[i + 1]} {words[i + 2]}"
            if self._is_relevant_phrase(trigram):
                keywords.add(trigram)

        return list(keywords)

    def _is_relevant_phrase(self, phrase: str) -> bool:
        """Check if a phrase is relevant for ATS"""
        # Check against known technical terms
        for category_terms in self.technical_keywords.values():
            if phrase in category_terms:
                return True

        # Check against industry terms
        for industry_terms in self.industry_keywords.values():
            if phrase in industry_terms:
                return True

        # Check if it contains technical patterns
        tech_patterns = [
            r'\b\w+\s+(development|programming|management|analysis|design)\b',
            r'\b(web|mobile|software|data|system)\s+\w+\b',
            r'\b\w+\s+(engineer|developer|analyst|manager|specialist)\b'
        ]

        for pattern in tech_patterns:
            if re.search(pattern, phrase):
                return True

        return False

    def get_industry_keywords(self, industry: str) -> List[str]:
        """Get keywords specific to an industry"""
        if not industry:
            return []

        industry_lower = industry.lower()
        return self.industry_keywords.get(industry_lower, [])

    def get_industry_skills(self, industry: str) -> List[str]:
        """Get skills specific to an industry"""
        if not industry:
            return []

        industry_lower = industry.lower()
        skills = []

        # Get technical skills relevant to industry
        if industry_lower == "technology":
            for category in ["programming_languages", "frameworks", "databases", "cloud_platforms", "devops_tools"]:
                skills.extend(self.technical_keywords.get(category, []))
        elif industry_lower == "healthcare":
            skills.extend(["medical terminology", "patient care", "clinical documentation", "hipaa compliance"])
        elif industry_lower == "finance":
            skills.extend(["financial modeling", "excel", "bloomberg terminal", "risk analysis"])

        # Add industry-specific keywords as skills
        skills.extend(self.get_industry_keywords(industry))

        return list(set(skills))

    def get_skill_priorities(self, industry: str) -> Dict[str, List[str]]:
        """Get skill priorities for an industry"""
        if not industry:
            return {"critical": [], "important": [], "nice_to_have": []}

        industry_lower = industry.lower()
        return self.skill_priorities.get(industry_lower, {"critical": [], "important": [], "nice_to_have": []})

    def extract_skills_from_text(self, text: str) -> List[str]:
        """Extract skills from job description or other text"""
        if not text:
            return []

        skills = set()
        text_lower = text.lower()

        # Extract technical skills
        for category, skill_list in self.technical_keywords.items():
            for skill in skill_list:
                if skill in text_lower:
                    skills.add(skill)

        # Extract soft skills patterns
        soft_skill_patterns = [
            r'\b(communication|leadership|teamwork|problem.solving|analytical|creative|detail.oriented)\b',
            r'\b(time.management|project.management|critical.thinking|adaptability)\b',
            r'\b(collaboration|interpersonal|presentation|negotiation|conflict.resolution)\b'
        ]

        for pattern in soft_skill_patterns:
            matches = re.findall(pattern, text_lower)
            skills.update(matches)

        return list(skills)

    def calculate_keyword_density(self, text: str, keywords: List[str]) -> float:
        """Calculate keyword density in text"""
        if not text or not keywords:
            return 0.0

        text_lower = text.lower()
        total_words = len(text_lower.split())
        keyword_count = 0

        for keyword in keywords:
            keyword_count += text_lower.count(keyword.lower())

        return (keyword_count / total_words) * 100 if total_words > 0 else 0.0

    def suggest_keyword_improvements(self, current_keywords: List[str], target_keywords: List[str]) -> Dict[str, Any]:
        """Suggest keyword improvements"""
        current_set = set(kw.lower() for kw in current_keywords)
        target_set = set(kw.lower() for kw in target_keywords)

        missing_keywords = list(target_set - current_set)
        present_keywords = list(target_set & current_set)

        # Prioritize missing keywords
        high_priority = []
        medium_priority = []
        low_priority = []

        for keyword in missing_keywords:
            # High priority: programming languages, frameworks, core technical skills
            if any(keyword in self.technical_keywords[cat] for cat in
                   ["programming_languages", "frameworks", "databases"]):
                high_priority.append(keyword)
            # Medium priority: tools and methodologies
            elif any(keyword in self.technical_keywords[cat] for cat in ["devops_tools", "testing"]):
                medium_priority.append(keyword)
            else:
                low_priority.append(keyword)

        return {
            "missing_keywords": missing_keywords,
            "present_keywords": present_keywords,
            "high_priority_missing": high_priority,
            "medium_priority_missing": medium_priority,
            "low_priority_missing": low_priority,
            "match_percentage": (len(present_keywords) / len(target_keywords) * 100) if target_keywords else 0
        }