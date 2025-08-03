from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class SectionCreate(BaseModel):
    """Schema for creating a resume section"""
    section_type: str = Field(..., min_length=1, max_length=50, description="Section type")
    section_title: Optional[str] = Field(None, max_length=255, description="Custom section title")
    content: Dict[str, Any] = Field(..., description="Section content as JSON")
    order_index: Optional[int] = Field(0, ge=0, description="Display order")


class SectionUpdate(BaseModel):
    """Schema for updating a resume section"""
    section_title: Optional[str] = Field(None, max_length=255, description="Custom section title")
    content: Optional[Dict[str, Any]] = Field(None, description="Section content as JSON")
    order_index: Optional[int] = Field(None, ge=0, description="Display order")


class SectionResponse(BaseModel):
    """Schema for section response"""
    id: UUID
    resume_id: UUID
    section_type: str
    section_title: Optional[str]
    content: Dict[str, Any]
    order_index: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SectionTemplateResponse(BaseModel):
    """Schema for section template response"""
    id: UUID
    section_type: str
    display_name: str
    description: Optional[str]
    schema: Dict[str, Any]
    default_content: Dict[str, Any]
    is_required: bool
    is_multiple: bool
    display_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SectionReorder(BaseModel):
    """Schema for reordering sections"""
    section_orders: List[Dict[str, Any]] = Field(
        ...,
        description="List of section IDs and their new order indices"
    )

    class Config:
        schema_extra = {
            "example": {
                "section_orders": [
                    {"section_id": "uuid1", "order_index": 0},
                    {"section_id": "uuid2", "order_index": 1},
                    {"section_id": "uuid3", "order_index": 2}
                ]
            }
        }