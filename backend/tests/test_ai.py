import pytest
import numpy as np
from app.ai.embedder import embedder_instance
from app.ai.recommender import recommender

@pytest.fixture
def anyio_backend():
    return 'asyncio'

def test_embedder_vector_shape():
    """Verifies that the embedding generator outputs 384-dimensional floats."""
    text = "Machine Learning Engineer"
    vector = embedder_instance.get_embedding(text)
    
    assert isinstance(vector, np.ndarray)
    assert vector.shape == (384,)
    assert vector.dtype == np.float32

@pytest.mark.anyio
async def test_skill_dna_calculation():
    """Verifies that skill DNA scoring maps arrays into correct occupations."""
    user_skills = ["Python", "PyTorch", "React", "Next.js", "Docker"]
    dna = await recommender.get_skill_dna(user_skills)
    
    assert isinstance(dna, dict)
    assert "Machine Learning Engineer" in dna
    assert "Frontend Engineer" in dna
    # PyTorch and Python match ML Engineer; React and Next.js match Frontend Engineer
    assert dna["Machine Learning Engineer"] > 0.0
    assert dna["Frontend Engineer"] > 0.0

@pytest.mark.anyio
async def test_recommender_fallback_gap_analysis():
    """Verifies that gap analysis returns correct schemas in fallback mode."""
    user_skills = ["Python", "SQL"]
    target = "Data Scientist"
    
    gap = await recommender.analyze_skill_gap(user_skills, target)
    
    assert isinstance(gap, dict)
    assert gap["target_occupation"] == target
    assert "match_score" in gap
    assert "matching_skills" in gap
    assert "missing_skills" in gap

@pytest.mark.anyio
async def test_recommender_career_twin():
    """Verifies that career twin paths generate correct structural steps."""
    start = "Frontend Engineer"
    target = "DevOps Engineer"
    
    twin = await recommender.career_twin_simulation(start, target)
    
    assert isinstance(twin, dict)
    assert twin["start_occupation"] == start
    assert twin["target_occupation"] == target
    assert "path_sequence" in twin
    assert len(twin["path_sequence"]) > 0
    assert "momentum_score" in twin
