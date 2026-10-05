from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient

from app.services.model_service import model_service


def test_predict_happy_path(client: TestClient, valid_payload: Dict[str, Any]):
    """Test 8: Prediction endpoint happy path with 12 valid features."""
    response = client.post("/api/v1/predict", json=valid_payload)
    assert response.status_code == 200
    data = response.json()

    assert "prediction" in data
    assert "confidence" in data
    assert "probabilities" in data
    assert "model_version" in data

    valid_classes = {"combine_both", "keep_incoming", "keep_local"}
    assert data["prediction"] in valid_classes
    assert data["model_version"] == "v3"


def test_predict_probability_consistency(client: TestClient, valid_payload: Dict[str, Any]):
    """Test 9: Probabilities sum to 1.0 and each is between 0 and 1."""
    response = client.post("/api/v1/predict", json=valid_payload)
    assert response.status_code == 200
    data = response.json()
    probs = data["probabilities"]

    assert set(probs.keys()) == {"combine_both", "keep_incoming", "keep_local"}
    for p in probs.values():
        assert 0.0 <= p <= 1.0

    # Probabilities must sum approximately to 1.0
    assert sum(probs.values()) == pytest.approx(1.0, abs=1e-2)


def test_predict_confidence_consistency(client: TestClient, valid_payload: Dict[str, Any]):
    """Test 10: Confidence equals the probability of the predicted class."""
    response = client.post("/api/v1/predict", json=valid_payload)
    assert response.status_code == 200
    data = response.json()

    predicted_class = data["prediction"]
    confidence = data["confidence"]
    class_prob = data["probabilities"][predicted_class]

    assert confidence == pytest.approx(class_prob, abs=1e-4)


def test_predict_highest_probability(client: TestClient, valid_payload: Dict[str, Any]):
    """Test 11: Prediction corresponds to the class having the highest probability."""
    response = client.post("/api/v1/predict", json=valid_payload)
    assert response.status_code == 200
    data = response.json()

    probs = data["probabilities"]
    expected_top_class = max(probs, key=probs.get)
    assert data["prediction"] == expected_top_class


def test_predict_model_failure(client: TestClient, valid_payload: Dict[str, Any]):
    """Test: When model is not loaded, endpoint returns 503."""
    original_state = model_service.is_loaded
    try:
        model_service.is_loaded = False
        response = client.post("/api/v1/predict", json=valid_payload)
        assert response.status_code == 503
        assert "not ready" in response.json()["detail"].lower()
    finally:
        model_service.is_loaded = original_state


def test_predict_determinism(client: TestClient, valid_payload: Dict[str, Any]):
    """Test 38: Sending the exact same payload multiple times returns identical results."""
    responses = [client.post("/api/v1/predict", json=valid_payload).json() for _ in range(5)]
    first_pred = responses[0]["prediction"]
    first_conf = responses[0]["confidence"]
    first_probs = responses[0]["probabilities"]

    for r in responses[1:]:
        assert r["prediction"] == first_pred
        assert r["confidence"] == pytest.approx(first_conf, abs=1e-5)
        for k, v in first_probs.items():
            assert r["probabilities"][k] == pytest.approx(v, abs=1e-5)


def test_predict_concurrency(client: TestClient, valid_payload: Dict[str, Any]):
    """Test 37: Concurrent prediction requests maintain deterministic state without corruption."""
    def send_request(_):
        res = client.post("/api/v1/predict", json=valid_payload)
        assert res.status_code == 200
        return res.json()

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(send_request, range(20)))

    assert len(results) == 20
    first = results[0]
    for r in results[1:]:
        assert r["prediction"] == first["prediction"]
        assert r["confidence"] == pytest.approx(first["confidence"], abs=1e-5)
