"""
Comparison endpoints for SEPE Templates Comparator API.
"""

import logging
from typing import Any, Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    BackgroundTasks
)
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from app.core.auth import (
    get_current_active_user,
    get_optional_current_user
)
from app.core.database import get_db
from app.models.user import User
from app.models.template import PDFTemplate
from app.models.comparison import Comparison, ComparisonField
from app.schemas.comparison import (
    ComparisonRequest,
    ComparisonResult,
)
from app.services.comparison_service import ComparisonService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/analyze",
    response_model=ComparisonResult,
    status_code=status.HTTP_200_OK,
    summary="Analyze Template Version Differences",
    description="""
    Compare two template versions field-by-field.

    This endpoint performs an in-memory comparison using data from the
    database without re-processing PDF files. It identifies added,
    removed, and modified fields, and calculates global metrics.

    **Use Case:**
    When SEPE publishes a new version of a form, administrators need to
    understand what has changed to update documentation, training
    materials, and integration code.

    **Features:**
    - In-memory comparison (fast, no PDF processing)
    - Field-by-field analysis
    - Global metrics (page count, field count, % changed)
    - Position comparison with tolerance (5px)
    - Value options comparison (for select/radio fields)

    **Authentication Required:** Valid JWT token must be provided.

    **Validation:**
    - Both version IDs must exist in the database
    - Version IDs must be different (cannot compare a version with itself)
    - User must be authenticated

    **Response Includes:**
    - Global metrics (page counts, field counts, modification percentage)
    - Detailed field changes with status (ADDED/REMOVED/MODIFIED/UNCHANGED)
    - Field attribute comparisons (position, label text, value options)
    """,
    responses={
        200: {
            "description": "Comparison completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "source_version_id": 1,
                        "target_version_id": 2,
                        "global_metrics": {
                            "source_version_number": "2024-Q1",
                            "target_version_number": "2024-Q2",
                            "source_page_count": 5,
                            "target_page_count": 6,
                            "page_count_changed": True,
                            "source_field_count": 48,
                            "target_field_count": 52,
                            "field_count_changed": True,
                            "fields_added": 4,
                            "fields_removed": 0,
                            "fields_modified": 3,
                            "fields_unchanged": 45,
                            "modification_percentage": 14.58,
                            "source_created_at": "2024-01-15T10:30:00Z",
                            "target_created_at": "2024-04-20T14:25:00Z"
                        },
                        "field_changes": [
                            {
                                "field_id": "NEW_FIELD_01",
                                "status": "ADDED",
                                "field_type": "text",
                                "target_page_number": 6,
                                "near_text_diff": "NOT_APPLICABLE",
                                "target_near_text": "New field label"
                            }
                        ],
                        "analyzed_at": "2025-10-26T15:45:30Z"
                    }
                }
            }
        },
        400: {
            "description": "Validation error (same version IDs)",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Source and target versions must be different"
                    }
                }
            }
        },
        401: {
            "description": "Not authenticated",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        404: {
            "description": "One or both versions not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Version with ID 999 not found"
                    }
                }
            }
        },
        422: {
            "description": "Invalid request parameters",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "source_version_id"],
                                "msg": "ensure this value is greater than 0",
                                "type": "value_error.number.not_gt"
                            }
                        ]
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to analyze comparison"
                    }
                }
            }
        }
    },
    tags=["comparisons"]
)
async def analyze_comparison(
    request: ComparisonRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ComparisonResult:
    """
    Analyze differences between two template versions.

    Args:
        request: Comparison request with source and target version IDs
        current_user: Current authenticated user
        db: Database session

    Returns:
        ComparisonResult: Complete comparison data with metrics and field
            changes

    Raises:
        HTTPException: For various error conditions (404, 400, 500)
    """
    logger.info(
        f"Comparison requested by user {current_user.id}: "
        f"source_version={request.source_version_id}, "
        f"target_version={request.target_version_id}"
    )

    try:
        # Create comparison service
        comparison_service = ComparisonService(db)

        # Perform comparison
        result = comparison_service.compare_versions(
            source_version_id=request.source_version_id,
            target_version_id=request.target_version_id
        )

        logger.info(
            f"Comparison completed: {result.global_metrics.fields_added} "
            f"added, {result.global_metrics.fields_removed} removed, "
            f"{result.global_metrics.fields_modified} modified"
        )

        return result

    except ValueError as e:
        # Handle "not found" or validation errors
        error_msg = str(e)
        if "not found" in error_msg.lower():
            logger.warning(f"Version not found: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        logger.warning(f"Validation error: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    except Exception as e:
        logger.error(
            f"Comparison analysis error: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze comparison"
        )



# NOTE: The rest of this file contained legacy comparison endpoints that used
# different schemas (ComparisonResponse, ComparisonCreate, etc). Those have been
# commented out to avoid conflicts with the new schema definitions used by the
# /analyze endpoint. The new comparison feature uses:
# - ComparisonRequest (for input)
# - ComparisonResult (for output)
# - ComparisonService (for business logic)
#
# The legacy endpoints can be re-enabled by creating separate schema files
# for the persistent comparison feature (e.g., comparison_persist.py schemas).
