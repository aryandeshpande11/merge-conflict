from fastapi import APIRouter, HTTPException, status

from app.schemas.prediction import (
    RepositoryAnalysisRequest,
    RepositoryAnalysisResponse,
)
from app.services.feature_service import FeatureService
from app.services.model_service import model_service

router = APIRouter(prefix="/api/v1", tags=["Repository Analysis"])


@router.post(
    "/analyze-repository",
    response_model=RepositoryAnalysisResponse,
    summary="Replay and analyze a Git merge conflict from repository commit",
    description="Analyzes a Git repository merge commit, replays the merge between parents, "
                "extracts all 12 ML features, and predicts the resolution strategy.",
)
def analyze_repository(request: RepositoryAnalysisRequest):
    """
    Validates repository and commit, safely replays merge between parents,
    extracts the exact 12 features, and generates model prediction.
    """
    if not model_service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model is not ready for inference: {model_service.load_error or 'Model not loaded'}",
        )

    try:
        features = FeatureService.analyze_git_repository_merge(
            repo_path_str=request.repository_path,
            merge_commit_str=request.merge_commit,
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during repository analysis: {str(e)}",
        )

    # Convert extracted features to DataFrame and predict
    features_df = FeatureService.dict_to_dataframe(features)
    prediction = model_service.predict_single(features_df)

    return RepositoryAnalysisResponse(
        repository_path=request.repository_path,
        merge_commit=request.merge_commit,
        features=features,
        prediction=prediction,
    )
