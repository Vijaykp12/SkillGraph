import pytest
from unittest.mock import MagicMock, patch
from app.services.parser import parse_resume_pdf

def test_parse_resume_pdf_layout_and_heuristics():
    """Verifies that the resume parser extracts regex, database-driven, and heuristic list skills."""
    mock_text = """
    John Doe
    Software Engineer at TechCorp
    
    Summary:
    Experienced in full-stack web development.
    
    Technical Skills:
    Languages: Python, Go, Rust, TypeScript, JavaScript
    Frameworks: FastAPI, Django, React, Next.js, Express.js, PyTorch Geometric, Spring Boot
    Databases: Neo4j, PostgreSQL, Redis, MongoDB
    Tools: Docker, Kubernetes, Git, AWS, GitHub Actions, Terraform
    
    Experience:
    Software Engineer, 2021 - Present
    - Developed backend services using Python and FastAPI.
    - Managed containerized services with Docker and Kubernetes.
    """
    
    mock_page = MagicMock()
    mock_page.extract_text.return_value = mock_text
    
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]
    
    with patch("app.services.parser.PdfReader", return_value=mock_reader) as mock_pdf_class:
        # We pass some existing skills to match
        existing_skills = ["Python", "JavaScript", "Neo4j", "Docker", "Kubernetes"]
        
        parsed_data = parse_resume_pdf(b"dummy_pdf_bytes", existing_skills=existing_skills)
        
        skills = parsed_data["parsed_skills"]
        
        # Verify page layout extraction mode was requested
        mock_page.extract_text.assert_called_with(extraction_mode="layout")
        
        # Verify standard regex skills are matched
        assert "Python" in skills
        assert "JavaScript" in skills
        assert "Neo4j" in skills
        assert "Docker" in skills
        assert "Kubernetes" in skills
        
        # Verify expanded regex patterns are matched
        assert "FastAPI" in skills
        assert "Django" in skills
        assert "React" in skills
        assert "Next.js" in skills
        assert "Express.js" in skills
        assert "Spring Boot" in skills
        assert "PyTorch Geometric" in skills
        assert "GitHub Actions" in skills
        
        # Verify heuristically extracted custom skills (Go, Rust, TypeScript, MongoDB, Git, AWS, Terraform)
        assert "Go" in skills
        assert "Rust" in skills
        assert "TypeScript" in skills
        assert "MongoDB" in skills
        assert "Git" in skills
        assert "AWS" in skills
        assert "Terraform" in skills
        
        # Verify occupations are inferred correctly
        assert parsed_data["current_occupation"] == "Software Engineer"
        
        # Verify bio was constructed
        assert "Software Engineer" in parsed_data["bio"]
        assert len(parsed_data["parsed_experience"]) > 0
        assert parsed_data["parsed_experience"][0]["role"] == "Software Engineer"
