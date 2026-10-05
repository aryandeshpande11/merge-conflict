from fastapi.testclient import TestClient
from app.services.model_service import model_service


def test_health_healthy(client: TestClient):
    """Test 1: Health endpoint returns 200 OK when model is loaded."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert data["model_version"] == "v3"


def test_health_model_unavailable(client: TestClient):
    """Test 2: Health endpoint returns 503 when model is unavailable."""
    original_state = model_service.is_loaded
    try:
        model_service.is_loaded = False
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["model_loaded"] is False
    finally:
        model_service.is_loaded = original_state


def test_health_repeated_requests(client: TestClient):
    """Test 3: Repeated health requests produce consistent responses with no state corruption."""
    for _ in range(5):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["model_loaded"] is True
        assert data["model_version"] == "v3"
