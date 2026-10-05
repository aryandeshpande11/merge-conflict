import json
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient


def test_zero_boundary(client: TestClient):
    """Test 12: Zero-boundary values are accepted and produce valid inference without crash/NaN."""
    zero_payload = {
        "Conflicting_Files_Count": 0,
        "Author_Match": 0,
        "Lines_Changed_Local": 0,
        "Lines_Changed_Incoming": 0,
        "Total_Lines_Changed": 0,
        "Conflict_Chunk_Count": 0,
        "Avg_Chunk_Size": 0.0,
        "Local_Conflict_Lines": 0,
        "Incoming_Conflict_Lines": 0,
        "Local_Incoming_Ratio": 0.0,
        "Primary_File_Type": 0,
        "Time_Diff_Hours": 0.0,
    }
    response = client.post("/api/v1/predict", json=zero_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] in {"combine_both", "keep_incoming", "keep_local"}
    for p in data["probabilities"].values():
        assert not (p != p)  # Not NaN


def test_extreme_values(client: TestClient):
    """Test 13: Extremely large values do not crash or expose tracebacks."""
    extreme_payload = {
        "Conflicting_Files_Count": 100000,
        "Author_Match": 1,
        "Lines_Changed_Local": 1000000,
        "Lines_Changed_Incoming": 1000000,
        "Total_Lines_Changed": 2000000,
        "Conflict_Chunk_Count": 100000,
        "Avg_Chunk_Size": 100000.0,
        "Local_Conflict_Lines": 500000,
        "Incoming_Conflict_Lines": 500000,
        "Local_Incoming_Ratio": 100.0,
        "Primary_File_Type": 3,
        "Time_Diff_Hours": 1000000.0,
    }
    response = client.post("/api/v1/predict", json=extreme_payload)
    assert response.status_code in {200, 422}
    if response.status_code == 200:
        data = response.json()
        assert data["prediction"] in {"combine_both", "keep_incoming", "keep_local"}


@pytest.mark.parametrize(
    "field",
    [
        "Conflicting_Files_Count",
        "Lines_Changed_Local",
        "Lines_Changed_Incoming",
        "Total_Lines_Changed",
        "Conflict_Chunk_Count",
        "Avg_Chunk_Size",
        "Local_Conflict_Lines",
        "Incoming_Conflict_Lines",
        "Local_Incoming_Ratio",
        "Time_Diff_Hours",
    ],
)
def test_negative_values(client: TestClient, valid_payload: Dict[str, Any], field: str):
    """Test 14: Negative values are rejected with 422 for each non-negative field."""
    bad_payload = valid_payload.copy()
    bad_payload[field] = -1 if "Count" in field or "Lines" in field else -1.5
    response = client.post("/api/v1/predict", json=bad_payload)
    assert response.status_code == 422


@pytest.mark.parametrize("val, expected_status", [(0, 200), (1, 200), (-1, 422), (2, 422), (10, 422)])
def test_author_match_enumeration(client: TestClient, valid_payload: Dict[str, Any], val: int, expected_status: int):
    """Test 15: Author_Match only accepts 0 or 1."""
    payload = valid_payload.copy()
    payload["Author_Match"] = val
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "val, expected_status",
    [(0, 200), (1, 200), (2, 200), (3, 200), (-1, 422), (4, 422), (99, 422)],
)
def test_primary_file_type_enumeration(
    client: TestClient, valid_payload: Dict[str, Any], val: int, expected_status: int
):
    """Test 15: Primary_File_Type only accepts 0, 1, 2, 3."""
    payload = valid_payload.copy()
    payload["Primary_File_Type"] = val
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "field",
    [
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
    ],
)
def test_missing_fields(client: TestClient, valid_payload: Dict[str, Any], field: str):
    """Test 16: Omitting any of the 12 features returns 422."""
    incomplete = valid_payload.copy()
    del incomplete[field]
    response = client.post("/api/v1/predict", json=incomplete)
    assert response.status_code == 422


def test_extra_fields(client: TestClient, valid_payload: Dict[str, Any]):
    """Test 17: Extra fields are safely ignored by Pydantic default schema configuration."""
    extra_payload = valid_payload.copy()
    extra_payload["unexpected_field"] = "random_value_123"
    response = client.post("/api/v1/predict", json=extra_payload)
    assert response.status_code == 200


@pytest.mark.parametrize("bad_val", ["abc", None, [], {}])
def test_wrong_data_types(client: TestClient, valid_payload: Dict[str, Any], bad_val: Any):
    """Test 18: Non-numeric data types return 422 Unprocessable Entity."""
    bad_payload = valid_payload.copy()
    bad_payload["Avg_Chunk_Size"] = bad_val
    response = client.post("/api/v1/predict", json=bad_payload)
    assert response.status_code == 422


def test_nan_infinity_values(client: TestClient, valid_payload: Dict[str, Any]):
    """Test 19: NaN and Infinity values in request payload are rejected cleanly (no 500 crash)."""
    headers = {"Content-Type": "application/json"}

    # NaN
    nan_json = json.dumps(valid_payload).replace('"Avg_Chunk_Size": 8.33', '"Avg_Chunk_Size": NaN')
    resp_nan = client.post("/api/v1/predict", content=nan_json, headers=headers)
    assert resp_nan.status_code in {400, 422}, f"NaN should be rejected cleanly, got {resp_nan.status_code}"

    # Infinity
    inf_json = json.dumps(valid_payload).replace('"Avg_Chunk_Size": 8.33', '"Avg_Chunk_Size": Infinity')
    resp_inf = client.post("/api/v1/predict", content=inf_json, headers=headers)
    assert resp_inf.status_code in {400, 422}, f"Infinity should be rejected cleanly, got {resp_inf.status_code}"

    # -Infinity
    neg_inf_json = json.dumps(valid_payload).replace('"Avg_Chunk_Size": 8.33', '"Avg_Chunk_Size": -Infinity')
    resp_neg_inf = client.post("/api/v1/predict", content=neg_inf_json, headers=headers)
    assert resp_neg_inf.status_code in {400, 422}, f"-Infinity should be rejected cleanly, got {resp_neg_inf.status_code}"

