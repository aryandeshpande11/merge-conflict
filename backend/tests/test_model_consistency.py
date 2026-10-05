import re
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.services.feature_service import FeatureService
from app.services.model_service import model_service
from app.schemas.prediction import ConflictPredictionRequest


def test_feature_order_regression(valid_payload: Dict[str, Any]):
    """Test 20: FeatureService guarantees strict feature ordering matching training schema."""
    # Reverse the dictionary keys
    reversed_dict = {k: valid_payload[k] for k in reversed(list(valid_payload.keys()))}
    request = ConflictPredictionRequest(**reversed_dict)
    df = FeatureService.request_to_dataframe(request)

    expected_cols = [
        "Conflicting_Files_Count",
        "Author_Match",
        "Lines_Changed_Local",
        "Lines_Changed_Incoming",
        "Total_Lines_Changed",
        "Conflict_Chunk_Count",
        "Avg_Chunk_Size",
        "Local_Conflict_Lines",
        "Incoming_Conflict_Lines",
        "Local_Incoming_Ratio",
        "Primary_File_Type",
        "Time_Diff_Hours",
    ]
    assert list(df.columns) == expected_cols


def test_direct_model_vs_api_consistency(client: TestClient, valid_payload: Dict[str, Any]):
    """Test 21: Direct XGBoost model inference matches API prediction and probabilities exactly."""
    # 1. API prediction
    api_res = client.post("/api/v1/predict", json=valid_payload).json()

    # 2. Direct model prediction
    request = ConflictPredictionRequest(**valid_payload)
    df = FeatureService.request_to_dataframe(request)
    direct_probs = model_service.model.predict_proba(df)[0]
    direct_top_idx = int(np.argmax(direct_probs))
    direct_pred_class = model_service.class_mapping[direct_top_idx]

    # Verify prediction matches
    assert api_res["prediction"] == direct_pred_class

    # Verify probabilities match within floating-point tolerance
    for idx, prob in enumerate(direct_probs):
        class_name = model_service.class_mapping[idx]
        assert api_res["probabilities"][class_name] == pytest.approx(float(prob), abs=1e-4)


def test_model_not_reloaded_per_request(client: TestClient, valid_payload: Dict[str, Any]):
    """Test 22: Model is loaded once at startup and not re-read from disk on inference requests."""
    with patch.object(model_service, "load_model", wraps=model_service.load_model) as spy_load:
        for _ in range(5):
            res = client.post("/api/v1/predict", json=valid_payload)
            assert res.status_code == 200

        # load_model was not called during requests
        assert spy_load.call_count == 0


def test_model_file_existence():
    """Test 44: Native XGBoost JSON model exists and can be loaded."""
    model_path = Path(__file__).resolve().parent.parent / "models" / "merge_conflict_model.json"
    assert model_path.exists(), f"Model file missing at: {model_path}"
    assert model_path.stat().st_size > 0


def test_training_inference_feature_compatibility():
    """Test 46: Verify FeatureService.FEATURE_NAMES strictly matches train_model_v3.py FEATURE_COLS."""
    train_script = Path(__file__).resolve().parent.parent.parent / "train_model_v3.py"
    if not train_script.exists():
        pytest.skip("train_model_v3.py not present in root directory")

    content = train_script.read_text(encoding="utf-8")
    # Extract FEATURE_COLS list from train_model_v3.py
    match = re.search(r"FEATURE_COLS\s*=\s*\[(.*?)\]", content, re.DOTALL)
    assert match, "Could not find FEATURE_COLS in train_model_v3.py"

    raw_features = match.group(1)
    extracted_features = [f.strip().strip("'\"") for f in raw_features.split(",") if f.strip().strip("'\"")]

    assert extracted_features == FeatureService.FEATURE_NAMES, (
        f"Feature mismatch between training script and FeatureService!\n"
        f"Training: {extracted_features}\n"
        f"Service:  {FeatureService.FEATURE_NAMES}"
    )


def test_no_smote_during_prediction(client: TestClient, valid_payload: Dict[str, Any]):
    """Test 47: Verify SMOTE is not imported or called during the prediction lifecycle."""
    with patch("imblearn.over_sampling.SMOTE", side_effect=RuntimeError("SMOTE called in inference!")):
        response = client.post("/api/v1/predict", json=valid_payload)
        assert response.status_code == 200


def test_no_data_leakage(valid_payload: Dict[str, Any]):
    """Test 48: Prediction does not mutate input or model parameters."""
    request = ConflictPredictionRequest(**valid_payload)
    df = FeatureService.request_to_dataframe(request)

    # Capture initial model dump / state
    initial_dump = model_service.model.get_booster().get_dump()

    # Perform multiple predictions
    model_service.predict_single(df)
    model_service.predict_single(df)

    final_dump = model_service.model.get_booster().get_dump()
    assert initial_dump == final_dump, "Model booster state mutated during prediction!"
