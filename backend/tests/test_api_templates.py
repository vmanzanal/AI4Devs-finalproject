"""
Tests for template API endpoints.
"""

import os
import tempfile
from io import BytesIO
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, create_access_token
from app.models.user import User
from app.models.template import PDFTemplate


class TestTemplateEndpoints:
    """Test cases for template endpoints."""
    
    @pytest.fixture
    def test_user(self, db: Session) -> User:
        """Create a test user."""
        user = User(
            email="testuser@example.com",
            hashed_password=get_password_hash("testpassword123"),
            full_name="Test User",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @pytest.fixture
    def auth_headers(self, test_user: User) -> dict:
        """Create authentication headers for test user."""
        token = create_access_token(subject=test_user.id)
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture
    def sample_pdf_content(self) -> bytes:
        """Create sample PDF content for testing."""
        # This is a minimal PDF content for testing
        return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000125 00000 n 
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
185
%%EOF"""
    
    def test_upload_template_valid(self, client: TestClient, auth_headers: dict, sample_pdf_content: bytes):
        """Test uploading a valid PDF template."""
        files = {
            "file": ("test_template.pdf", BytesIO(sample_pdf_content), "application/pdf")
        }
        data = {
            "name": "Test Template",
            "version": "1.0",
            "sepe_url": "https://www.sepe.es/test-template"
        }
        
        response = client.post(
            "/api/v1/templates/upload",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        result = response.json()
        assert result["name"] == "Test Template"
        assert result["version"] == "1.0"
        assert result["file_size_bytes"] > 0
        assert "id" in result
        assert result["message"] == "Template uploaded successfully"
    
    def test_upload_template_unauthorized(self, client: TestClient, sample_pdf_content: bytes):
        """Test uploading template without authentication."""
        files = {
            "file": ("test_template.pdf", BytesIO(sample_pdf_content), "application/pdf")
        }
        data = {
            "name": "Test Template",
            "version": "1.0"
        }
        
        response = client.post(
            "/api/v1/templates/upload",
            files=files,
            data=data
        )
        
        assert response.status_code == 403  # Forbidden
    
    def test_upload_template_invalid_file_type(self, client: TestClient, auth_headers: dict):
        """Test uploading non-PDF file."""
        files = {
            "file": ("test_file.txt", BytesIO(b"This is not a PDF"), "text/plain")
        }
        data = {
            "name": "Test Template",
            "version": "1.0"
        }
        
        response = client.post(
            "/api/v1/templates/upload",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Only PDF files are allowed" in response.json()["detail"]
    
    def test_list_templates_empty(self, client: TestClient):
        """Test listing templates when none exist."""
        response = client.get("/api/v1/templates/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["limit"] == 10
        assert data["offset"] == 0
    
    def test_list_templates_with_data(self, client: TestClient, db: Session, test_user: User):
        """Test listing templates with existing data."""
        # Create test templates
        template1 = PDFTemplate(
            name="Template 1",
            version="1.0",
            file_path="/fake/path/template1.pdf",
            file_size_bytes=1024,
            field_count=5,
            uploaded_by=test_user.id
        )
        template2 = PDFTemplate(
            name="Template 2",
            version="2.0",
            file_path="/fake/path/template2.pdf",
            file_size_bytes=2048,
            field_count=10,
            uploaded_by=test_user.id
        )
        
        db.add_all([template1, template2])
        db.commit()
        
        response = client.get("/api/v1/templates/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2
        
        # Check that templates are returned
        template_names = [item["name"] for item in data["items"]]
        assert "Template 1" in template_names
        assert "Template 2" in template_names
    
    def test_list_templates_pagination(self, client: TestClient, db: Session, test_user: User):
        """Test template list pagination."""
        # Create multiple templates
        templates = []
        for i in range(15):
            template = PDFTemplate(
                name=f"Template {i}",
                version="1.0",
                file_path=f"/fake/path/template{i}.pdf",
                file_size_bytes=1024,
                field_count=5,
                uploaded_by=test_user.id
            )
            templates.append(template)
        
        db.add_all(templates)
        db.commit()
        
        # Test first page
        response = client.get("/api/v1/templates/?limit=10&skip=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] == 15
        
        # Test second page
        response = client.get("/api/v1/templates/?limit=10&skip=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total"] == 15
    
    def test_list_templates_search(self, client: TestClient, db: Session, test_user: User):
        """Test template search functionality."""
        # Create test templates
        template1 = PDFTemplate(
            name="Employment Form",
            version="1.0",
            file_path="/fake/path/employment.pdf",
            file_size_bytes=1024,
            field_count=5,
            uploaded_by=test_user.id
        )
        template2 = PDFTemplate(
            name="Unemployment Benefit",
            version="1.0",
            file_path="/fake/path/benefit.pdf",
            file_size_bytes=2048,
            field_count=10,
            uploaded_by=test_user.id
        )
        
        db.add_all([template1, template2])
        db.commit()
        
        # Search for "employment"
        response = client.get("/api/v1/templates/?search=employment")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Employment Form"
        
        # Search for "benefit"
        response = client.get("/api/v1/templates/?search=benefit")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Unemployment Benefit"
    
    def test_get_template_valid_id(self, client: TestClient, db: Session, test_user: User):
        """Test getting template by valid ID."""
        template = PDFTemplate(
            name="Test Template",
            version="1.0",
            file_path="/fake/path/template.pdf",
            file_size_bytes=1024,
            field_count=5,
            sepe_url="https://www.sepe.es/test",
            uploaded_by=test_user.id
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        
        response = client.get(f"/api/v1/templates/{template.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == template.id
        assert data["name"] == "Test Template"
        assert data["version"] == "1.0"
        assert data["sepe_url"] == "https://www.sepe.es/test"
        assert data["uploaded_by"] == test_user.id
    
    def test_get_template_invalid_id(self, client: TestClient):
        """Test getting template by invalid ID."""
        response = client.get("/api/v1/templates/99999")
        
        assert response.status_code == 404
        assert "Template not found" in response.json()["detail"]
    
    def test_update_template_owner(self, client: TestClient, db: Session, test_user: User, auth_headers: dict):
        """Test updating template by owner."""
        template = PDFTemplate(
            name="Original Name",
            version="1.0",
            file_path="/fake/path/template.pdf",
            file_size_bytes=1024,
            field_count=5,
            uploaded_by=test_user.id
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        
        update_data = {
            "name": "Updated Name",
            "version": "2.0",
            "sepe_url": "https://www.sepe.es/updated"
        }
        
        response = client.put(
            f"/api/v1/templates/{template.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["version"] == "2.0"
        assert data["sepe_url"] == "https://www.sepe.es/updated"
    
    def test_update_template_unauthorized(self, client: TestClient, db: Session, test_user: User):
        """Test updating template without authentication."""
        template = PDFTemplate(
            name="Test Template",
            version="1.0",
            file_path="/fake/path/template.pdf",
            file_size_bytes=1024,
            field_count=5,
            uploaded_by=test_user.id
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        
        update_data = {"name": "Updated Name"}
        
        response = client.put(f"/api/v1/templates/{template.id}", json=update_data)
        
        assert response.status_code == 403  # Forbidden
    
    def test_update_template_not_owner(self, client: TestClient, db: Session, test_user: User):
        """Test updating template by non-owner."""
        # Create another user
        other_user = User(
            email="other@example.com",
            hashed_password=get_password_hash("password123"),
            full_name="Other User",
            is_active=True
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)
        
        # Create template owned by other user
        template = PDFTemplate(
            name="Test Template",
            version="1.0",
            file_path="/fake/path/template.pdf",
            file_size_bytes=1024,
            field_count=5,
            uploaded_by=other_user.id
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        
        # Try to update with test_user token
        token = create_access_token(subject=test_user.id)
        headers = {"Authorization": f"Bearer {token}"}
        update_data = {"name": "Updated Name"}
        
        response = client.put(
            f"/api/v1/templates/{template.id}",
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == 403
        assert "Not enough permissions" in response.json()["detail"]
    
    def test_delete_template_owner(self, client: TestClient, db: Session, test_user: User, auth_headers: dict):
        """Test deleting template by owner."""
        template = PDFTemplate(
            name="Test Template",
            version="1.0",
            file_path="/fake/path/template.pdf",
            file_size_bytes=1024,
            field_count=5,
            uploaded_by=test_user.id
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        
        response = client.delete(f"/api/v1/templates/{template.id}", headers=auth_headers)
        
        assert response.status_code == 200
        assert "Template deleted successfully" in response.json()["message"]
        
        # Verify template was deleted
        deleted_template = db.query(PDFTemplate).filter(PDFTemplate.id == template.id).first()
        assert deleted_template is None
    
    def test_delete_template_not_found(self, client: TestClient, auth_headers: dict):
        """Test deleting non-existent template."""
        response = client.delete("/api/v1/templates/99999", headers=auth_headers)
        
        assert response.status_code == 404
        assert "Template not found" in response.json()["detail"]
