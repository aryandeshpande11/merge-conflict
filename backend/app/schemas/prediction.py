from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ConflictPredictionRequest(BaseModel):
    Conflicting_Files_Count: int = Field(
        ...,
        ge=0,
        description="Number of files involved in the conflict",
        json_schema_extra={"example": 2}
    )
    Author_Match: int = Field(
        ...,
        ge=0,
        le=1,
        description="1 if both parents were authored by the same developer, otherwise 0",
        json_schema_extra={"example": 0}
    )
    Lines_Changed_Local: int = Field(
        ...,
        ge=0,
        description="Lines changed in local branch compared with common ancestor",
        json_schema_extra={"example": 15}
    )
    Lines_Changed_Incoming: int = Field(
        ...,
        ge=0,
        description="Lines changed in incoming branch compared with common ancestor",
        json_schema_extra={"example": 10}
    )
    Total_Lines_Changed: int = Field(
        ...,
        ge=0,
        description="Total lines changed (local + incoming changes)",
        json_schema_extra={"example": 25}
    )
    Conflict_Chunk_Count: int = Field(
        ...,
        ge=0,
        description="Number of conflict marker blocks",
        json_schema_extra={"example": 3}
    )
    Avg_Chunk_Size: float = Field(
        ...,
        ge=0.0,
        allow_inf_nan=False,
        description="Average size of conflict chunks in lines",
        json_schema_extra={"example": 8.33}
    )
    Local_Conflict_Lines: int = Field(
        ...,
        ge=0,
        description="Number of lines on local side of conflict",
        json_schema_extra={"example": 15}
    )
    Incoming_Conflict_Lines: int = Field(
        ...,
        ge=0,
        description="Number of lines on incoming side of conflict",
        json_schema_extra={"example": 10}
    )
    Local_Incoming_Ratio: float = Field(
        ...,
        ge=0.0,
        allow_inf_nan=False,
        description="Ratio of local conflict lines to incoming conflict lines",
        json_schema_extra={"example": 1.5}
    )
    Primary_File_Type: int = Field(
        ...,
        ge=0,
        le=3,
        description="0: Code, 1: Config, 2: Docs, 3: Other",
        json_schema_extra={"example": 0}
    )
    Time_Diff_Hours: float = Field(
        ...,
        ge=0.0,
        allow_inf_nan=False,
        description="Time difference between parent commits in hours",
        json_schema_extra={"example": 24.5}
    )

    model_config = {
        "allow_inf_nan": False,
        "json_schema_extra": {
            "example": {
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
        }
    }


class PredictionResponse(BaseModel):
    prediction: str = Field(..., description="Predicted resolution strategy (keep_local, keep_incoming, combine_both)")
    confidence: float = Field(..., description="Probability of the predicted class")
    probabilities: Dict[str, float] = Field(..., description="Probability distribution across all resolution classes")
    model_version: str = Field("v3", description="Model version used for prediction")

    model_config = {
        "json_schema_extra": {
            "example": {
                "prediction": "combine_both",
                "confidence": 0.87,
                "probabilities": {
                    "keep_local": 0.05,
                    "keep_incoming": 0.08,
                    "combine_both": 0.87
                },
                "model_version": "v3"
            }
        }
    }


class ModelInfoResponse(BaseModel):
    model: str
    version: str
    features: List[str]
    classes: List[str]
    algorithm: str
    metrics: Optional[Dict[str, object]] = None


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: Optional[str] = None


class RawConflictAnalysisRequest(BaseModel):
    conflict_text: str = Field(
        ...,
        description="Raw conflict text containing Git conflict markers (<<<<<<<, =======, >>>>>>>)",
        json_schema_extra={
            "example": "<<<<<<< HEAD\nlocal code line 1\nlocal code line 2\n=======\nincoming code line 1\n>>>>>>> feature"
        }
    )
    filename: Optional[str] = Field(
        None,
        description="Optional filename to infer Primary_File_Type (e.g. Service.java, config.yaml)"
    )
    # Optional contextual features if user wants full prediction
    Conflicting_Files_Count: Optional[int] = Field(None, ge=0)
    Author_Match: Optional[int] = Field(None, ge=0, le=1)
    Lines_Changed_Local: Optional[int] = Field(None, ge=0)
    Lines_Changed_Incoming: Optional[int] = Field(None, ge=0)
    Total_Lines_Changed: Optional[int] = Field(None, ge=0)
    Primary_File_Type: Optional[int] = Field(None, ge=0, le=3)
    Time_Diff_Hours: Optional[float] = Field(None, ge=0.0, allow_inf_nan=False)

    model_config = {
        "allow_inf_nan": False
    }


class ConflictFeatures(BaseModel):
    Conflict_Chunk_Count: int
    Avg_Chunk_Size: float
    Local_Conflict_Lines: int
    Incoming_Conflict_Lines: int
    Local_Incoming_Ratio: float


class RawConflictAnalysisResponse(BaseModel):
    conflict_features: ConflictFeatures
    missing_contextual_features: List[str]
    note: str
    inferred_file_type: Optional[int] = None
    prediction: Optional[PredictionResponse] = None


class RepositoryAnalysisRequest(BaseModel):
    repository_path: str = Field(
        ...,
        description="Absolute or relative path to a local Git repository",
        json_schema_extra={"example": "/path/to/repository"}
    )
    merge_commit: str = Field(
        ...,
        description="Commit hash or revision of the merge commit to analyze",
        json_schema_extra={"example": "abc1234"}
    )


class RepositoryAnalysisResponse(BaseModel):
    repository_path: str
    merge_commit: str
    features: Dict[str, object]
    prediction: PredictionResponse
