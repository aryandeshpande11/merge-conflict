import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.services.feature_service import FeatureService


def test_model_info_endpoint(client: TestClient):
    """Test model-info endpoint returns 200 with complete model metadata."""
    response = client.get("/api/v1/model-info")
    assert response.status_code == 200
    data = response.json()

    assert data["model"] == "XGBoost"
    assert data["version"] == "v3"
    assert data["algorithm"] == "XGBoost"

    # Exactly 12 features
    assert len(data["features"]) == 12
    # No duplicate feature names
    assert len(data["features"]) == len(set(data["features"]))
    # Matches FeatureService order exactly
    assert data["features"] == FeatureService.get_feature_names()

    # Verified classes matching LabelEncoder
    expected_classes = ["combine_both", "keep_incoming", "keep_local"]
    assert data["classes"] == expected_classes


def test_model_metadata_file_consistency():
    """Verify backend/models/model_metadata.json matches expected schema."""
    metadata_path = Path(__file__).resolve().parent.parent / "models" / "model_metadata.json"
    assert metadata_path.exists(), f"Metadata file missing at {metadata_path}"

    with open(metadata_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["model"] == "XGBoost"
    assert meta["version"] == "v3"
    assert len(meta["features"]) == 12
    assert meta["features"] == FeatureService.get_feature_names()
    assert meta["classes"] == ["combine_both", "keep_incoming", "keep_local"]
    assert "metrics" in meta
    assert "cross_validation_accuracy" in meta["metrics"]
    assert "full_dataset_accuracy" in meta["metrics"]
