"""
Template models for SEPE Templates Comparator.

This module defines the PDFTemplate, TemplateVersion, and TemplateField
SQLAlchemy models for managing PDF template storage, versioning, and
extracted AcroForm field data.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
    JSON
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class PDFTemplate(Base):
    """PDF template model for template metadata and file information."""

    __tablename__ = "pdf_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    version = Column(String(50), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    field_count = Column(Integer, default=0)
    sepe_url = Column(String(1000), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    uploader = relationship("User", back_populates="uploaded_templates")
    versions = relationship(
        "TemplateVersion",
        back_populates="template",
        cascade="all, delete-orphan"
    )
    source_comparisons = relationship(
        "Comparison",
        foreign_keys="Comparison.source_template_id",
        back_populates="source_template"
    )
    target_comparisons = relationship(
        "Comparison",
        foreign_keys="Comparison.target_template_id",
        back_populates="target_template"
    )

    def __repr__(self) -> str:
        return (
            f"<PDFTemplate(id={self.id}, name='{self.name}', "
            f"version='{self.version}')>"
        )


class TemplateVersion(Base):
    """Template version model for tracking template change history."""

    __tablename__ = "template_versions"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("pdf_templates.id"),
        nullable=False,
        index=True
    )
    version_number = Column(String(50), nullable=False)
    change_summary = Column(Text, nullable=True)
    is_current = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # PDF Document Metadata
    title = Column(String(255), nullable=True)
    author = Column(String(255), nullable=True)
    subject = Column(String(255), nullable=True)
    creation_date = Column(DateTime(timezone=True), nullable=True)
    modification_date = Column(DateTime(timezone=True), nullable=True)
    page_count = Column(Integer, nullable=False, default=0)

    # Relationships
    template = relationship("PDFTemplate", back_populates="versions")
    fields = relationship(
        "TemplateField",
        back_populates="version",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<TemplateVersion(id={self.id}, "
            f"template_id={self.template_id}, "
            f"version='{self.version_number}')>"
        )


class TemplateField(Base):
    """Template field model for storing extracted PDF AcroForm data."""

    __tablename__ = "template_fields"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Key to template_versions
    version_id = Column(
        Integer,
        ForeignKey("template_versions.id"),
        nullable=False,
        index=True
    )

    # Field Identification
    field_id = Column(String(255), nullable=False)
    field_type = Column(String(50), nullable=False)
    raw_type = Column(String(50), nullable=True)

    # Page Information
    page_number = Column(Integer, nullable=False)
    field_page_order = Column(Integer, nullable=False)

    # Field Content
    near_text = Column(Text, nullable=True)

    # JSON Fields (using JSONB for PostgreSQL)
    value_options = Column(JSON, nullable=True)
    position_data = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    version = relationship("TemplateVersion", back_populates="fields")

    def __repr__(self) -> str:
        return (
            f"<TemplateField(id={self.id}, version_id={self.version_id}, "
            f"field_id='{self.field_id}', type='{self.field_type}')>"
        )
