"""
Comparison service for template version analysis.

This module provides the ComparisonService class that performs in-memory
comparison of two template versions, analyzing field-by-field differences.
"""
import logging
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.template import TemplateField, TemplateVersion
from app.schemas.comparison import (
    ComparisonResult,
    DiffStatus,
    FieldChange,
    FieldChangeStatus,
    GlobalMetrics,
)

logger = logging.getLogger(__name__)


class ComparisonService:
    """
    Service for comparing two template versions.

    Performs in-memory comparison using data from the database without
    re-processing PDF files.
    """

    def __init__(self, db: Session):
        """
        Initialize comparison service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def compare_versions(
        self,
        source_version_id: int,
        target_version_id: int
    ) -> ComparisonResult:
        """
        Compare two template versions field-by-field.

        Args:
            source_version_id: ID of the source version to compare from
            target_version_id: ID of the target version to compare to

        Returns:
            ComparisonResult: Complete comparison data with metrics and
                field-by-field changes

        Raises:
            ValueError: If either version is not found
        """
        logger.info(
            f"Starting comparison: source_id={source_version_id}, "
            f"target_id={target_version_id}"
        )

        # Step 1: Fetch versions
        source_version = self._get_version(source_version_id)
        target_version = self._get_version(target_version_id)

        # Step 2: Fetch fields
        source_fields = self._get_version_fields(source_version_id)
        target_fields = self._get_version_fields(target_version_id)

        logger.info(
            f"Comparing {len(source_fields)} source fields with "
            f"{len(target_fields)} target fields"
        )

        # Step 3: Calculate global metrics
        global_metrics = self._calculate_global_metrics(
            source_version, target_version,
            source_fields, target_fields
        )

        # Step 4: Perform field-by-field comparison
        field_changes = self._compare_fields(source_fields, target_fields)

        logger.info(
            f"Comparison complete: {global_metrics.fields_added} added, "
            f"{global_metrics.fields_removed} removed, "
            f"{global_metrics.fields_modified} modified"
        )

        return ComparisonResult(
            source_version_id=source_version_id,
            target_version_id=target_version_id,
            global_metrics=global_metrics,
            field_changes=field_changes
        )

    def _get_version(self, version_id: int) -> TemplateVersion:
        """
        Fetch version from database.

        Args:
            version_id: ID of the version to fetch

        Returns:
            TemplateVersion: The version record

        Raises:
            ValueError: If version not found
        """
        version = self.db.query(TemplateVersion).filter(
            TemplateVersion.id == version_id
        ).first()

        if not version:
            raise ValueError(f"Version with ID {version_id} not found")

        return version

    def _get_version_fields(self, version_id: int) -> List[TemplateField]:
        """
        Fetch all fields for a version.

        Args:
            version_id: ID of the version

        Returns:
            List[TemplateField]: List of fields for the version
        """
        fields = self.db.query(TemplateField).filter(
            TemplateField.version_id == version_id
        ).order_by(
            TemplateField.page_number,
            TemplateField.field_page_order
        ).all()

        return fields

    def _calculate_global_metrics(
        self,
        source_version: TemplateVersion,
        target_version: TemplateVersion,
        source_fields: List[TemplateField],
        target_fields: List[TemplateField]
    ) -> GlobalMetrics:
        """
        Calculate high-level comparison metrics.

        Args:
            source_version: Source version record
            target_version: Target version record
            source_fields: List of source version fields
            target_fields: List of target version fields

        Returns:
            GlobalMetrics: High-level comparison statistics
        """
        # Create field ID sets for quick lookups
        source_field_ids = {f.field_id for f in source_fields}
        target_field_ids = {f.field_id for f in target_fields}

        # Calculate basic counts
        fields_added = len(target_field_ids - source_field_ids)
        fields_removed = len(source_field_ids - target_field_ids)

        # Count modified and unchanged fields
        common_field_ids = source_field_ids & target_field_ids
        fields_modified = 0
        fields_unchanged = 0

        # Build field dictionaries for quick access
        source_fields_dict = {f.field_id: f for f in source_fields}
        target_fields_dict = {f.field_id: f for f in target_fields}

        for field_id in common_field_ids:
            source_field = source_fields_dict[field_id]
            target_field = target_fields_dict[field_id]

            if self._is_field_modified(source_field, target_field):
                fields_modified += 1
            else:
                fields_unchanged += 1

        # Calculate modification percentage
        total_fields = len(source_field_ids | target_field_ids)
        if total_fields > 0:
            modification_percentage = round(
                ((fields_added + fields_removed + fields_modified)
                 / total_fields) * 100,
                2
            )
        else:
            modification_percentage = 0.0

        return GlobalMetrics(
            source_version_number=str(source_version.version_number),
            target_version_number=str(target_version.version_number),
            source_page_count=int(source_version.page_count),
            target_page_count=int(target_version.page_count),
            page_count_changed=bool(
                source_version.page_count != target_version.page_count
            ),
            source_field_count=len(source_fields),
            target_field_count=len(target_fields),
            field_count_changed=(len(source_fields) != len(target_fields)),
            fields_added=fields_added,
            fields_removed=fields_removed,
            fields_modified=fields_modified,
            fields_unchanged=fields_unchanged,
            modification_percentage=modification_percentage,
            source_created_at=source_version.created_at,  # type: ignore
            target_created_at=target_version.created_at  # type: ignore
        )

    def _is_field_modified(
        self,
        source_field: TemplateField,
        target_field: TemplateField
    ) -> bool:
        """
        Check if a field has been modified.

        Args:
            source_field: Source version field
            target_field: Target version field

        Returns:
            bool: True if field has changes, False otherwise
        """
        # Check page number
        if source_field.page_number != target_field.page_number:
            return True

        # Check near text
        if source_field.near_text != target_field.near_text:
            return True

        # Check value options
        if self._compare_value_options(
            source_field.value_options,  # type: ignore
            target_field.value_options  # type: ignore
        ) == DiffStatus.DIFFERENT:
            return True

        # Check position
        if self._compare_positions(
            source_field.position_data,  # type: ignore
            target_field.position_data  # type: ignore
        ) == DiffStatus.DIFFERENT:
            return True

        return False

    def _compare_fields(
        self,
        source_fields: List[TemplateField],
        target_fields: List[TemplateField]
    ) -> List[FieldChange]:
        """
        Perform field-by-field comparison.

        Algorithm:
        1. Create dictionaries indexed by field_id
        2. Find added fields (in target, not in source)
        3. Find removed fields (in source, not in target)
        4. Find common fields and check for modifications
        5. Return sorted list of changes

        Args:
            source_fields: List of source version fields
            target_fields: List of target version fields

        Returns:
            List[FieldChange]: Detailed field-by-field comparison data
        """
        # Build field dictionaries
        source_fields_dict: Dict[str, TemplateField] = {
            str(f.field_id): f for f in source_fields  # type: ignore
        }
        target_fields_dict: Dict[str, TemplateField] = {
            str(f.field_id): f for f in target_fields  # type: ignore
        }

        # Get field ID sets
        source_field_ids = set(source_fields_dict.keys())
        target_field_ids = set(target_fields_dict.keys())

        field_changes: List[FieldChange] = []

        # 1. Find added fields
        added_field_ids = target_field_ids - source_field_ids
        for field_id in added_field_ids:
            target_field = target_fields_dict[field_id]
            field_changes.append(self._create_added_field_change(
                target_field
            ))

        # 2. Find removed fields
        removed_field_ids = source_field_ids - target_field_ids
        for field_id in removed_field_ids:
            source_field = source_fields_dict[field_id]
            field_changes.append(self._create_removed_field_change(
                source_field
            ))

        # 3. Find common fields and check for modifications
        common_field_ids = source_field_ids & target_field_ids
        for field_id in common_field_ids:
            source_field = source_fields_dict[field_id]
            target_field = target_fields_dict[field_id]
            field_changes.append(self._compare_field_attributes(
                source_field, target_field
            ))

        # Sort by field_id for consistent output
        field_changes.sort(key=lambda x: x.field_id)

        return field_changes

    def _create_added_field_change(
        self,
        target_field: TemplateField
    ) -> FieldChange:
        """
        Create FieldChange for an added field.

        Args:
            target_field: The field that was added

        Returns:
            FieldChange: Field change record for added field
        """
        return FieldChange(
            field_id=str(target_field.field_id),
            status=FieldChangeStatus.ADDED,
            field_type=str(target_field.field_type) if target_field.field_type else None,  # noqa: E501
            source_page_number=None,
            target_page_number=int(target_field.page_number),
            page_number_changed=False,
            near_text_diff=DiffStatus.NOT_APPLICABLE,
            source_near_text=None,
            target_near_text=str(target_field.near_text) if target_field.near_text else None,  # noqa: E501
            value_options_diff=DiffStatus.NOT_APPLICABLE,
            source_value_options=None,
            target_value_options=target_field.value_options,  # type: ignore
            position_change=DiffStatus.NOT_APPLICABLE,
            source_position=None,
            target_position=target_field.position_data  # type: ignore
        )

    def _create_removed_field_change(
        self,
        source_field: TemplateField
    ) -> FieldChange:
        """
        Create FieldChange for a removed field.

        Args:
            source_field: The field that was removed

        Returns:
            FieldChange: Field change record for removed field
        """
        return FieldChange(
            field_id=str(source_field.field_id),
            status=FieldChangeStatus.REMOVED,
            field_type=str(source_field.field_type) if source_field.field_type else None,  # noqa: E501
            source_page_number=int(source_field.page_number),
            target_page_number=None,
            page_number_changed=False,
            near_text_diff=DiffStatus.NOT_APPLICABLE,
            source_near_text=str(source_field.near_text) if source_field.near_text else None,  # noqa: E501
            target_near_text=None,
            value_options_diff=DiffStatus.NOT_APPLICABLE,
            source_value_options=source_field.value_options,  # type: ignore
            target_value_options=None,
            position_change=DiffStatus.NOT_APPLICABLE,
            source_position=source_field.position_data,  # type: ignore
            target_position=None
        )

    def _compare_field_attributes(
        self,
        source_field: TemplateField,
        target_field: TemplateField
    ) -> FieldChange:
        """
        Compare individual field attributes.

        Compares:
        - page_number
        - near_text
        - value_options (list comparison)
        - position_data (coordinate comparison with tolerance)

        Args:
            source_field: Source version field
            target_field: Target version field

        Returns:
            FieldChange: Detailed comparison of field attributes
        """
        # Compare page numbers
        page_number_changed = bool(
            source_field.page_number != target_field.page_number
        )

        # Compare near text
        near_text_diff = (
            DiffStatus.EQUAL if source_field.near_text == target_field.near_text  # noqa: E501
            else DiffStatus.DIFFERENT
        )

        # Compare value options
        value_options_diff = self._compare_value_options(
            source_field.value_options,  # type: ignore
            target_field.value_options  # type: ignore
        )

        # Compare positions
        position_change = self._compare_positions(
            source_field.position_data,  # type: ignore
            target_field.position_data  # type: ignore
        )

        # Determine overall status
        is_modified = (
            page_number_changed or
            near_text_diff == DiffStatus.DIFFERENT or
            value_options_diff == DiffStatus.DIFFERENT or
            position_change == DiffStatus.DIFFERENT
        )

        status = (
            FieldChangeStatus.MODIFIED if is_modified
            else FieldChangeStatus.UNCHANGED
        )

        return FieldChange(
            field_id=str(source_field.field_id),
            status=status,
            field_type=str(source_field.field_type) if source_field.field_type else None,  # noqa: E501
            source_page_number=int(source_field.page_number),
            target_page_number=int(target_field.page_number),
            page_number_changed=page_number_changed,
            near_text_diff=near_text_diff,
            source_near_text=str(source_field.near_text) if source_field.near_text else None,  # noqa: E501
            target_near_text=str(target_field.near_text) if target_field.near_text else None,  # noqa: E501
            value_options_diff=value_options_diff,
            source_value_options=source_field.value_options,  # type: ignore
            target_value_options=target_field.value_options,  # type: ignore
            position_change=position_change,
            source_position=source_field.position_data,  # type: ignore
            target_position=target_field.position_data  # type: ignore
        )

    def _compare_positions(
        self,
        source_pos: Optional[dict],
        target_pos: Optional[dict],
        tolerance: float = 5.0
    ) -> DiffStatus:
        """
        Compare field positions with tolerance.

        Considers positions equal if all coordinates are within tolerance.

        Args:
            source_pos: Source position {x0, y0, x1, y1}
            target_pos: Target position {x0, y0, x1, y1}
            tolerance: Maximum difference in pixels to consider equal

        Returns:
            DiffStatus: EQUAL, DIFFERENT, or NOT_APPLICABLE
        """
        if source_pos is None and target_pos is None:
            return DiffStatus.NOT_APPLICABLE

        if source_pos is None or target_pos is None:
            return DiffStatus.DIFFERENT

        # Compare each coordinate with tolerance
        for key in ['x0', 'y0', 'x1', 'y1']:
            source_val = source_pos.get(key, 0)
            target_val = target_pos.get(key, 0)

            if abs(source_val - target_val) > tolerance:
                return DiffStatus.DIFFERENT

        return DiffStatus.EQUAL

    def _compare_value_options(
        self,
        source_options: Optional[List[str]],
        target_options: Optional[List[str]]
    ) -> DiffStatus:
        """
        Compare value option lists.

        Args:
            source_options: Source value options
            target_options: Target value options

        Returns:
            DiffStatus: EQUAL, DIFFERENT, or NOT_APPLICABLE
        """
        # Both None or both empty list -> NOT_APPLICABLE
        if (source_options is None or len(source_options) == 0) and \
           (target_options is None or len(target_options) == 0):
            return DiffStatus.NOT_APPLICABLE

        # One has options, the other doesn't -> DIFFERENT
        if (source_options is None or len(source_options) == 0) != \
           (target_options is None or len(target_options) == 0):
            return DiffStatus.DIFFERENT

        # Both have options -> compare as sets
        source_set = set(source_options or [])
        target_set = set(target_options or [])

        return (
            DiffStatus.EQUAL if source_set == target_set
            else DiffStatus.DIFFERENT
        )

