from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pickle
import pandas as pd
import os
from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Merge Conflict Predictor API")

# Expose Prometheus /metrics endpoint (tracks latency and http requests)
Instrumentator().instrument(app).expose(app)

# Custom counter for prediction requests matching CIE PDF rubric
PREDICTION_REQUESTS = Counter(
    "prediction_requests_total",
    "Total count of prediction requests",
    ["prediction"]
)

# Load the V3 model on startup (supports both root and model/ directory)
model_path = 'xgboost_merge_model_v3.pkl' if os.path.exists('xgboost_merge_model_v3.pkl') else 'model/model.pkl'
try:
    with open(model_path, 'rb') as f:
        data = pickle.load(f)
        model = data['model']
        encoder = data['encoder']
        features = data['features']
except Exception as e:
    print(f"Error loading model from {model_path}: {e}")
    model, encoder, features = None, None, None

# Define the expected input payload using Pydantic (12 features)
class ConflictData(BaseModel):
    Conflicting_Files_Count: int
    Author_Match: int
    Lines_Changed_Local: int
    Lines_Changed_Incoming: int
    Total_Lines_Changed: int
    Conflict_Chunk_Count: int
    Avg_Chunk_Size: float
    Local_Conflict_Lines: int
    Incoming_Conflict_Lines: int
    Local_Incoming_Ratio: float
    Primary_File_Type: int
    Time_Diff_Hours: float

@app.get("/health")
def health_check():
    """Endpoint for Kubernetes readiness/liveness probes and Prometheus API Health panel"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "healthy"}

@app.post("/predict")
def predict_resolution(data: ConflictData):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
        
    # Convert input to DataFrame (ensuring order matches training)
    input_df = pd.DataFrame([data.model_dump()])[features]
    
    # Predict probabilities and final class
    probabilities = model.predict_proba(input_df)[0]
    pred_idx = model.predict(input_df)[0]
    
    prediction = encoder.inverse_transform([pred_idx])[0]
    
    # Increment Prometheus metric
    PREDICTION_REQUESTS.labels(prediction=str(prediction)).inc()
    
    # Optional: Log the request to standard out so Prometheus/Grafana can track it
    print(f"Prediction made: {prediction}")
    
    return {
        "prediction": prediction,
        "confidence": float(max(probabilities))
    }
