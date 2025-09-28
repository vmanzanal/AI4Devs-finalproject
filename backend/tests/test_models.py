"""
Tests for SQLAlchemy database models.
"""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.models.template import PDFTemplate, TemplateVersion
from app.models.comparison import Comparison, ComparisonField


class TestUserModel:
    """Test cases for User model."""
    
    def test_user_creation(self, db_session):
        """Test creating a new user."""
        user = User(
            email="test@example.com",
            hashed_password="hashed_password_123",
            full_name="Test User"
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)
    
    def test_user_email_uniqueness(self, db_session):
        """Test that user email must be unique."""
        user1 = User(
            email="duplicate@example.com",
            hashed_password="password1"
        )
        user2 = User(
            email="duplicate@example.com",
            hashed_password="password2"
        )
        
        db_session.add(user1)
        db_session.commit()
        
        db_session.add(user2)
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_user_string_representation(self, db_session):
        """Test user string representation."""
        user = User(
            email="repr@example.com",
            hashed_password="password",
            full_name="Repr User"
        )
        db_session.add(user)
        db_session.commit()
        
        assert "repr@example.com" in str(user)


class TestPDFTemplateModel:
    """Test cases for PDFTemplate model."""
    
    def test_template_creation(self, db_session):
        """Test creating a new PDF template."""
        # Create a user first (foreign key requirement)
        user = User(
            email="uploader@example.com",
            hashed_password="password"
        )
        db_session.add(user)
        db_session.commit()
        
        template = PDFTemplate(
            name="Test Template",
            version="1.0.0",
            file_path="/uploads/test_template.pdf",
            file_size_bytes=245760,
            field_count=25,
            sepe_url="https://www.sepe.es/test",
            uploaded_by=user.id
        )
        db_session.add(template)
        db_session.commit()
        
        assert template.id is not None
        assert template.name == "Test Template"
        assert template.version == "1.0.0"
        assert template.file_size_bytes == 245760
        assert template.field_count == 25
        assert template.uploaded_by == user.id
        assert template.created_at is not None
    
    def test_template_string_representation(self, db_session):
        """Test template string representation."""
        template = PDFTemplate(
            name="Repr Template",
            version="2.0.0",
            file_path="/test.pdf",
            file_size_bytes=1000
        )
        db_session.add(template)
        db_session.commit()
        
        repr_str = str(template)
        assert "Repr Template" in repr_str
        assert "2.0.0" in repr_str


class TestTemplateVersionModel:
    """Test cases for TemplateVersion model."""
    
    def test_template_version_creation(self, db_session):
        """Test creating a template version."""
        template = PDFTemplate(
            name="Versioned Template",
            version="1.0.0",
            file_path="/test.pdf",
            file_size_bytes=1000
        )
        db_session.add(template)
        db_session.commit()
        
        version = TemplateVersion(
            template_id=template.id,
            version_number="1.0.0",
            change_summary="Initial version",
            is_current=True
        )
        db_session.add(version)
        db_session.commit()
        
        assert version.id is not None
        assert version.template_id == template.id
        assert version.version_number == "1.0.0"
        assert version.change_summary == "Initial version"
        assert version.is_current is True
        assert version.created_at is not None


class TestComparisonModel:
    """Test cases for Comparison model."""
    
    def test_comparison_creation(self, db_session):
        """Test creating a comparison."""
        # Create user and templates
        user = User(
            email="comparator@example.com",
            hashed_password="password"
        )
        db_session.add(user)
        db_session.commit()
        
        template1 = PDFTemplate(
            name="Template A",
            version="1.0.0",
            file_path="/template_a.pdf",
            file_size_bytes=1000
        )
        template2 = PDFTemplate(
            name="Template B",
            version="2.0.0",
            file_path="/template_b.pdf",
            file_size_bytes=1200
        )
        db_session.add_all([template1, template2])
        db_session.commit()
        
        comparison = Comparison(
            source_template_id=template1.id,
            target_template_id=template2.id,
            comparison_type="structure",
            status="pending",
            created_by=user.id
        )
        db_session.add(comparison)
        db_session.commit()
        
        assert comparison.id is not None
        assert comparison.source_template_id == template1.id
        assert comparison.target_template_id == template2.id
        assert comparison.comparison_type == "structure"
        assert comparison.status == "pending"
        assert comparison.differences_count == 0
        assert comparison.created_by == user.id
        assert comparison.created_at is not None


class TestComparisonFieldModel:
    """Test cases for ComparisonField model."""
    
    def test_comparison_field_creation(self, db_session):
        """Test creating a comparison field."""
        # Create necessary parent records
        user = User(
            email="field_test@example.com",
            hashed_password="password"
        )
        template1 = PDFTemplate(
            name="Template 1",
            version="1.0.0",
            file_path="/t1.pdf",
            file_size_bytes=1000
        )
        template2 = PDFTemplate(
            name="Template 2",
            version="1.0.0",
            file_path="/t2.pdf",
            file_size_bytes=1000
        )
        db_session.add_all([user, template1, template2])
        db_session.commit()
        
        comparison = Comparison(
            source_template_id=template1.id,
            target_template_id=template2.id,
            created_by=user.id
        )
        db_session.add(comparison)
        db_session.commit()
        
        field = ComparisonField(
            comparison_id=comparison.id,
            field_name="applicant_name",
            field_type="text",
            change_type="modified",
            old_value="text_field",
            new_value="text_field_required",
            position_x=100.5,
            position_y=200.5
        )
        db_session.add(field)
        db_session.commit()
        
        assert field.id is not None
        assert field.comparison_id == comparison.id
        assert field.field_name == "applicant_name"
        assert field.change_type == "modified"
        assert field.old_value == "text_field"
        assert field.new_value == "text_field_required"
        assert field.position_x == 100.5
        assert field.position_y == 200.5
        assert field.created_at is not None
