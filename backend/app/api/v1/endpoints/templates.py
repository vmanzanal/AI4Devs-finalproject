"""
Template management endpoints for SEPE Templates Comparator API.
"""

import os
import shutil
from typing import Any, List, Optional
from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException, 
    status, 
    UploadFile, 
    File, 
    Query,
    Form
)
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from app.core.auth import get_current_active_user, get_optional_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.template import PDFTemplate, TemplateVersion
from app.schemas.template import (
    TemplateResponse,
    TemplateListResponse,
    TemplateUploadResponse,
    TemplateUpdate,
    TemplateVersionResponse,
)

router = APIRouter()


@router.post("/upload", response_model=TemplateUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_template(
    name: str = Form(..., max_length=255),
    version: str = Form(..., max_length=50),
    sepe_url: Optional[str] = Form(None, max_length=1000),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Upload a new PDF template.
    
    Args:
        name: Template name
        version: Template version
        sepe_url: Optional SEPE URL
        file: PDF file to upload
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        TemplateUploadResponse: Upload result
        
    Raises:
        HTTPException: If file is invalid or upload fails
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Validate file size
    file_size = 0
    content = await file.read()
    file_size = len(content)
    
    if file_size > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB"
        )
    
    # Create upload directory if it doesn't exist
    upload_dir = settings.UPLOAD_DIRECTORY
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    import uuid
    file_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{file_id}{file_extension}"
    file_path = os.path.join(upload_dir, filename)
    
    try:
        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # TODO: Extract field count from PDF
        # For now, we'll use a placeholder
        field_count = 0
        
        # Create database record
        db_template = PDFTemplate(
            name=name,
            version=version,
            file_path=file_path,
            file_size_bytes=file_size,
            field_count=field_count,
            sepe_url=sepe_url,
            uploaded_by=current_user.id
        )
        
        db.add(db_template)
        db.commit()
        db.refresh(db_template)
        
        return TemplateUploadResponse(
            id=db_template.id,
            name=db_template.name,
            version=db_template.version,
            file_path=db_template.file_path,
            file_size_bytes=db_template.file_size_bytes,
            field_count=db_template.field_count,
            message="Template uploaded successfully"
        )
        
    except Exception as e:
        # Clean up file if database operation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload template: {str(e)}"
        )


@router.get("/", response_model=TemplateListResponse)
def list_templates(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    search: Optional[str] = Query(None, description="Search by name or version"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    List PDF templates with pagination and filtering.
    
    Args:
        skip: Number of records to skip
        limit: Number of records to return
        search: Optional search term
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)
        current_user: Optional current user
        db: Database session
        
    Returns:
        TemplateListResponse: Paginated list of templates
    """
    query = db.query(PDFTemplate)
    
    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            PDFTemplate.name.ilike(search_term) |
            PDFTemplate.version.ilike(search_term)
        )
    
    # Apply sorting
    sort_column = getattr(PDFTemplate, sort_by, PDFTemplate.created_at)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    templates = query.offset(skip).limit(limit).all()
    
    # Convert to response format
    template_responses = []
    for template in templates:
        template_responses.append(TemplateResponse(
            id=template.id,
            name=template.name,
            version=template.version,
            file_path=template.file_path,
            file_size_bytes=template.file_size_bytes,
            field_count=template.field_count,
            sepe_url=template.sepe_url,
            uploaded_by=template.uploaded_by,
            created_at=template.created_at,
            updated_at=template.updated_at
        ))
    
    return TemplateListResponse(
        items=template_responses,
        total=total,
        limit=limit,
        offset=skip
    )


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get a specific template by ID.
    
    Args:
        template_id: Template ID
        current_user: Optional current user
        db: Database session
        
    Returns:
        TemplateResponse: Template data
        
    Raises:
        HTTPException: If template not found
    """
    template = db.query(PDFTemplate).filter(PDFTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    return TemplateResponse(
        id=template.id,
        name=template.name,
        version=template.version,
        file_path=template.file_path,
        file_size_bytes=template.file_size_bytes,
        field_count=template.field_count,
        sepe_url=template.sepe_url,
        uploaded_by=template.uploaded_by,
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: int,
    template_data: TemplateUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Update template metadata.
    
    Args:
        template_id: Template ID
        template_data: Template update data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        TemplateResponse: Updated template data
        
    Raises:
        HTTPException: If template not found or access denied
    """
    template = db.query(PDFTemplate).filter(PDFTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    # Check permissions (only owner or superuser can update)
    if template.uploaded_by != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to update this template"
        )
    
    # Update fields
    update_data = template_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
    
    db.commit()
    db.refresh(template)
    
    return TemplateResponse(
        id=template.id,
        name=template.name,
        version=template.version,
        file_path=template.file_path,
        file_size_bytes=template.file_size_bytes,
        field_count=template.field_count,
        sepe_url=template.sepe_url,
        uploaded_by=template.uploaded_by,
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Delete a template.
    
    Args:
        template_id: Template ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If template not found or access denied
    """
    template = db.query(PDFTemplate).filter(PDFTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    # Check permissions (only owner or superuser can delete)
    if template.uploaded_by != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to delete this template"
        )
    
    try:
        # Delete file from filesystem
        if os.path.exists(template.file_path):
            os.remove(template.file_path)
        
        # Delete database record
        db.delete(template)
        db.commit()
        
        return {"message": "Template deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete template: {str(e)}"
        )


@router.get("/{template_id}/versions", response_model=List[TemplateVersionResponse])
def get_template_versions(
    template_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get all versions of a template.
    
    Args:
        template_id: Template ID
        current_user: Optional current user
        db: Database session
        
    Returns:
        List[TemplateVersionResponse]: List of template versions
        
    Raises:
        HTTPException: If template not found
    """
    # Check if template exists
    template = db.query(PDFTemplate).filter(PDFTemplate.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    # Get versions
    versions = db.query(TemplateVersion).filter(
        TemplateVersion.template_id == template_id
    ).order_by(desc(TemplateVersion.created_at)).all()
    
    return [
        TemplateVersionResponse(
            id=version.id,
            template_id=version.template_id,
            version_number=version.version_number,
            change_summary=version.change_summary,
            is_current=version.is_current,
            created_at=version.created_at
        )
        for version in versions
    ]
