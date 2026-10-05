from app.routes.health import router as health_router
from app.routes.prediction import router as prediction_router
from app.routes.repository import router as repository_router

__all__ = ["health_router", "prediction_router", "repository_router"]
