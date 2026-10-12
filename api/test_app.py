from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_prediction_endpoint():
    # Test payload with all 12 required features
    payload = {
        "Conflicting_Files_Count": 2,
        "Author_Match": 1,
        "Lines_Changed_Local": 15,
        "Lines_Changed_Incoming": 5,
        "Total_Lines_Changed": 20,
        "Conflict_Chunk_Count": 2,
        "Avg_Chunk_Size": 10.0,
        "Local_Conflict_Lines": 15,
        "Incoming_Conflict_Lines": 5,
        "Local_Incoming_Ratio": 3.0,
        "Primary_File_Type": 0,
        "Time_Diff_Hours": 24.5
    }
    
    response = client.post("/predict", json=payload)
    
    # Assert successful response and correct format
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert "confidence" in data
    assert data["prediction"] in ["keep_local", "keep_incoming", "combine_both"]
