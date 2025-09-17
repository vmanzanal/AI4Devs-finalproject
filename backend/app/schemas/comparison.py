"""
Comparison-related Pydantic schemas.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class ComparisonStatus(str, Enum):
    """Enum for comparison status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ChangeType(str, Enum):
    """Enum for field change types."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class ComparisonCreate(BaseModel):
    """Schema for comparison creation."""
    source_template_id: int
    target_template_id: int
    comparison_type: str = Field(default="structure", max_length=50)


class ComparisonFieldResponse(BaseModel):
    """Schema for comparison field response."""
    id: int
    comparison_id: int
    field_name: str
    field_type: Optional[str] = None
    change_type: Optional[ChangeType] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ComparisonResponse(BaseModel):
    """Schema for comparison response."""
    id: int
    source_template_id: int
    target_template_id: int
    comparison_type: str
    status: ComparisonStatus
    differences_count: int
    created_by: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    field_differences: Optional[List[ComparisonFieldResponse]] = None
    
    class Config:
        from_attributes = True


class ComparisonListResponse(BaseModel):
    """Schema for comparison list response."""
    items: List[ComparisonResponse]
    total: int
    limit: int
    offset: int


class ComparisonUpdate(BaseModel):
    """Schema for comparison update."""
    status: Optional[ComparisonStatus] = None
    differences_count: Optional[int] = None
    completed_at: Optional[datetime] = None


class ComparisonSummary(BaseModel):
    """Schema for comparison summary."""
    id: int
    source_template_name: str
    target_template_name: str
    status: ComparisonStatus
    differences_count: int
    created_at: datetime
    completed_at: Optional[datetime] = None
