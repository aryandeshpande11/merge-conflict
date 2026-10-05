from fastapi import APIRouter, Response, status
from app.schemas.prediction import HealthResponse
from app.services.model_service import model_service

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def get_health(response: Response):
    """
    Health check endpoint reporting application readiness and model load status.
    """
    if model_service.is_loaded:
        return HealthResponse(
            status="healthy",
            model_loaded=True,
            model_version=model_service.version,
        )

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="unhealthy",
        model_loaded=False,
        model_version=None,
    )
