from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List, Dict, Any

from app.services.template_service import TemplateService
from app.schemas.response import SuccessResponse
from app.core.dependencies import get_current_user_optional

router = APIRouter()


@router.get("/")
async def get_templates(
        include_premium: bool = Query(True, description="Include premium templates"),
        category: Optional[str] = Query(None, description="Filter by category"),
        current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get all available resume templates"""
    try:
        service = TemplateService()

        if category:
            # Search by category
            templates = [
                template for template in service.get_all_templates(include_premium)
                if template["category"] == category
            ]
        else:
            templates = service.get_all_templates(include_premium)

        return SuccessResponse(data={
            "templates": templates,
            "total": len(templates)
        })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve templates"
        )


@router.get("/categories")
async def get_template_categories():
    """Get all template categories"""
    try:
        service = TemplateService()
        categories = service.get_template_categories()

        return SuccessResponse(data={
            "categories": categories,
            "total": len(categories)
        })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template categories"
        )


@router.get("/search")
async def search_templates(
        q: str = Query(..., min_length=1, description="Search query"),
        category: Optional[str] = Query(None, description="Filter by category"),
):
    """Search templates by name, description, or features"""
    try:
        service = TemplateService()
        templates = service.search_templates(query=q, category=category)

        return SuccessResponse(data={
            "templates": templates,
            "total": len(templates),
            "query": q
        })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search templates"
        )


@router.get("/recommended")
async def get_recommended_templates(
        current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get recommended templates based on user profile"""
    try:
        service = TemplateService()

        # Extract user profile info if available
        user_profile = None
        if current_user:
            user_profile = {
                "industry": current_user.get("industry"),
                "job_role": current_user.get("job_role")
            }

        templates = service.get_recommended_templates(user_profile)

        return SuccessResponse(data={
            "templates": templates,
            "total": len(templates)
        })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recommended templates"
        )


@router.get("/{template_id}")
async def get_template(template_id: str):
    """Get specific template by ID"""
    try:
        service = TemplateService()
        template = service.get_template(template_id)

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' not found"
            )

        # Remove internal styling details from public response
        public_template = {
            "id": template["id"],
            "name": template["name"],
            "description": template["description"],
            "category": template["category"],
            "features": template["features"],
            "preview_url": template["preview_url"],
            "is_premium": template.get("is_premium", False),
            "sections": template.get("sections", [])
        }

        return SuccessResponse(data=public_template)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template"
        )


@router.get("/{template_id}/sections")
async def get_template_sections(template_id: str):
    """Get sections configuration for a template"""
    try:
        service = TemplateService()
        sections = service.get_template_sections(template_id)

        if sections is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' not found"
            )

        return SuccessResponse(data={
            "template_id": template_id,
            "sections": sections,
            "total": len(sections)
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template sections"
        )


@router.get("/{template_id}/default-content")
async def get_template_default_content(template_id: str):
    """Get default content structure for a template"""
    try:
        service = TemplateService()

        # Validate template exists
        if not service.validate_template_id(template_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' not found"
            )

        default_content = service.get_default_template_content(template_id)

        return SuccessResponse(data={
            "template_id": template_id,
            "default_content": default_content
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve default content"
        )


@router.get("/{template_id}/preview")
async def get_template_preview(template_id: str):
    """Get template preview information"""
    try:
        service = TemplateService()
        template = service.get_template(template_id)

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' not found"
            )

        preview_data = {
            "template_id": template_id,
            "name": template["name"],
            "description": template["description"],
            "preview_url": template["preview_url"],
            "features": template["features"],
            "is_premium": template.get("is_premium", False),
            "styling": {
                "colors": template.get("styling", {}).get("colors", {}),
                "font_family": template.get("styling", {}).get("font_family", ""),
                "font_size": template.get("styling", {}).get("font_size", "")
            }
        }

        return SuccessResponse(data=preview_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template preview"
        )