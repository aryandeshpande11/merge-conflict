from fastapi import APIRouter, HTTPException, status
import pandas as pd

from app.schemas.prediction import (
    ConflictPredictionRequest,
    PredictionResponse,
    ModelInfoResponse,
    RawConflictAnalysisRequest,
    RawConflictAnalysisResponse,
)
from app.services.model_service import model_service
from app.services.feature_service import FeatureService

router = APIRouter(prefix="/api/v1", tags=["Prediction"])


@router.get("/model-info", response_model=ModelInfoResponse)
def get_model_info():
    """
    Returns model metadata including algorithm, version, features, and classes.
    """
    return model_service.get_model_info()


@router.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Predict merge conflict resolution strategy",
    description="Accepts 12 Git merge conflict features and predicts whether to keep_local, keep_incoming, or combine_both.",
)
def predict_conflict(request: ConflictPredictionRequest):
    """
    Validates the 12 features, converts to DataFrame with strict ordering,
    and runs XGBoost inference.
    """
    if not model_service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model is not ready for inference: {model_service.load_error or 'Model not loaded'}",
        )

    try:
        features_df = FeatureService.request_to_dataframe(request)
        return model_service.predict_single(features_df)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error: {str(e)}",
        )


@router.post(
    "/analyze-conflict",
    response_model=RawConflictAnalysisResponse,
    summary="Extract conflict-level features from raw conflict text",
    description="Parses Git conflict markers (<<<<<<< ======= >>>>>>>) from raw text. "
                "Can optionally execute prediction if contextual repository features are supplied.",
)
def analyze_conflict_text(request: RawConflictAnalysisRequest):
    """
    Parses conflict markers to extract:
    - Conflict_Chunk_Count
    - Avg_Chunk_Size
    - Local_Conflict_Lines
    - Incoming_Conflict_Lines
    - Local_Incoming_Ratio
    """
    conflict_stats = FeatureService.parse_conflict_text(request.conflict_text)

    # Inferred file type if filename provided
    inferred_type = None
    if request.filename:
        inferred_type = FeatureService.get_file_type(request.filename)

    # Check contextual features
    primary_file_type = request.Primary_File_Type if request.Primary_File_Type is not None else inferred_type

    contextual = {
        "Conflicting_Files_Count": request.Conflicting_Files_Count,
        "Author_Match": request.Author_Match,
        "Lines_Changed_Local": request.Lines_Changed_Local,
        "Lines_Changed_Incoming": request.Lines_Changed_Incoming,
        "Total_Lines_Changed": request.Total_Lines_Changed,
        "Primary_File_Type": primary_file_type,
        "Time_Diff_Hours": request.Time_Diff_Hours,
    }

    missing = [k for k, v in contextual.items() if v is None]

    prediction_result = None
    if not missing and model_service.is_loaded:
        # All 12 features are available
        all_features = {
            "Conflicting_Files_Count": request.Conflicting_Files_Count,
            "Author_Match": request.Author_Match,
            "Lines_Changed_Local": request.Lines_Changed_Local,
            "Lines_Changed_Incoming": request.Lines_Changed_Incoming,
            "Total_Lines_Changed": request.Total_Lines_Changed,
            "Conflict_Chunk_Count": conflict_stats.Conflict_Chunk_Count,
            "Avg_Chunk_Size": conflict_stats.Avg_Chunk_Size,
            "Local_Conflict_Lines": conflict_stats.Local_Conflict_Lines,
            "Incoming_Conflict_Lines": conflict_stats.Incoming_Conflict_Lines,
            "Local_Incoming_Ratio": conflict_stats.Local_Incoming_Ratio,
            "Primary_File_Type": primary_file_type,
            "Time_Diff_Hours": request.Time_Diff_Hours,
        }
        df = FeatureService.dict_to_dataframe(all_features)
        prediction_result = model_service.predict_single(df)

    note = (
        "Conflict-level features extracted successfully. Note that the 7 contextual features "
        "(Conflicting_Files_Count, Author_Match, Lines_Changed_Local, Lines_Changed_Incoming, "
        "Total_Lines_Changed, Primary_File_Type, Time_Diff_Hours) cannot be inferred from conflict "
        "text alone and must be supplied from Git metadata to compute an ML prediction."
        if missing else
        "All features present; prediction generated."
    )

    return RawConflictAnalysisResponse(
        conflict_features=conflict_stats,
        missing_contextual_features=missing,
        note=note,
        inferred_file_type=inferred_type,
        prediction=prediction_result,
    )
