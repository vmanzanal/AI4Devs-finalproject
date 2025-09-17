"""
Comparison models for SEPE Templates Comparator.

This module defines the Comparison and ComparisonField SQLAlchemy models
for managing template comparisons and detailed field-level differences.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Comparison(Base):
    """Comparison model for storing template comparison metadata and results."""
    
    __tablename__ = "comparisons"
    
    id = Column(Integer, primary_key=True, index=True)
    source_template_id = Column(Integer, ForeignKey("pdf_templates.id"), nullable=False, index=True)
    target_template_id = Column(Integer, ForeignKey("pdf_templates.id"), nullable=False, index=True)
    comparison_type = Column(String(50), default="structure")
    status = Column(String(50), default="pending", index=True)
    differences_count = Column(Integer, default=0)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    source_template = relationship(
        "PDFTemplate",
        foreign_keys=[source_template_id],
        back_populates="source_comparisons"
    )
    target_template = relationship(
        "PDFTemplate", 
        foreign_keys=[target_template_id],
        back_populates="target_comparisons"
    )
    creator = relationship("User", back_populates="created_comparisons")
    field_differences = relationship(
        "ComparisonField",
        back_populates="comparison",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Comparison(id={self.id}, source={self.source_template_id}, target={self.target_template_id}, status='{self.status}')>"


class ComparisonField(Base):
    """Comparison field model for storing detailed field-level differences."""
    
    __tablename__ = "comparison_fields"
    
    id = Column(Integer, primary_key=True, index=True)
    comparison_id = Column(Integer, ForeignKey("comparisons.id"), nullable=False, index=True)
    field_name = Column(String(255), nullable=False)
    field_type = Column(String(100), nullable=True)
    change_type = Column(String(50), nullable=True, index=True)  # 'added', 'removed', 'modified', 'unchanged'
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    position_x = Column(Float, nullable=True)
    position_y = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    comparison = relationship("Comparison", back_populates="field_differences")
    
    def __repr__(self) -> str:
        return f"<ComparisonField(id={self.id}, comparison_id={self.comparison_id}, field='{self.field_name}', change='{self.change_type}')>"
