from fastapi.testclient import TestClient

from app.services.feature_service import FeatureService


def test_standard_conflict_text(client: TestClient):
    """Test 23: Standard conflict parsing extracts correct chunk, line, and ratio metrics."""
    conflict_text = (
        "<<<<<<< HEAD\n"
        "local code\n"
        "=======\n"
        "incoming code\n"
        ">>>>>>> feature"
    )
    response = client.post("/api/v1/analyze-conflict", json={"conflict_text": conflict_text})
    assert response.status_code == 200
    feats = response.json()["conflict_features"]

    assert feats["Conflict_Chunk_Count"] == 1
    assert feats["Local_Conflict_Lines"] == 1
    assert feats["Incoming_Conflict_Lines"] == 1
    assert feats["Local_Incoming_Ratio"] == 1.0


def test_multiple_conflict_chunks(client: TestClient):
    """Test 24: Multiple distinct conflict blocks are correctly identified and aggregated."""
    conflict_text = (
        "<<<<<<< HEAD\n"
        "local 1\n"
        "=======\n"
        "incoming 1\n"
        ">>>>>>> branch\n"
        "\n"
        "normal code\n"
        "\n"
        "<<<<<<< HEAD\n"
        "local 2\n"
        "local 3\n"
        "=======\n"
        "incoming 2\n"
        ">>>>>>> branch"
    )
    response = client.post("/api/v1/analyze-conflict", json={"conflict_text": conflict_text})
    assert response.status_code == 200
    feats = response.json()["conflict_features"]

    assert feats["Conflict_Chunk_Count"] == 2
    assert feats["Local_Conflict_Lines"] == 3
    assert feats["Incoming_Conflict_Lines"] == 2
    assert feats["Avg_Chunk_Size"] == 2.5
    assert feats["Local_Incoming_Ratio"] == 1.5


def test_empty_conflict_sides(client: TestClient):
    """Test 25: Empty conflict sides on local or incoming branch do not crash."""
    text_empty_local = "<<<<<<< HEAD\n=======\nincoming\n>>>>>>> branch"
    res1 = client.post("/api/v1/analyze-conflict", json={"conflict_text": text_empty_local})
    assert res1.status_code == 200
    f1 = res1.json()["conflict_features"]
    assert f1["Local_Conflict_Lines"] == 0
    assert f1["Incoming_Conflict_Lines"] == 1
    assert f1["Local_Incoming_Ratio"] == 0.0

    text_empty_incoming = "<<<<<<< HEAD\nlocal\n=======\n>>>>>>> branch"
    res2 = client.post("/api/v1/analyze-conflict", json={"conflict_text": text_empty_incoming})
    assert res2.status_code == 200
    f2 = res2.json()["conflict_features"]
    assert f2["Local_Conflict_Lines"] == 1
    assert f2["Incoming_Conflict_Lines"] == 0
    # Safe division: 1 / max(0, 1) == 1.0
    assert f2["Local_Incoming_Ratio"] == 1.0


def test_division_by_zero_safety(client: TestClient):
    """Test 26: Conflict text with zero incoming lines or zero chunks does not trigger ZeroDivisionError."""
    # Zero incoming lines
    stats = FeatureService.parse_conflict_text("<<<<<<< HEAD\nline\n=======\n>>>>>>> branch")
    assert stats.Local_Incoming_Ratio == 1.0

    # Zero chunks total
    stats_empty = FeatureService.parse_conflict_text("No conflict markers at all.")
    assert stats_empty.Conflict_Chunk_Count == 0
    assert stats_empty.Avg_Chunk_Size == 0.0
    assert stats_empty.Local_Incoming_Ratio == 0.0


def test_malformed_conflict_markers(client: TestClient):
    """Test 27: Malformed or partial conflict markers are parsed safely without crashing."""
    malformed_cases = [
        "<<<<<<<",
        "=======",
        ">>>>>>>",
        "<<<<<<< HEAD\nlocal code with no end",
        "Just a plain text file without markers",
    ]
    for text in malformed_cases:
        response = client.post("/api/v1/analyze-conflict", json={"conflict_text": text})
        assert response.status_code == 200
        data = response.json()
        assert "conflict_features" in data
        assert data["conflict_features"]["Conflict_Chunk_Count"] >= 0


def test_very_large_conflict_text(client: TestClient):
    """Test 28: Very large conflict text (thousands of lines) is parsed efficiently."""
    lines = ["<<<<<<< HEAD"]
    lines.extend([f"local_line_{i}" for i in range(2500)])
    lines.append("=======")
    lines.extend([f"incoming_line_{i}" for i in range(2500)])
    lines.append(">>>>>>> branch")
    large_text = "\n".join(lines)

    response = client.post("/api/v1/analyze-conflict", json={"conflict_text": large_text})
    assert response.status_code == 200
    feats = response.json()["conflict_features"]
    assert feats["Conflict_Chunk_Count"] == 1
    assert feats["Local_Conflict_Lines"] == 2500
    assert feats["Incoming_Conflict_Lines"] == 2500
    assert feats["Local_Incoming_Ratio"] == 1.0


def test_file_type_inference():
    """Test 29: Primary_File_Type classifies extensions into 0=Code, 1=Config, 2=Docs, 3=Other."""
    assert FeatureService.get_file_type("Example.java") == 0
    assert FeatureService.get_file_type("config.yaml") == 1
    assert FeatureService.get_file_type("application.yml") == 1
    assert FeatureService.get_file_type("README.md") == 2
    assert FeatureService.get_file_type("Dockerfile") == 3
    assert FeatureService.get_file_type("package.json") == 1
    assert FeatureService.get_file_type("unknown.xyz") == 3


def test_analyze_conflict_with_full_context(client: TestClient, sample_conflict_text: str):
    """Test analyze-conflict produces prediction when contextual features are provided."""
    payload = {
        "conflict_text": sample_conflict_text,
        "filename": "Service.java",
        "Conflicting_Files_Count": 1,
        "Author_Match": 1,
        "Lines_Changed_Local": 5,
        "Lines_Changed_Incoming": 5,
        "Total_Lines_Changed": 10,
        "Time_Diff_Hours": 1.5,
    }
    response = client.post("/api/v1/analyze-conflict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] is not None
    assert data["prediction"]["prediction"] in {"combine_both", "keep_incoming", "keep_local"}
