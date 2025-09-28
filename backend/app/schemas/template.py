"""
Template-related Pydantic schemas.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class TemplateBase(BaseModel):
    """Base template schema."""
    name: str = Field(..., max_length=255)
    version: str = Field(..., max_length=50)
    sepe_url: Optional[str] = Field(None, max_length=1000)


class TemplateCreate(TemplateBase):
    """Schema for template creation."""
    pass


class TemplateUpdate(BaseModel):
    """Schema for template update."""
    name: Optional[str] = Field(None, max_length=255)
    version: Optional[str] = Field(None, max_length=50)
    sepe_url: Optional[str] = Field(None, max_length=1000)


class TemplateResponse(TemplateBase):
    """Schema for template response."""
    id: int
    file_path: str
    file_size_bytes: int
    field_count: int
    uploaded_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """Schema for template list response."""
    items: List[TemplateResponse]
    total: int
    limit: int
    offset: int


class TemplateVersionResponse(BaseModel):
    """Schema for template version response."""
    id: int
    template_id: int
    version_number: str
    change_summary: Optional[str] = None
    is_current: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class TemplateUploadResponse(BaseModel):
    """Schema for template upload response."""
    id: int
    name: str
    version: str
    file_path: str
    file_size_bytes: int
    field_count: int
    message: str = "Template uploaded successfully"
