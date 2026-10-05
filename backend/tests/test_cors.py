from fastapi.testclient import TestClient


def test_cors_allowed_origin(client: TestClient):
    """Test 39: Preflight / request from allowed origin receives appropriate CORS headers."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
    }
    response = client.options("/api/v1/predict", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_disallowed_origin(client: TestClient):
    """Test 39: Request from unauthorized origin does not receive access-control-allow-origin for that domain."""
    headers = {
        "Origin": "https://unauthorized-evil-domain.com",
        "Access-Control-Request-Method": "POST",
    }
    response = client.options("/api/v1/predict", headers=headers)
    allow_origin = response.headers.get("access-control-allow-origin")
    assert allow_origin != "https://unauthorized-evil-domain.com"
