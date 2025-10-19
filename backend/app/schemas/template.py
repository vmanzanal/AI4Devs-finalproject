"""
Template-related Pydantic schemas.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, HttpUrl


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


# Template Ingestion Schemas

class TemplateIngestRequest(BaseModel):
    """Schema for template ingestion request."""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Template name"
    )
    version: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Version identifier"
    )
    sepe_url: Optional[HttpUrl] = Field(
        None,
        description="SEPE source URL"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name is not empty after stripping."""
        if not v or not v.strip():
            raise ValueError('Template name cannot be empty')
        return v.strip()

    @field_validator('version')
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version is not empty after stripping."""
        if not v or not v.strip():
            raise ValueError('Template version cannot be empty')
        return v.strip()


class TemplateIngestResponse(BaseModel):
    """Schema for template ingestion response."""
    
    id: int
    name: str
    version: str
    file_path: str
    file_size_bytes: int = Field(..., gt=0, description="File size in bytes")
    field_count: int = Field(..., ge=0, description="Number of fields extracted")
    checksum: str = Field(..., description="SHA256 checksum of file")
    message: str = "Template ingested successfully"


class TemplateFieldData(BaseModel):
    """Schema for template field data matching database structure."""
    
    field_id: str = Field(..., max_length=255, description="Field identifier")
    field_type: str = Field(..., max_length=50, description="Field type")
    raw_type: Optional[str] = Field(
        None,
        max_length=50,
        description="Raw PDF field type"
    )
    page_number: int = Field(
        ...,
        ge=1,
        description="Page number (1-indexed)"
    )
    field_page_order: int = Field(
        ...,
        ge=0,
        description="Order within page (0-indexed)"
    )
    near_text: Optional[str] = Field(
        None,
        description="Nearby text label"
    )
    value_options: Optional[List[str]] = Field(
        None,
        description="Available options for selection fields"
    )
    position_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Field position coordinates"
    )
