from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TemplateService:
    """Service for managing resume templates"""

    def __init__(self):
        self.templates = self._initialize_templates()

    def _initialize_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize available resume templates"""
        return {
            "professional": {
                "id": "professional",
                "name": "Professional",
                "description": "Clean and professional layout suitable for corporate environments",
                "category": "business",
                "features": ["Clean layout", "Professional fonts", "Structured sections"],
                "preview_url": "/static/templates/professional_preview.png",
                "is_premium": False,
                "sections": [
                    {
                        "type": "personal_info",
                        "name": "Personal Information",
                        "required": True,
                        "order": 1
                    },
                    {
                        "type": "professional_summary",
                        "name": "Professional Summary",
                        "required": False,
                        "order": 2
                    },
                    {
                        "type": "work_experience",
                        "name": "Work Experience",
                        "required": True,
                        "order": 3
                    },
                    {
                        "type": "education",
                        "name": "Education",
                        "required": True,
                        "order": 4
                    },
                    {
                        "type": "skills",
                        "name": "Skills",
                        "required": False,
                        "order": 5
                    },
                    {
                        "type": "certifications",
                        "name": "Certifications",
                        "required": False,
                        "order": 6
                    },
                    {
                        "type": "projects",
                        "name": "Projects",
                        "required": False,
                        "order": 7
                    },
                    {
                        "type": "languages",
                        "name": "Languages",
                        "required": False,
                        "order": 8
                    }
                ],
                "styling": {
                    "font_family": "Arial, sans-serif",
                    "font_size": "11pt",
                    "line_spacing": "1.2",
                    "margins": "0.75in",
                    "colors": {
                        "primary": "#2E4057",
                        "secondary": "#666666",
                        "accent": "#2E4057"
                    }
                }
            },
            "modern": {
                "id": "modern",
                "name": "Modern",
                "description": "Contemporary design with clean lines and modern typography",
                "category": "creative",
                "features": ["Modern design", "Color accents", "Visual hierarchy"],
                "preview_url": "/static/templates/modern_preview.png",
                "is_premium": True,
                "sections": [
                    {
                        "type": "personal_info",
                        "name": "Personal Information",
                        "required": True,
                        "order": 1
                    },
                    {
                        "type": "professional_summary",
                        "name": "Professional Summary",
                        "required": False,
                        "order": 2
                    },
                    {
                        "type": "work_experience",
                        "name": "Experience",
                        "required": True,
                        "order": 3
                    },
                    {
                        "type": "skills",
                        "name": "Core Skills",
                        "required": False,
                        "order": 4
                    },
                    {
                        "type": "education",
                        "name": "Education",
                        "required": True,
                        "order": 5
                    },
                    {
                        "type": "projects",
                        "name": "Key Projects",
                        "required": False,
                        "order": 6
                    },
                    {
                        "type": "certifications",
                        "name": "Certifications",
                        "required": False,
                        "order": 7
                    }
                ],
                "styling": {
                    "font_family": "Helvetica, sans-serif",
                    "font_size": "10pt",
                    "line_spacing": "1.3",
                    "margins": "0.5in",
                    "colors": {
                        "primary": "#1a365d",
                        "secondary": "#4a5568",
                        "accent": "#3182ce"
                    }
                }
            },
            "creative": {
                "id": "creative",
                "name": "Creative",
                "description": "Bold design for creative professionals and designers",
                "category": "creative",
                "features": ["Bold typography", "Creative layout", "Visual elements"],
                "preview_url": "/static/templates/creative_preview.png",
                "is_premium": True,
                "sections": [
                    {
                        "type": "personal_info",
                        "name": "Contact",
                        "required": True,
                        "order": 1
                    },
                    {
                        "type": "professional_summary",
                        "name": "About Me",
                        "required": False,
                        "order": 2
                    },
                    {
                        "type": "skills",
                        "name": "Expertise",
                        "required": False,
                        "order": 3
                    },
                    {
                        "type": "work_experience",
                        "name": "Experience",
                        "required": True,
                        "order": 4
                    },
                    {
                        "type": "projects",
                        "name": "Portfolio",
                        "required": False,
                        "order": 5
                    },
                    {
                        "type": "education",
                        "name": "Education",
                        "required": True,
                        "order": 6
                    },
                    {
                        "type": "certifications",
                        "name": "Achievements",
                        "required": False,
                        "order": 7
                    }
                ],
                "styling": {
                    "font_family": "Georgia, serif",
                    "font_size": "11pt",
                    "line_spacing": "1.4",
                    "margins": "0.6in",
                    "colors": {
                        "primary": "#2d3748",
                        "secondary": "#718096",
                        "accent": "#e53e3e"
                    }
                }
            }
        }

    def get_all_templates(self, include_premium: bool = True) -> List[Dict[str, Any]]:
        """Get all available templates"""
        try:
            templates = []
            for template_id, template_data in self.templates.items():
                if not include_premium and template_data.get('is_premium', False):
                    continue

                # Return template without internal styling details
                template_info = {
                    "id": template_data["id"],
                    "name": template_data["name"],
                    "description": template_data["description"],
                    "category": template_data["category"],
                    "features": template_data["features"],
                    "preview_url": template_data["preview_url"],
                    "is_premium": template_data.get("is_premium", False)
                }
                templates.append(template_info)

            logger.info(f"Retrieved {len(templates)} templates")
            return templates

        except Exception as e:
            logger.error(f"Error getting templates: {e}")
            raise

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get specific template by ID"""
        try:
            template = self.templates.get(template_id)
            if not template:
                logger.warning(f"Template not found: {template_id}")
                return None

            logger.info(f"Retrieved template: {template_id}")
            return template.copy()

        except Exception as e:
            logger.error(f"Error getting template {template_id}: {e}")
            raise

    def get_template_sections(self, template_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get sections configuration for a template"""
        try:
            template = self.get_template(template_id)
            if not template:
                return None

            return template.get("sections", [])

        except Exception as e:
            logger.error(f"Error getting template sections for {template_id}: {e}")
            raise

    def validate_template_id(self, template_id: str) -> bool:
        """Validate if template ID exists"""
        return template_id in self.templates

    def get_template_categories(self) -> List[Dict[str, Any]]:
        """Get all template categories"""
        try:
            categories = {}

            for template_data in self.templates.values():
                category = template_data["category"]
                if category not in categories:
                    categories[category] = {
                        "name": category.title(),
                        "count": 0,
                        "templates": []
                    }

                categories[category]["count"] += 1
                categories[category]["templates"].append({
                    "id": template_data["id"],
                    "name": template_data["name"],
                    "is_premium": template_data.get("is_premium", False)
                })

            return list(categories.values())

        except Exception as e:
            logger.error(f"Error getting template categories: {e}")
            raise

    def get_default_template_content(self, template_id: str) -> Dict[str, Any]:
        """Get default content structure for a template"""
        try:
            template = self.get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")

            # Generate default content based on template sections
            default_content = {
                "personal_info": {
                    "first_name": "",
                    "last_name": "",
                    "email": "",
                    "phone": "",
                    "address": "",
                    "linkedin_url": "",
                    "portfolio_url": "",
                    "github_url": ""
                },
                "professional_summary": "",
                "work_experience": [],
                "education": [],
                "skills": {
                    "technical": [],
                    "soft": [],
                    "languages": [],
                    "tools": []
                },
                "certifications": [],
                "projects": [],
                "languages": [],
                "additional_sections": {}
            }

            return default_content

        except Exception as e:
            logger.error(f"Error getting default content for template {template_id}: {e}")
            raise

    def get_template_styling(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get styling configuration for a template"""
        try:
            template = self.get_template(template_id)
            if not template:
                return None

            return template.get("styling", {})

        except Exception as e:
            logger.error(f"Error getting template styling for {template_id}: {e}")
            raise

    def search_templates(self, query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search templates by name, description, or features"""
        try:
            results = []
            query_lower = query.lower()

            for template_data in self.templates.values():
                # Check category filter
                if category and template_data["category"] != category:
                    continue

                # Search in name, description, and features
                searchable_text = (
                        template_data["name"].lower() + " " +
                        template_data["description"].lower() + " " +
                        " ".join(template_data["features"]).lower()
                )

                if query_lower in searchable_text:
                    template_info = {
                        "id": template_data["id"],
                        "name": template_data["name"],
                        "description": template_data["description"],
                        "category": template_data["category"],
                        "features": template_data["features"],
                        "preview_url": template_data["preview_url"],
                        "is_premium": template_data.get("is_premium", False)
                    }
                    results.append(template_info)

            logger.info(f"Found {len(results)} templates matching '{query}'")
            return results

        except Exception as e:
            logger.error(f"Error searching templates: {e}")
            raise

    def get_recommended_templates(self, user_profile: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get recommended templates based on user profile"""
        try:
            # Simple recommendation logic
            recommended = []

            if not user_profile:
                # Default recommendations
                recommended = ["professional", "modern"]
            else:
                # Recommend based on industry or job role
                industry = user_profile.get("industry", "").lower()
                job_role = user_profile.get("job_role", "").lower()

                if any(keyword in industry or keyword in job_role for keyword in
                       ["creative", "design", "art", "marketing"]):
                    recommended = ["creative", "modern", "professional"]
                elif any(keyword in industry or keyword in job_role for keyword in
                         ["tech", "software", "engineering", "developer"]):
                    recommended = ["modern", "professional", "creative"]
                else:
                    recommended = ["professional", "modern", "creative"]

            # Get template details
            result = []
            for template_id in recommended[:3]:  # Limit to top 3
                template = self.get_template(template_id)
                if template:
                    template_info = {
                        "id": template["id"],
                        "name": template["name"],
                        "description": template["description"],
                        "category": template["category"],
                        "features": template["features"],
                        "preview_url": template["preview_url"],
                        "is_premium": template.get("is_premium", False)
                    }
                    result.append(template_info)

            return result

        except Exception as e:
            logger.error(f"Error getting recommended templates: {e}")
            raise