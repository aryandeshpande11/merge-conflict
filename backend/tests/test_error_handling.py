from fastapi.testclient import TestClient
from app.services.model_service import model_service


def test_invalid_json_syntax(client: TestClient):
    """Test 40: Malformed JSON syntax returns clean 400 or 422 without server tracebacks."""
    headers = {"Content-Type": "application/json"}
    bad_json = '{"Conflicting_Files_Count": 2, '  # Truncated
    response = client.post("/api/v1/predict", content=bad_json, headers=headers)
    assert response.status_code in {400, 422}
    assert "traceback" not in response.text.lower()


def test_no_stack_trace_leakage_on_error(client: TestClient):
    """Test 41: Error responses do not leak internal stack traces or Python file paths."""
    # 1. Invalid commit
    res_repo = client.post(
        "/api/v1/analyze-repository",
        json={"repository_path": "/invalid", "merge_commit": "abc; rm -rf"},
    )
    assert "traceback" not in res_repo.text.lower()
    assert ".py" not in res_repo.text

    # 2. Invalid prediction input
    res_pred = client.post("/api/v1/predict", json={"Author_Match": "invalid_type"})
    assert "traceback" not in res_pred.text.lower()
    assert ".py" not in res_pred.text


def test_no_secret_or_env_leakage(client: TestClient):
    """Test 41: Error responses do not expose environment variables or secret keys."""
    res = client.post("/api/v1/predict", json={})
    assert res.status_code == 422
    body = res.text
    forbidden_tokens = ["ALLOWED_ORIGINS", "SECRET", "PRIVATE_KEY", "AWS_", "PASSWORD"]
    for token in forbidden_tokens:
        assert token not in body
