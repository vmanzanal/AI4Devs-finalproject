"""
Template models for SEPE Templates Comparator.

This module defines the PDFTemplate and TemplateVersion SQLAlchemy models
for managing PDF template storage and versioning.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class PDFTemplate(Base):
    """PDF template model for storing template metadata and file information."""
    
    __tablename__ = "pdf_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    version = Column(String(50), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    field_count = Column(Integer, default=0)
    sepe_url = Column(String(1000), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
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
        return f"<PDFTemplate(id={self.id}, name='{self.name}', version='{self.version}')>"


class TemplateVersion(Base):
    """Template version model for tracking template change history."""
    
    __tablename__ = "template_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("pdf_templates.id"), nullable=False, index=True)
    version_number = Column(String(50), nullable=False)
    change_summary = Column(Text, nullable=True)
    is_current = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    template = relationship("PDFTemplate", back_populates="versions")
    
    def __repr__(self) -> str:
        return f"<TemplateVersion(id={self.id}, template_id={self.template_id}, version='{self.version_number}')>"
