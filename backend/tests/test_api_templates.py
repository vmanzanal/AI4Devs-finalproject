"""
Tests for template CRUD API endpoints.

Note: Template ingestion tests are in test_ingest_endpoint.py
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, create_access_token
from app.models.user import User
from app.models.template import PDFTemplate, TemplateVersion, TemplateField


class TestTemplateEndpoints:
    """Test cases for template CRUD endpoints."""
    
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
        token = create_access_token(subject=str(test_user.id))
        return {"Authorization": f"Bearer {token}"}
    
    def create_template_with_version(
        self, 
        db: Session, 
        name: str, 
        version: str, 
        user_id: int,
        file_path: str = None,
        file_size_bytes: int = 1024,
        field_count: int = 5
    ) -> PDFTemplate:
        """Helper to create a template with its current version."""
        template = PDFTemplate(
            name=name,
            current_version=version,
            uploaded_by=user_id
        )
        db.add(template)
        db.flush()  # Get template.id
        
        version_record = TemplateVersion(
            template_id=template.id,
            version_number=version,
            file_path=file_path or f"/fake/path/{name.replace(' ', '_')}.pdf",
            file_size_bytes=file_size_bytes,
            field_count=field_count,
            is_current=True,
            page_count=1
        )
        db.add(version_record)
        db.commit()
        db.refresh(template)
        return template
    
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
        # Create test templates with current versions
        template1 = PDFTemplate(
            name="Template 1",
            current_version="1.0",
            uploaded_by=test_user.id
        )
        template2 = PDFTemplate(
            name="Template 2",
            current_version="2.0",
            uploaded_by=test_user.id
        )
        
        db.add_all([template1, template2])
        db.commit()
        
        # Create current versions
        version1 = TemplateVersion(
            template_id=template1.id,
            version_number="1.0",
            file_path="/fake/path/template1.pdf",
            file_size_bytes=1024,
            field_count=5,
            is_current=True,
            page_count=1
        )
        version2 = TemplateVersion(
            template_id=template2.id,
            version_number="2.0",
            file_path="/fake/path/template2.pdf",
            file_size_bytes=2048,
            field_count=10,
            is_current=True,
            page_count=1
        )
        
        db.add_all([version1, version2])
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
        # Create multiple templates with versions
        for i in range(15):
            self.create_template_with_version(
                db, f"Template {i}", "1.0", test_user.id
            )
        
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
        # Create test templates with versions
        self.create_template_with_version(db, "Employment Form", "1.0", test_user.id)
        self.create_template_with_version(db, "Unemployment Benefit", "1.0", test_user.id)
        
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
    
    # Download Endpoint Tests
    
    def test_download_template_success(self, client: TestClient, db: Session, test_user: User, auth_headers: dict, tmp_path):
        """Test downloading template PDF successfully."""
        # Create a temporary PDF file
        pdf_path = tmp_path / "test_template.pdf"
        pdf_content = b"%PDF-1.4\nTest PDF content"
        pdf_path.write_bytes(pdf_content)
        
        # Create template with actual file
        template = PDFTemplate(
            name="Test Template",
            version="1.0",
            file_path=str(pdf_path),
            file_size_bytes=len(pdf_content),
            field_count=5,
            uploaded_by=test_user.id
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        
        response = client.get(f"/api/v1/templates/{template.id}/download", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers["content-disposition"]
        assert "Test_Template_v1.0.pdf" in response.headers["content-disposition"]
        assert response.content == pdf_content
    
    def test_download_template_not_found(self, client: TestClient, auth_headers: dict):
        """Test downloading non-existent template."""
        response = client.get("/api/v1/templates/99999/download", headers=auth_headers)
        
        assert response.status_code == 404
        assert "Template not found" in response.json()["detail"]
    
    def test_download_template_file_not_found(self, client: TestClient, db: Session, test_user: User, auth_headers: dict):
        """Test downloading template when PDF file doesn't exist on disk."""
        template = PDFTemplate(
            name="Test Template",
            version="1.0",
            file_path="/nonexistent/path/template.pdf",
            file_size_bytes=1024,
            field_count=5,
            uploaded_by=test_user.id
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        
        response = client.get(f"/api/v1/templates/{template.id}/download", headers=auth_headers)
        
        assert response.status_code == 404
        assert "PDF file not found" in response.json()["detail"]
    
    def test_download_template_unauthorized(self, client: TestClient, db: Session, test_user: User, tmp_path):
        """Test downloading template without authentication."""
        pdf_path = tmp_path / "test_template.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\nTest")
        
        template = PDFTemplate(
            name="Test Template",
            version="1.0",
            file_path=str(pdf_path),
            file_size_bytes=100,
            field_count=5,
            uploaded_by=test_user.id
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        
        response = client.get(f"/api/v1/templates/{template.id}/download")
        
        assert response.status_code == 403  # Not authenticated
    
    def test_download_template_special_characters_in_name(self, client: TestClient, db: Session, test_user: User, auth_headers: dict, tmp_path):
        """Test downloading template with special characters in filename."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\nTest")
        
        template = PDFTemplate(
            name="Template & Test (Special)",
            version="1.0-alpha",
            file_path=str(pdf_path),
            file_size_bytes=100,
            field_count=5,
            uploaded_by=test_user.id
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        
        response = client.get(f"/api/v1/templates/{template.id}/download", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        # Filename should be sanitized
        assert "attachment" in response.headers["content-disposition"]
    
    # Version Endpoints Tests (Enhanced with pagination)
    
    def test_get_template_versions_with_pagination(self, client: TestClient, db: Session, test_user: User):
        """Test getting template versions with pagination and sorting."""
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
        
        # Create multiple versions
        for i in range(5):
            version = TemplateVersion(
                template_id=template.id,
                version_number=f"1.{i}",
                change_summary=f"Changes in version 1.{i}",
                is_current=(i == 4),  # Last one is current
                title=f"SEPE Form v1.{i}",
                author="SEPE",
                subject="Employment Registration",
                page_count=3 + i
            )
            db.add(version)
        db.commit()
        
        # Test first page
        response = client.get(f"/api/v1/templates/{template.id}/versions?limit=3&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 5
        assert data["limit"] == 3
        assert data["offset"] == 0
        
        # Test sorting (newest first by default)
        assert data["items"][0]["version_number"] == "1.4"
        assert data["items"][0]["is_current"] is True
    
    def test_get_template_versions_metadata(self, client: TestClient, db: Session, test_user: User):
        """Test that version metadata is included in response."""
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
        
        version = TemplateVersion(
            template_id=template.id,
            version_number="1.0",
            change_summary="Initial version",
            is_current=True,
            title="SEPE Employment Form 2024",
            author="SEPE - Servicio Público de Empleo Estatal",
            subject="Employment Registration",
            creation_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
            modification_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            page_count=5
        )
        db.add(version)
        db.commit()
        
        response = client.get(f"/api/v1/templates/{template.id}/versions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        
        version_data = data["items"][0]
        assert version_data["title"] == "SEPE Employment Form 2024"
        assert version_data["author"] == "SEPE - Servicio Público de Empleo Estatal"
        assert version_data["subject"] == "Employment Registration"
        assert version_data["page_count"] == 5
    
    def test_get_template_versions_sorting(self, client: TestClient, db: Session, test_user: User):
        """Test template versions with different sorting options."""
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
        
        # Create versions
        version1 = TemplateVersion(
            template_id=template.id,
            version_number="1.0",
            is_current=False,
            page_count=3
        )
        version2 = TemplateVersion(
            template_id=template.id,
            version_number="2.0",
            is_current=True,
            page_count=5
        )
        db.add_all([version1, version2])
        db.commit()
        
        # Test ascending order
        response = client.get(f"/api/v1/templates/{template.id}/versions?sort_order=asc")
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["version_number"] == "1.0"
        
        # Test descending order (default)
        response = client.get(f"/api/v1/templates/{template.id}/versions?sort_order=desc")
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["version_number"] == "2.0"
    
    # Current Version Fields Endpoint Tests
    
    def test_get_current_version_fields_success(self, client: TestClient, db: Session, test_user: User):
        """Test getting fields from current version."""
        template = PDFTemplate(
            name="Test Template",
            version="1.0",
            file_path="/fake/path/template.pdf",
            file_size_bytes=1024,
            field_count=2,
            uploaded_by=test_user.id
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        
        version = TemplateVersion(
            template_id=template.id,
            version_number="1.0",
            is_current=True,
            page_count=1
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        
        # Create fields
        field1 = TemplateField(
            version_id=version.id,
            field_id="A0101",
            field_type="text",
            raw_type="/Tx",
            page_number=1,
            field_page_order=0,
            near_text="Nombre completo:",
            value_options=None,
            position_data={"x0": 100, "y0": 200, "x1": 300, "y1": 220}
        )
        field2 = TemplateField(
            version_id=version.id,
            field_id="A0102",
            field_type="radiobutton",
            raw_type="/Btn",
            page_number=1,
            field_page_order=1,
            near_text="Sexo:",
            value_options=["Hombre", "Mujer", "Otro"],
            position_data={"x0": 100, "y0": 240, "x1": 200, "y1": 260}
        )
        db.add_all([field1, field2])
        db.commit()
        
        response = client.get(f"/api/v1/templates/{template.id}/fields/current")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["version_info"]["version_number"] == "1.0"
        assert data["version_info"]["field_count"] == 2
        
        # Check field ordering (by page_number, then field_page_order)
        assert data["items"][0]["field_id"] == "A0101"
        assert data["items"][1]["field_id"] == "A0102"
    
    def test_get_current_version_fields_pagination(self, client: TestClient, db: Session, test_user: User):
        """Test pagination for current version fields."""
        template = PDFTemplate(
            name="Test Template",
            version="1.0",
            file_path="/fake/path/template.pdf",
            file_size_bytes=1024,
            field_count=25,
            uploaded_by=test_user.id
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        
        version = TemplateVersion(
            template_id=template.id,
            version_number="1.0",
            is_current=True,
            page_count=3
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        
        # Create 25 fields
        for i in range(25):
            field = TemplateField(
                version_id=version.id,
                field_id=f"A{i:04d}",
                field_type="text",
                page_number=(i // 10) + 1,
                field_page_order=i % 10,
                near_text=f"Field {i}"
            )
            db.add(field)
        db.commit()
        
        # Test first page
        response = client.get(f"/api/v1/templates/{template.id}/fields/current?limit=20&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 20
        assert data["total"] == 25
        
        # Test second page
        response = client.get(f"/api/v1/templates/{template.id}/fields/current?limit=20&offset=20")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
    
    def test_get_current_version_fields_search(self, client: TestClient, db: Session, test_user: User):
        """Test search functionality for current version fields."""
        template = PDFTemplate(
            name="Test Template",
            version="1.0",
            file_path="/fake/path/template.pdf",
            file_size_bytes=1024,
            field_count=3,
            uploaded_by=test_user.id
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        
        version = TemplateVersion(
            template_id=template.id,
            version_number="1.0",
            is_current=True,
            page_count=1
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        
        field1 = TemplateField(
            version_id=version.id,
            field_id="NAME_FIELD",
            field_type="text",
            page_number=1,
            field_page_order=0,
            near_text="Nombre completo del solicitante"
        )
        field2 = TemplateField(
            version_id=version.id,
            field_id="EMAIL_FIELD",
            field_type="text",
            page_number=1,
            field_page_order=1,
            near_text="Correo electrónico"
        )
        field3 = TemplateField(
            version_id=version.id,
            field_id="PHONE_FIELD",
            field_type="text",
            page_number=1,
            field_page_order=2,
            near_text="Número de teléfono"
        )
        db.add_all([field1, field2, field3])
        db.commit()
        
        # Search by field_id
        response = client.get(f"/api/v1/templates/{template.id}/fields/current?search=NAME")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["field_id"] == "NAME_FIELD"
        
        # Search by near_text
        response = client.get(f"/api/v1/templates/{template.id}/fields/current?search=correo")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["field_id"] == "EMAIL_FIELD"
    
    def test_get_current_version_fields_page_filter(self, client: TestClient, db: Session, test_user: User):
        """Test filtering fields by page number."""
        template = PDFTemplate(
            name="Test Template",
            version="1.0",
            file_path="/fake/path/template.pdf",
            file_size_bytes=1024,
            field_count=6,
            uploaded_by=test_user.id
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        
        version = TemplateVersion(
            template_id=template.id,
            version_number="1.0",
            is_current=True,
            page_count=3
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        
        # Create fields on different pages
        for page in [1, 1, 2, 2, 3, 3]:
            field = TemplateField(
                version_id=version.id,
                field_id=f"FIELD_PAGE_{page}",
                field_type="text",
                page_number=page,
                field_page_order=0,
                near_text=f"Field on page {page}"
            )
            db.add(field)
        db.commit()
        
        # Filter by page 2
        response = client.get(f"/api/v1/templates/{template.id}/fields/current?page_number=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(item["page_number"] == 2 for item in data["items"])
    
    def test_get_current_version_fields_no_current_version(self, client: TestClient, db: Session, test_user: User):
        """Test getting fields when no current version exists."""
        template = PDFTemplate(
            name="Test Template",
            version="1.0",
            file_path="/fake/path/template.pdf",
            file_size_bytes=1024,
            field_count=0,
            uploaded_by=test_user.id
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        
        response = client.get(f"/api/v1/templates/{template.id}/fields/current")
        assert response.status_code == 404
        assert "No current version found" in response.json()["detail"]
    
    # Specific Version Fields Endpoint Tests
    
    def test_get_version_fields_success(self, client: TestClient, db: Session, test_user: User):
        """Test getting fields from specific version."""
        template = PDFTemplate(
            name="Test Template",
            version="1.0",
            file_path="/fake/path/template.pdf",
            file_size_bytes=1024,
            field_count=2,
            uploaded_by=test_user.id
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        
        version = TemplateVersion(
            template_id=template.id,
            version_number="1.0",
            is_current=False,
            page_count=1
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        
        field = TemplateField(
            version_id=version.id,
            field_id="A0101",
            field_type="text",
            page_number=1,
            field_page_order=0,
            near_text="Test field"
        )
        db.add(field)
        db.commit()
        
        response = client.get(f"/api/v1/templates/{template.id}/versions/{version.id}/fields")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["field_id"] == "A0101"
        assert data["version_info"]["version_id"] == version.id
    
    def test_get_version_fields_version_mismatch(self, client: TestClient, db: Session, test_user: User):
        """Test getting fields when version doesn't belong to template."""
        template1 = PDFTemplate(
            name="Template 1",
            version="1.0",
            file_path="/fake/path/template1.pdf",
            file_size_bytes=1024,
            field_count=0,
            uploaded_by=test_user.id
        )
        template2 = PDFTemplate(
            name="Template 2",
            version="1.0",
            file_path="/fake/path/template2.pdf",
            file_size_bytes=1024,
            field_count=0,
            uploaded_by=test_user.id
        )
        db.add_all([template1, template2])
        db.commit()
        db.refresh(template1)
        db.refresh(template2)
        
        version = TemplateVersion(
            template_id=template2.id,
            version_number="1.0",
            is_current=True,
            page_count=1
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        
        # Try to access version from wrong template
        response = client.get(f"/api/v1/templates/{template1.id}/versions/{version.id}/fields")
        assert response.status_code == 400
        assert "does not belong to" in response.json()["detail"]
    
    def test_get_version_fields_version_not_found(self, client: TestClient, db: Session, test_user: User):
        """Test getting fields from non-existent version."""
        template = PDFTemplate(
            name="Test Template",
            version="1.0",
            file_path="/fake/path/template.pdf",
            file_size_bytes=1024,
            field_count=0,
            uploaded_by=test_user.id
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        
        response = client.get(f"/api/v1/templates/{template.id}/versions/99999/fields")
        assert response.status_code == 404
        assert "Version not found" in response.json()["detail"]