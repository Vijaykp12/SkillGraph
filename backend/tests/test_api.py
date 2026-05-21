from fastapi.testclient import TestClient
from app.main import app
from app.core.security import get_current_user
from app.models.models import User

def mock_get_current_user():
    return User(id=1, email="admin@skillgraph.ai", role="admin")

app.dependency_overrides[get_current_user] = mock_get_current_user

client = TestClient(app)

def test_api_root():
    """Verifies that the main service landing route returns online status."""
    res = client.get("/")
    assert res.status_code == 200
    assert res.json() == {
        "status": "online",
        "service": "SkillGraph Workforce Intelligence API"
    }

def test_skills_search():
    """Verifies that the FAISS semantic search endpoint returns matches."""
    res = client.get("/api/v1/skills/search?q=Python&limit=2")
    assert res.status_code == 200
    data = res.json()
    assert "query" in data
    assert "results" in data
    assert len(data["results"]) <= 2

def test_graph_explorer_mock_fallback():
    """Verifies that explorer queries fallback to mock nodes when DB is offline."""
    res = client.get("/api/v1/skills/explorer")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0
    # Core nodes like Python and Data Scientist must be present in mock fallback list
    node_names = [n["name"] for n in data["nodes"]]
    assert "Python" in node_names
