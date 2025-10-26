"""
Template CRUD endpoints for SEPE Templates Comparator API.

This module handles Read, Update, and Delete operations for PDF templates.
For template ingestion (create with analysis), use the /ingest endpoint.
For temporary PDF analysis without persistence, use the /analyze endpoint.
"""

import os
import time
import re
from typing import Any, Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Query
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_
from pathlib import Path

from app.core.auth import get_current_active_user, get_optional_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.template import (
    PDFTemplate,
    TemplateVersion,
    TemplateField as TemplateFieldModel
)
from app.schemas.template import (
    TemplateResponse,
    TemplateListResponse,
    TemplateUpdate,
    TemplateVersionResponse,
    TemplateVersionListResponse,
    TemplateFieldResponse,
    TemplateFieldListResponse,
    VersionInfo,
)
from app.schemas.pdf_analysis import (
    TemplateField as TemplateFieldSchema,
    AnalysisResponse,
    create_analysis_response,
)
from app.services.pdf_analysis_service import (
    PDFAnalysisService,
    PDFProcessingError,
    InvalidPDFError,
    NoFormFieldsError
)

router = APIRouter()


@router.get(
    "/",
    response_model=TemplateListResponse,
    summary="List Templates",
    description="""
    Retrieve a paginated list of ingested PDF templates with filtering and sorting.
    
    This endpoint provides read-only access to the catalog of templates
    that have been successfully ingested and stored in the system.
    
    **Features:**
    - Pagination with configurable page size
    - Full-text search by template name or version
    - Flexible sorting by any template field
    - Public access (no authentication required)
    
    **Use Cases:**
    - Browse available templates for comparison
    - Search for specific template versions
    - Display template catalog in UI
    """,
    tags=["Templates - CRUD"]
)
def list_templates(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    search: Optional[str] = Query(None, description="Search by name or version"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    List PDF templates with pagination, filtering, and sorting.
    
    Args:
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return (1-100)
        search: Optional search term for filtering by name or version
        sort_by: Field name to sort by (default: created_at)
        sort_order: Sort direction - 'asc' or 'desc' (default: desc)
        current_user: Optional authenticated user (for personalization)
        db: Database session
        
    Returns:
        TemplateListResponse: Paginated list with items, total count, and pagination info
    """
    # Join with current version to get file data
    query = db.query(PDFTemplate).outerjoin(
        TemplateVersion,
        (TemplateVersion.template_id == PDFTemplate.id) &
        (TemplateVersion.is_current == True)
    )
    
    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            PDFTemplate.name.ilike(search_term) |
            PDFTemplate.current_version.ilike(search_term)
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
        # Get current version data
        current_version = template.current_version_record
        
        template_responses.append(TemplateResponse(
            id=template.id,
            name=template.name,
            current_version=template.current_version,
            comment=template.comment,
            uploaded_by=template.uploaded_by,
            created_at=template.created_at,
            updated_at=template.updated_at,
            # From current version
            file_path=current_version.file_path if current_version else None,
            file_size_bytes=current_version.file_size_bytes if current_version else None,
            field_count=current_version.field_count if current_version else None,
            sepe_url=current_version.sepe_url if current_version else None
        ))
    
    return TemplateListResponse(
        items=template_responses,
        total=total,
        limit=limit,
        offset=skip
    )


@router.get(
    "/{template_id}",
    response_model=TemplateResponse,
    summary="Get Template by ID",
    description="Retrieve detailed information about a specific template.",
    tags=["Templates - CRUD"]
)
def get_template(
    template_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get a specific template by ID.
    
    Args:
        template_id: Unique template identifier
        current_user: Optional authenticated user
        db: Database session
        
    Returns:
        TemplateResponse: Complete template data including metadata
        
    Raises:
        HTTPException 404: If template not found
    """
    template = db.query(PDFTemplate).filter(PDFTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    # Get current version data
    current_version = template.current_version_record
    
    return TemplateResponse(
        id=template.id,
        name=template.name,
        current_version=template.current_version,
        comment=template.comment,
        uploaded_by=template.uploaded_by,
        created_at=template.created_at,
        updated_at=template.updated_at,
        # From current version
        file_path=current_version.file_path if current_version else None,
        file_size_bytes=current_version.file_size_bytes if current_version else None,
        field_count=current_version.field_count if current_version else None,
        sepe_url=current_version.sepe_url if current_version else None
    )


@router.put(
    "/{template_id}",
    response_model=TemplateResponse,
    summary="Update Template Metadata",
    description="""
    Update metadata for an existing template.
    
    **Authentication Required:** Only the template owner or superuser can update.
    
    **Updatable Fields:**
    - name
    - version  
    - sepe_url
    
    **Note:** The PDF file itself cannot be updated. To change the PDF,
    ingest a new version using the /ingest endpoint.
    """,
    tags=["Templates - CRUD"]
)
def update_template(
    template_id: int,
    template_data: TemplateUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Update template metadata (name, version, sepe_url).
    
    Args:
        template_id: Unique template identifier
        template_data: Fields to update (only non-null fields are updated)
        current_user: Authenticated user (must be owner or superuser)
        db: Database session
        
    Returns:
        TemplateResponse: Updated template data
        
    Raises:
        HTTPException 404: If template not found
        HTTPException 403: If user lacks permission to update
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
    
    # Update fields (only template-level fields, not version-specific ones)
    update_data = template_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
    
    db.commit()
    db.refresh(template)
    
    # Get current version data for response
    current_version = template.current_version_record
    
    return TemplateResponse(
        id=template.id,
        name=template.name,
        current_version=template.current_version,
        comment=template.comment,
        uploaded_by=template.uploaded_by,
        created_at=template.created_at,
        updated_at=template.updated_at,
        # From current version
        file_path=current_version.file_path if current_version else None,
        file_size_bytes=current_version.file_size_bytes if current_version else None,
        field_count=current_version.field_count if current_version else None,
        sepe_url=current_version.sepe_url if current_version else None
    )


@router.delete(
    "/{template_id}",
    summary="Delete Template",
    description="""
    Permanently delete a template and its associated PDF file.
    
    **Authentication Required:** Only the template owner or superuser can delete.
    
    **Warning:** This action is irreversible. The template record, all versions,
    fields, and the PDF file will be permanently removed.
    
    **Cascade Deletion:** Related records (versions, fields, comparisons) are
    automatically deleted via database constraints.
    """,
    tags=["Templates - CRUD"]
)
def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Permanently delete a template and its PDF file.
    
    Args:
        template_id: Unique template identifier
        current_user: Authenticated user (must be owner or superuser)
        db: Database session
        
    Returns:
        dict: Success confirmation message
        
    Raises:
        HTTPException 404: If template not found
        HTTPException 403: If user lacks permission to delete
        HTTPException 500: If deletion fails
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
        # Delete all version files from filesystem
        for version in template.versions:
            if version.file_path and os.path.exists(version.file_path):
                os.remove(version.file_path)
        
        # Delete database record (cascade will delete versions and fields)
        db.delete(template)
        db.commit()
        
        return {"message": "Template deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete template: {str(e)}"
        )


@router.get(
    "/{template_id}/download",
    summary="Download Template PDF",
    description="""
    Download the PDF file of a template's current version.
    
    **Authentication Required:** JWT Bearer token
    
    **Response:** Binary PDF file with appropriate headers for download
    
    **Filename Format:** `{template_name}_v{version}.pdf`
    
    Special characters in filenames are sanitized for compatibility.
    """,
    tags=["Templates - CRUD"],
    response_class=FileResponse
)
def download_template(
    template_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> FileResponse:
    """
    Download template PDF file.
    
    Args:
        template_id: Unique template identifier
        current_user: Authenticated user
        db: Database session
        
    Returns:
        FileResponse: PDF file stream with download headers
        
    Raises:
        HTTPException 404: If template or file not found
        HTTPException 401: If not authenticated
    """
    # Get template
    template = db.query(PDFTemplate).filter(PDFTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    # Get current version to access file_path
    current_version = template.current_version_record
    
    if not current_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template has no current version"
        )
    
    # Check if file exists
    if not os.path.exists(current_version.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found on disk"
        )
    
    # Sanitize filename for download
    # Replace spaces with underscores and remove special characters
    safe_name = re.sub(r'[^\w\s-]', '', template.name)
    safe_name = re.sub(r'[\s]+', '_', safe_name)
    safe_version = re.sub(r'[^\w.-]', '', template.current_version)
    filename = f"{safe_name}_v{safe_version}.pdf"
    
    return FileResponse(
        path=current_version.file_path,
        media_type="application/pdf",
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get(
    "/{template_id}/versions",
    response_model=TemplateVersionListResponse,
    summary="Get Template Versions",
    description="""
    Retrieve all versions of a specific template with pagination and sorting.
    
    Returns version history with full PDF metadata including title, author,
    subject, page count, and document dates.
    
    **Features:**
    - Pagination support
    - Sorting by created_at, version_number, or page_count
    - Ascending or descending order
    - Current version highlighted
    """,
    tags=["Templates - CRUD"]
)
def get_template_versions(
    template_id: int,
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    sort_by: str = Query("created_at", description="Sort field: created_at, version_number, page_count"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get all versions of a template with pagination and sorting.
    
    Args:
        template_id: Unique template identifier
        limit: Maximum number of results (1-100)
        offset: Number of results to skip
        sort_by: Field to sort by
        sort_order: Sort direction (asc/desc)
        current_user: Optional authenticated user
        db: Database session
        
    Returns:
        TemplateVersionListResponse: Paginated list of versions with metadata
        
    Raises:
        HTTPException 404: If template not found
        HTTPException 422: If invalid sort parameters
    """
    # Check if template exists
    template = db.query(PDFTemplate).filter(PDFTemplate.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    # Build query
    query = db.query(TemplateVersion).filter(
        TemplateVersion.template_id == template_id
    )
    
    # Apply sorting
    valid_sort_fields = ["created_at", "version_number", "page_count"]
    if sort_by not in valid_sort_fields:
        sort_by = "created_at"
    
    sort_column = getattr(TemplateVersion, sort_by)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    versions = query.offset(offset).limit(limit).all()
    
    return TemplateVersionListResponse(
        items=[
            TemplateVersionResponse(
                id=version.id,
                template_id=version.template_id,
                version_number=version.version_number,
                change_summary=version.change_summary,
                is_current=version.is_current,
                created_at=version.created_at,
                # File information (version-specific)
                file_path=version.file_path,
                file_size_bytes=version.file_size_bytes,
                field_count=version.field_count,
                sepe_url=version.sepe_url,
                # PDF metadata
                title=version.title,
                author=version.author,
                subject=version.subject,
                creation_date=version.creation_date,
                modification_date=version.modification_date,
                page_count=version.page_count
            )
            for version in versions
        ],
        total=total,
        limit=limit,
        offset=offset
    )


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    summary="Analyze PDF Template Fields (Temporary)",
    description="""
    Analyze an uploaded PDF template and extract its AcroForm field structure.
    
    **Important:** This endpoint performs temporary analysis without persisting data.
    - For permanent storage with analysis, use the `/ingest` endpoint instead.
    - This endpoint is ideal for preview/validation before ingestion.
    
    This endpoint processes PDF files containing form fields (such as SEPE templates) 
    and returns a structured analysis of all form fields found in the document.
    
    **Features:**
    - Extracts all AcroForm fields with their unique identifiers
    - Determines field types (text, radiobutton, checkbox, listbox)
    - Finds meaningful Spanish descriptive text near each field
    - Preserves document field ordering (top-to-bottom, left-to-right)
    - Handles encrypted PDFs and various PDF formats
    - Returns processing metadata including timing information
    
    **Supported Field Types:**
    - `text`: Text input fields
    - `radiobutton`: Radio button selections
    - `checkbox`: Checkbox inputs  
    - `listbox`: Dropdown/selection lists
    
    **File Requirements:**
    - Format: PDF files only (.pdf extension)
    - Size: Maximum 10MB
    - Content: Must contain AcroForm fields
    - Encoding: Supports encrypted PDFs
    
    **Response Format:**
    The response includes:
    - `status`: Success/error indicator
    - `data`: Array of field objects with ID, type, nearby text, and options
    - `metadata`: Processing information (field count, timing, page count)
    
    **Example Response:**
    ```json
    {
      "status": "success",
      "data": [
        {
          "field_id": "A0101",
          "type": "text", 
          "near_text": "hasta un máximo de",
          "value_options": null
        }
      ],
      "metadata": {
        "total_fields": 12,
        "processing_time_ms": 850,
        "document_pages": 1
      }
    }
    ```
    """,
    response_description="Structured analysis of PDF form fields with metadata",
    responses={
        200: {
            "description": "PDF analysis completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": [
                            {
                                "field_id": "A0101",
                                "type": "text",
                                "near_text": "hasta un máximo de",
                                "value_options": None
                            },
                            {
                                "field_id": "A0102", 
                                "type": "text",
                                "near_text": "que suponen",
                                "value_options": None
                            }
                        ],
                        "metadata": {
                            "total_fields": 12,
                            "processing_time_ms": 850,
                            "document_pages": 1
                        }
                    }
                }
            }
        },
        400: {
            "description": "Invalid file format or empty file",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "File must be a PDF (.pdf extension required)"
                    }
                }
            }
        },
        413: {
            "description": "File too large",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "File size exceeds 10MB limit"
                    }
                }
            }
        },
        422: {
            "description": "Missing or invalid file parameter",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "file"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        },
        500: {
            "description": "PDF processing error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "PDF processing failed: Unable to extract form fields"
                    }
                }
            }
        }
    },
    tags=["PDF Analysis"],
    operation_id="analyze_pdf_template"
)
async def analyze_pdf_template(
    file: UploadFile = File(..., description="PDF file to analyze")
) -> Any:
    """
    Analyze uploaded PDF template and extract AcroForm field structure.
    
    This endpoint accepts a PDF file upload and returns a structured analysis
    of all form fields found in the document, including field IDs, types,
    nearby text, and available options for selection fields.
    
    Args:
        file: PDF file to analyze (max 10MB)
        
    Returns:
        AnalysisResponse: Structured analysis results with field data and metadata
        
    Raises:
        HTTPException: Various HTTP errors for validation and processing failures
    """
    # Start timing for processing metadata
    start_time = time.time()
    
    try:
        # Validate file is provided
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No file provided in the request"
            )
        
        # Validate file extension
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed. Please upload a valid PDF document."
            )
        
        # Read file content for size validation
        file_content = await file.read()
        file_size = len(file_content)
        
        # Validate file size (10MB limit as specified)
        max_size_bytes = 10 * 1024 * 1024  # 10MB
        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size limit of 10MB. File size: {file_size / (1024*1024):.1f}MB"
            )
        
        # Validate file is not empty
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty. Please provide a valid PDF document."
            )
        
        # Create temporary file for processing
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = Path(temp_file.name)
        
        try:
            # Initialize PDF analysis service
            pdf_service = PDFAnalysisService()
            
            # Analyze the PDF
            analysis_results = pdf_service.analyze_pdf(temp_file_path)
            
            # Get the actual number of pages from the PDF
            document_pages = pdf_service.get_page_count(temp_file_path)
            
            # Convert service results to Pydantic models
            template_fields = []
            for field_data in analysis_results:
                template_field = TemplateFieldSchema(
                    field_id=field_data.field_id,
                    type=field_data.type,
                    near_text=field_data.near_text,
                    value_options=field_data.value_options
                )
                template_fields.append(template_field)
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Create response using utility function
            response = create_analysis_response(
                fields=template_fields,
                processing_time_ms=processing_time_ms,
                document_pages=document_pages
            )
            
            return response
            
        finally:
            # Clean up temporary file
            if temp_file_path.exists():
                temp_file_path.unlink()
    
    except HTTPException:
        # Re-raise HTTPExceptions to let FastAPI handle them properly
        raise
    
    except InvalidPDFError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or corrupted PDF file: {str(e)}"
        )
    
    except NoFormFieldsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No AcroForm fields found in the PDF document: {str(e)}"
        )
    
    except PDFProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process PDF: {str(e)}"
        )
    
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Temporary file processing error. Please try again."
        )
    
    except Exception as e:
        # Log the unexpected error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error in PDF analysis endpoint: {str(e)}", exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the PDF. Please try again."
        )


@router.get(
    "/{template_id}/fields/current",
    response_model=TemplateFieldListResponse,
    summary="Get Current Version Fields",
    description="""
    Retrieve all AcroForm fields from the current version of a template.
    
    **Features:**
    - Pagination support (default 20 items per page)
    - Search by field_id or near_text (case-insensitive)
    - Filter by page_number
    - Fields ordered by page_number, then field_page_order
    - Includes version metadata in response
    
    **Use Cases:**
    - Display template structure in UI
    - Field mapping and comparison
    - Form generation and validation
    """,
    tags=["Templates - Fields"]
)
def get_current_version_fields(
    template_id: int,
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    page_number: Optional[int] = Query(None, ge=1, description="Filter by page number"),
    search: Optional[str] = Query(None, description="Search in field_id or near_text"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get all fields from the current version of a template.
    
    Args:
        template_id: Unique template identifier
        limit: Maximum number of results (1-100)
        offset: Number of results to skip
        page_number: Optional page filter
        search: Optional search term
        current_user: Optional authenticated user
        db: Database session
        
    Returns:
        TemplateFieldListResponse: Paginated list of fields with version info
        
    Raises:
        HTTPException 404: If template or current version not found
    """
    # Check if template exists
    template = db.query(PDFTemplate).filter(PDFTemplate.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    # Find current version
    current_version = db.query(TemplateVersion).filter(
        TemplateVersion.template_id == template_id,
        TemplateVersion.is_current == True
    ).first()
    
    if not current_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No current version found for this template"
        )
    
    # Build query for fields
    query = db.query(TemplateFieldModel).filter(
        TemplateFieldModel.version_id == current_version.id
    )
    
    # Apply page filter if provided
    if page_number is not None:
        query = query.filter(TemplateFieldModel.page_number == page_number)
    
    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                TemplateFieldModel.field_id.ilike(search_term),
                TemplateFieldModel.near_text.ilike(search_term)
            )
        )
    
    # Order by page and field order
    query = query.order_by(
        asc(TemplateFieldModel.page_number),
        asc(TemplateFieldModel.field_page_order)
    )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    fields = query.offset(offset).limit(limit).all()
    
    # Build version info
    version_info = VersionInfo(
        version_id=current_version.id,
        version_number=current_version.version_number,
        field_count=total
    )
    
    return TemplateFieldListResponse(
        items=[
            TemplateFieldResponse(
                id=field.id,
                version_id=field.version_id,
                field_id=field.field_id,
                field_type=field.field_type,
                raw_type=field.raw_type,
                page_number=field.page_number,
                field_page_order=field.field_page_order,
                near_text=field.near_text,
                value_options=field.value_options,
                position_data=field.position_data,
                created_at=field.created_at
            )
            for field in fields
        ],
        total=total,
        limit=limit,
        offset=offset,
        version_info=version_info
    )


@router.get(
    "/{template_id}/versions/{version_id}/fields",
    response_model=TemplateFieldListResponse,
    summary="Get Specific Version Fields",
    description="""
    Retrieve all AcroForm fields from a specific version of a template.
    
    **Features:**
    - Same features as current version endpoint
    - Useful for historical analysis and version comparison
    - Validates that version belongs to template
    
    **Use Cases:**
    - Compare field changes between versions
    - Historical analysis of template evolution
    - Audit trail and documentation
    """,
    tags=["Templates - Fields"]
)
def get_version_fields(
    template_id: int,
    version_id: int,
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    page_number: Optional[int] = Query(None, ge=1, description="Filter by page number"),
    search: Optional[str] = Query(None, description="Search in field_id or near_text"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get all fields from a specific version of a template.
    
    Args:
        template_id: Unique template identifier
        version_id: Unique version identifier
        limit: Maximum number of results (1-100)
        offset: Number of results to skip
        page_number: Optional page filter
        search: Optional search term
        current_user: Optional authenticated user
        db: Database session
        
    Returns:
        TemplateFieldListResponse: Paginated list of fields with version info
        
    Raises:
        HTTPException 404: If template or version not found
        HTTPException 400: If version doesn't belong to template
    """
    # Check if template exists
    template = db.query(PDFTemplate).filter(PDFTemplate.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    # Find specific version
    version = db.query(TemplateVersion).filter(
        TemplateVersion.id == version_id
    ).first()
    
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )
    
    # Verify version belongs to template
    if version.template_id != template_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Version {version_id} does not belong to template {template_id}"
        )
    
    # Build query for fields
    query = db.query(TemplateFieldModel).filter(
        TemplateFieldModel.version_id == version_id
    )
    
    # Apply page filter if provided
    if page_number is not None:
        query = query.filter(TemplateFieldModel.page_number == page_number)
    
    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                TemplateFieldModel.field_id.ilike(search_term),
                TemplateFieldModel.near_text.ilike(search_term)
            )
        )
    
    # Order by page and field order
    query = query.order_by(
        asc(TemplateFieldModel.page_number),
        asc(TemplateFieldModel.field_page_order)
    )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    fields = query.offset(offset).limit(limit).all()
    
    # Build version info
    version_info = VersionInfo(
        version_id=version.id,
        version_number=version.version_number,
        field_count=total
    )
    
    return TemplateFieldListResponse(
        items=[
            TemplateFieldResponse(
                id=field.id,
                version_id=field.version_id,
                field_id=field.field_id,
                field_type=field.field_type,
                raw_type=field.raw_type,
                page_number=field.page_number,
                field_page_order=field.field_page_order,
                near_text=field.near_text,
                value_options=field.value_options,
                position_data=field.position_data,
                created_at=field.created_at
            )
            for field in fields
        ],
        total=total,
        limit=limit,
        offset=offset,
        version_info=version_info
    )
