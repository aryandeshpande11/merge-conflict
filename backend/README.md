# Merge Conflict Resolution Predictor — FastAPI Backend

A production-grade REST API built with **FastAPI**, **Pydantic**, and **XGBoost** that predicts how Git merge conflicts should be resolved (`keep_local`, `keep_incoming`, or `combine_both`) using machine learning features mined from real-world conflict histories.

---

## 1. What the API Does

When developers collaborate using Git, branch divergence frequently results in merge conflicts. Deciding how to resolve a conflict—whether to retain local branch edits, accept incoming branch edits, or combine modifications from both sides—can be tedious and error-prone.

This API serves an **XGBoost multi-class classifier** trained on 529 real-world merge conflicts mined across open-source Java repositories (Dropwizard, JBehave, Zanata, Grails). The API:
- Validates 12 conflict-level, structural, and semantic features using Pydantic.
- Ensures feature ordering matches the XGBoost training schema exactly.
- Returns the predicted resolution strategy (`keep_local`, `keep_incoming`, `combine_both`), genuine prediction confidence (probability of the predicted class), and the full probability distribution from `predict_proba()`.
- Extracts conflict features directly from raw Git conflict text markers (`<<<<<<<`, `=======`, `>>>>>>>`).
- Programmatically replays historical merge commits in local repositories to extract all 12 features in an isolated, secure Git environment.

---

## 2. Technology Stack & Architecture

- **Language & Runtime**: Python 3.12+
- **API Framework**: FastAPI with Starlette
- **Server**: Uvicorn ASGI
- **ML Framework**: XGBoost (`multi:softprob`), scikit-learn, imbalanced-learn (training only)
- **Validation**: Pydantic v2
- **Data Manipulation**: pandas, numpy

```text
                     CLIENT / FRONTEND
                            │
                            ▼
                    ┌───────────────┐
                    │    FastAPI    │
                    └───────┬───────┘
                            │
                 ┌──────────┴──────────┐
                 ▼                     ▼
           Prediction Route       Repository Route
                 │                     │
                 ▼                     ▼
          Feature Service       Git Feature Extraction
                 │                     │
                 └──────────┬──────────┘
                            ▼
                    ┌───────────────┐
                    │ Model Service │
                    └───────┬───────┘
                            ▼
                    ┌───────────────┐
                    │    XGBoost    │
                    │  (JSON Model) │
                    └───────┬───────┘
                            ▼
                  Prediction + Probability
```

---

## 3. Installation & Setup

### Prerequisites
- Python 3.12 or newer
- Git installed on your system path

### 1. Navigate to the backend directory
```bash
cd backend
```

### 2. Create and activate a virtual environment
```bash
# On Linux / macOS:
python3 -m venv venv
source venv/bin/activate

# On Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default configuration:
```env
PORT=8000
HOST=0.0.0.0
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

---

## 4. Running the API

Start the FastAPI application with Uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Once running:
- **Interactive OpenAPI Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 5. Endpoints Reference

### 5.1. Health Check
`GET /health`

Checks service liveness and confirms the ML model is initialized in memory.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_version": "v3"
}
```

If the model file is missing or failed to initialize:
```json
{
  "status": "unhealthy",
  "model_loaded": false,
  "model_version": null
}
```

---

### 5.2. Model Information
`GET /api/v1/model-info`

Returns details about the trained XGBoost model, ordered features, class mappings, and cross-validation metrics.

**Response (200 OK):**
```json
{
  "model": "XGBoost",
  "version": "v3",
  "features": [
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
    "Time_Diff_Hours"
  ],
  "classes": [
    "combine_both",
    "keep_incoming",
    "keep_local"
  ],
  "algorithm": "XGBoost",
  "metrics": {
    "cross_validation_accuracy": "82.34% ± 2.33%",
    "full_dataset_accuracy": "98.49%"
  }
}
```

---

### 5.3. Predict Merge Conflict Resolution
`POST /api/v1/predict`

Calculates resolution probabilities and the optimal resolution strategy for 12 validated input features.

**Request:**
```json
{
  "Conflicting_Files_Count": 2,
  "Author_Match": 0,
  "Lines_Changed_Local": 15,
  "Lines_Changed_Incoming": 10,
  "Total_Lines_Changed": 25,
  "Conflict_Chunk_Count": 3,
  "Avg_Chunk_Size": 8.33,
  "Local_Conflict_Lines": 15,
  "Incoming_Conflict_Lines": 10,
  "Local_Incoming_Ratio": 1.5,
  "Primary_File_Type": 0,
  "Time_Diff_Hours": 24.5
}
```

**Response (200 OK):**
```json
{
  "prediction": "combine_both",
  "confidence": 0.8741,
  "probabilities": {
    "combine_both": 0.8741,
    "keep_incoming": 0.0523,
    "keep_local": 0.0736
  },
  "model_version": "v3"
}
```

**Validation Rules:**
- `Author_Match`: Must be `0` or `1`
- `Primary_File_Type`: Must be `0` (Code), `1` (Config), `2` (Docs), or `3` (Other)
- Count features (`Conflicting_Files_Count`, `Lines_Changed_Local`, etc.): Must be non-negative integers (`>= 0`)
- Ratios and sizes (`Avg_Chunk_Size`, `Local_Incoming_Ratio`, `Time_Diff_Hours`): Must be non-negative floats (`>= 0.0`)
- Invalid or missing parameters automatically return `HTTP 422 Unprocessable Entity`.

---

### 5.4. Analyze Raw Conflict Text
`POST /api/v1/analyze-conflict`

Extracts conflict-level features (`Conflict_Chunk_Count`, `Avg_Chunk_Size`, `Local_Conflict_Lines`, `Incoming_Conflict_Lines`, `Local_Incoming_Ratio`) directly from standard Git conflict markers.

**Request (Text only):**
```json
{
  "conflict_text": "<<<<<<< HEAD\nlogger.info(\"Starting service\");\n=======\nlogger.debug(\"Initializing\");\n>>>>>>> feature/logging",
  "filename": "Service.java"
}
```

**Response (200 OK):**
```json
{
  "conflict_features": {
    "Conflict_Chunk_Count": 1,
    "Avg_Chunk_Size": 2.0,
    "Local_Conflict_Lines": 1,
    "Incoming_Conflict_Lines": 1,
    "Local_Incoming_Ratio": 1.0
  },
  "missing_contextual_features": [
    "Conflicting_Files_Count",
    "Author_Match",
    "Lines_Changed_Local",
    "Lines_Changed_Incoming",
    "Total_Lines_Changed",
    "Time_Diff_Hours"
  ],
  "note": "Conflict-level features extracted successfully. Note that the 7 contextual features cannot be inferred from conflict text alone and must be supplied from Git metadata to compute an ML prediction.",
  "inferred_file_type": 0,
  "prediction": null
}
```

*Note: If contextual features are supplied in the request body, the endpoint will also return the ML prediction.*

---

### 5.5. Analyze Local Git Repository
`POST /api/v1/analyze-repository`

Replays a historical merge commit programmatically in a local Git repository:
1. Validates repository path and commit hash (rejecting unsafe shell sequences).
2. Identifies parents (`p1`, `p2`) and the common ancestor (`merge-base`).
3. Checks out `p1` and initiates `git merge --no-commit --no-ff p2`.
4. Inspects conflicting files and extracts all 12 ML features.
5. Reliably aborts the merge and restores the repository's original HEAD.
6. Returns the 12 features and predicted resolution strategy.

**Request:**
```json
{
  "repository_path": "/path/to/local/git/repo",
  "merge_commit": "8bcd6953e92162475dc56be97786fcd8485b996e"
}
```

**Response (200 OK):**
```json
{
  "repository_path": "/path/to/local/git/repo",
  "merge_commit": "8bcd6953e92162475dc56be97786fcd8485b996e",
  "features": {
    "Conflicting_Files_Count": 2,
    "Author_Match": 0,
    "Lines_Changed_Local": 43,
    "Lines_Changed_Incoming": 20,
    "Total_Lines_Changed": 63,
    "Conflict_Chunk_Count": 2,
    "Avg_Chunk_Size": 8.0,
    "Local_Conflict_Lines": 9,
    "Incoming_Conflict_Lines": 7,
    "Local_Incoming_Ratio": 1.2857,
    "Primary_File_Type": 0,
    "Time_Diff_Hours": 2.17
  },
  "prediction": {
    "prediction": "keep_local",
    "confidence": 0.8124,
    "probabilities": {
      "combine_both": 0.1235,
      "keep_incoming": 0.0641,
      "keep_local": 0.8124
    },
    "model_version": "v3"
  }
}
```

---

## 6. How the Model Is Loaded

The model is persisted using native XGBoost serialization format:
```text
backend/models/merge_conflict_model.json
```
Metadata detailing the feature schema, class mappings, and evaluation metrics is saved in:
```text
backend/models/model_metadata.json
```

### Lifespan Initialization
The FastAPI application uses FastAPI's `lifespan` context manager (`app/main.py`). The `ModelService` loads the model **exactly once** during process startup:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    model_service.load_model()
    yield
```
Requests never trigger re-training or redundant disk reads.

---

## 7. Why SMOTE Is NOT Used During Prediction

### What SMOTE Does
SMOTE (**Synthetic Minority Oversampling Technique**) synthesizes artificial data points along line segments joining nearest neighbors in minority classes (`keep_incoming` in our training data had only 12 instances vs 304 for `combine_both`).

### Why SMOTE is Training-Only:
1. **SMOTE is an oversampling algorithm, not a transformer**: It does not transform, normalize, or scale feature dimensions.
2. **Data Leakage & Invariance**: Applying SMOTE during inference would distort single input vectors and violate inference independence.
3. **Inference Pipeline**:
```text
Request (12 features) → Pydantic Validation → DataFrame → model.predict_proba() → Response
```

---

## 8. Feature Definitions & Zero-Division Safety

| Feature | Meaning | Calculation / Note |
|---|---|---|
| `Conflicting_Files_Count` | Number of files with conflicts | Count of files in `git diff --diff-filter=U` |
| `Author_Match` | Both commits authored by same developer | `1` if author emails match, else `0` |
| `Lines_Changed_Local` | Lines changed in local branch | `git diff --shortstat base p1` |
| `Lines_Changed_Incoming` | Lines changed in incoming branch | `git diff --shortstat base p2` |
| `Total_Lines_Changed` | Total lines changed across branches | `Lines_Changed_Local + Lines_Changed_Incoming` |
| `Conflict_Chunk_Count` | Number of conflict blocks | Count of `<<<<<<<` markers |
| `Avg_Chunk_Size` | Average lines per conflict block | `(local_lines + incoming_lines) / max(chunks, 1)` |
| `Local_Conflict_Lines` | Total lines inside local sides | Lines between `<<<<<<<` and `=======` |
| `Incoming_Conflict_Lines` | Total lines inside incoming sides | Lines between `=======` and `>>>>>>>` |
| `Local_Incoming_Ratio` | Ratio of local vs incoming conflict lines | `local_lines / max(incoming_lines, 1)` |
| `Primary_File_Type` | Semantic classification of first file | `0`=Code, `1`=Config, `2`=Docs, `3`=Other |
| `Time_Diff_Hours` | Time between parent commits | Commit timestamp delta in hours |

**Safe Division:**
For `Local_Incoming_Ratio` and `Avg_Chunk_Size`, division by zero is safely guarded by `max(incoming_lines, 1)` and `max(total_chunks, 1)`, identical to the training data-mining implementation.

---

## 9. Security & Command Injection Prevention

The repository analysis endpoint (`/api/v1/analyze-repository`) interacts with local Git repositories. To prevent command injection and unauthorized execution:
1. **Never use `shell=True` or `os.system`**: All git invocations pass explicit argument arrays (`["git", "checkout", ...]`) directly to `subprocess.run()`.
2. **Path Sanitization**: `repository_path` must exist, be a directory, and confirm `git rev-parse --is-inside-work-tree == true`.
3. **Git Reference Whitelist**: `merge_commit` is strictly validated using regex `^[a-zA-Z0-9_\-\./~^]{2,64}$` and disallowed from starting with hyphens (`-`).
4. **Isolated Worktrees**: Temporary merge replays are wrapped in `try ... finally` blocks to ensure `git merge --abort` and `git checkout -f <original_head>` always execute.

---

## 10. Automated Testing

The backend includes a comprehensive test suite covering health endpoints, prediction validation, edge cases, model failure states, conflict text parsing, and end-to-end repository replay with temporary Git repositories.

Run tests from the root or `backend` folder:
```bash
python -m pytest
```

Run with verbose output and coverage:
```bash
python -m pytest -v
```

---

## 11. Docker Deployment

### 1. Build the Docker image
```bash
docker build -t merge-conflict-api .
```

### 2. Run the Docker container
```bash
docker run -d -p 8000:8000 --name merge-conflict-service merge-conflict-api
```

### 3. Verify container health
```bash
curl http://localhost:8000/health
```
