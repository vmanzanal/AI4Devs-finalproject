"""
Comparison endpoints for SEPE Templates Comparator API.
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from app.core.auth import get_current_active_user, get_optional_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.template import PDFTemplate
from app.models.comparison import Comparison, ComparisonField
from app.schemas.comparison import (
    ComparisonCreate,
    ComparisonResponse,
    ComparisonListResponse,
    ComparisonUpdate,
    ComparisonFieldResponse,
    ComparisonSummary,
    ComparisonStatus,
)

router = APIRouter()


def process_comparison_task(comparison_id: int, db: Session):
    """
    Background task to process template comparison.
    
    Args:
        comparison_id: ID of comparison to process
        db: Database session
    """
    # This would be implemented with actual PDF comparison logic
    # For now, we'll simulate the process
    comparison = db.query(Comparison).filter(Comparison.id == comparison_id).first()
    if not comparison:
        return
    
    try:
        # Update status to in_progress
        comparison.status = ComparisonStatus.IN_PROGRESS
        db.commit()
        
        # TODO: Implement actual PDF comparison logic here
        # For now, we'll create some mock differences
        mock_differences = [
            ComparisonField(
                comparison_id=comparison.id,
                field_name="field_1",
                field_type="text",
                change_type="modified",
                old_value="Old Value 1",
                new_value="New Value 1",
                position_x=100.0,
                position_y=200.0
            ),
            ComparisonField(
                comparison_id=comparison.id,
                field_name="field_2",
                field_type="text",
                change_type="added",
                new_value="Added Field Value",
                position_x=150.0,
                position_y=250.0
            )
        ]
        
        for diff in mock_differences:
            db.add(diff)
        
        # Update comparison status and count
        comparison.status = ComparisonStatus.COMPLETED
        comparison.differences_count = len(mock_differences)
        from datetime import datetime
        comparison.completed_at = datetime.utcnow()
        
        db.commit()
        
    except Exception as e:
        # Mark as failed
        comparison.status = ComparisonStatus.FAILED
        db.commit()


@router.post("/", response_model=ComparisonResponse, status_code=status.HTTP_201_CREATED)
def create_comparison(
    comparison_data: ComparisonCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Create a new template comparison.
    
    Args:
        comparison_data: Comparison creation data
        background_tasks: FastAPI background tasks
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ComparisonResponse: Created comparison
        
    Raises:
        HTTPException: If templates not found or invalid
    """
    # Validate source template exists
    source_template = db.query(PDFTemplate).filter(
        PDFTemplate.id == comparison_data.source_template_id
    ).first()
    if not source_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source template not found"
        )
    
    # Validate target template exists
    target_template = db.query(PDFTemplate).filter(
        PDFTemplate.id == comparison_data.target_template_id
    ).first()
    if not target_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target template not found"
        )
    
    # Check if comparing the same template
    if comparison_data.source_template_id == comparison_data.target_template_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot compare a template with itself"
        )
    
    # Create comparison record
    db_comparison = Comparison(
        source_template_id=comparison_data.source_template_id,
        target_template_id=comparison_data.target_template_id,
        comparison_type=comparison_data.comparison_type,
        status=ComparisonStatus.PENDING,
        created_by=current_user.id
    )
    
    db.add(db_comparison)
    db.commit()
    db.refresh(db_comparison)
    
    # Start background processing
    background_tasks.add_task(process_comparison_task, db_comparison.id, db)
    
    return ComparisonResponse(
        id=db_comparison.id,
        source_template_id=db_comparison.source_template_id,
        target_template_id=db_comparison.target_template_id,
        comparison_type=db_comparison.comparison_type,
        status=db_comparison.status,
        differences_count=db_comparison.differences_count,
        created_by=db_comparison.created_by,
        created_at=db_comparison.created_at,
        completed_at=db_comparison.completed_at
    )


@router.get("/", response_model=ComparisonListResponse)
def list_comparisons(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    status_filter: Optional[ComparisonStatus] = Query(None, description="Filter by status"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    List comparisons with pagination and filtering.
    
    Args:
        skip: Number of records to skip
        limit: Number of records to return
        status_filter: Optional status filter
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)
        current_user: Optional current user
        db: Database session
        
    Returns:
        ComparisonListResponse: Paginated list of comparisons
    """
    query = db.query(Comparison)
    
    # Apply status filter
    if status_filter:
        query = query.filter(Comparison.status == status_filter)
    
    # Apply sorting
    sort_column = getattr(Comparison, sort_by, Comparison.created_at)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    comparisons = query.offset(skip).limit(limit).all()
    
    # Convert to response format
    comparison_responses = []
    for comparison in comparisons:
        comparison_responses.append(ComparisonResponse(
            id=comparison.id,
            source_template_id=comparison.source_template_id,
            target_template_id=comparison.target_template_id,
            comparison_type=comparison.comparison_type,
            status=comparison.status,
            differences_count=comparison.differences_count,
            created_by=comparison.created_by,
            created_at=comparison.created_at,
            completed_at=comparison.completed_at
        ))
    
    return ComparisonListResponse(
        items=comparison_responses,
        total=total,
        limit=limit,
        offset=skip
    )


@router.get("/{comparison_id}", response_model=ComparisonResponse)
def get_comparison(
    comparison_id: int,
    include_details: bool = Query(False, description="Include field differences"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get a specific comparison by ID.
    
    Args:
        comparison_id: Comparison ID
        include_details: Whether to include field differences
        current_user: Optional current user
        db: Database session
        
    Returns:
        ComparisonResponse: Comparison data
        
    Raises:
        HTTPException: If comparison not found
    """
    comparison = db.query(Comparison).filter(Comparison.id == comparison_id).first()
    
    if not comparison:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comparison not found"
        )
    
    field_differences = None
    if include_details:
        differences = db.query(ComparisonField).filter(
            ComparisonField.comparison_id == comparison_id
        ).all()
        
        field_differences = [
            ComparisonFieldResponse(
                id=diff.id,
                comparison_id=diff.comparison_id,
                field_name=diff.field_name,
                field_type=diff.field_type,
                change_type=diff.change_type,
                old_value=diff.old_value,
                new_value=diff.new_value,
                position_x=diff.position_x,
                position_y=diff.position_y,
                created_at=diff.created_at
            )
            for diff in differences
        ]
    
    return ComparisonResponse(
        id=comparison.id,
        source_template_id=comparison.source_template_id,
        target_template_id=comparison.target_template_id,
        comparison_type=comparison.comparison_type,
        status=comparison.status,
        differences_count=comparison.differences_count,
        created_by=comparison.created_by,
        created_at=comparison.created_at,
        completed_at=comparison.completed_at,
        field_differences=field_differences
    )


@router.delete("/{comparison_id}")
def delete_comparison(
    comparison_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Delete a comparison.
    
    Args:
        comparison_id: Comparison ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If comparison not found or access denied
    """
    comparison = db.query(Comparison).filter(Comparison.id == comparison_id).first()
    
    if not comparison:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comparison not found"
        )
    
    # Check permissions (only creator or superuser can delete)
    if comparison.created_by != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to delete this comparison"
        )
    
    try:
        # Delete database record (cascade will handle comparison_fields)
        db.delete(comparison)
        db.commit()
        
        return {"message": "Comparison deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete comparison: {str(e)}"
        )


@router.get("/{comparison_id}/summary", response_model=ComparisonSummary)
def get_comparison_summary(
    comparison_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get a comparison summary with template names.
    
    Args:
        comparison_id: Comparison ID
        current_user: Optional current user
        db: Database session
        
    Returns:
        ComparisonSummary: Comparison summary
        
    Raises:
        HTTPException: If comparison not found
    """
    # Query with joins to get template names
    result = db.query(
        Comparison,
        PDFTemplate.name.label("source_name"),
        PDFTemplate.name.label("target_name")
    ).join(
        PDFTemplate, 
        Comparison.source_template_id == PDFTemplate.id,
        isouter=True
    ).filter(
        Comparison.id == comparison_id
    ).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comparison not found"
        )
    
    comparison = result[0]
    
    # Get target template name separately
    target_template = db.query(PDFTemplate).filter(
        PDFTemplate.id == comparison.target_template_id
    ).first()
    
    return ComparisonSummary(
        id=comparison.id,
        source_template_name=result.source_name or "Unknown",
        target_template_name=target_template.name if target_template else "Unknown",
        status=comparison.status,
        differences_count=comparison.differences_count,
        created_at=comparison.created_at,
        completed_at=comparison.completed_at
    )
