import math
import os
from contextlib import asynccontextmanager
from typing import Any, List

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes.health import router as health_router
from app.routes.prediction import router as prediction_router
from app.routes.repository import router as repository_router
from app.services.model_service import model_service

# Load environment variables from .env if present
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Loads the XGBoost ML model and metadata once at startup.
    """
    print("[FastAPI Startup] Initializing ModelService...")
    success = model_service.load_model()
    if success:
        print(f"[FastAPI Startup] Model v{model_service.version} loaded successfully from {model_service.model_path}")
    else:
        print(f"[FastAPI Startup] WARNING: Model loading failed: {model_service.load_error}")
    yield
    print("[FastAPI Shutdown] Shutting down application...")


app = FastAPI(
    title="Merge Conflict Resolution Predictor API",
    description=(
        "Production-grade FastAPI service powered by an XGBoost multiclass classifier "
        "trained on real-world Git merge conflict history. Predicts whether a merge conflict "
        "should be resolved by keeping local changes, keeping incoming changes, or combining both."
    ),
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS securely from environment
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000")
allowed_origins: List[str] = [
    origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()
]

# Ensure no unrestricted wildcard in production
if "*" in allowed_origins and len(allowed_origins) > 1:
    allowed_origins = [o for o in allowed_origins if o != "*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# Custom exception handler: sanitize NaN/Inf in validation error details
# before JSON serialization. Python's JSON encoder rejects NaN/Inf, but
# Pydantic captures the raw input (which may be NaN) in the error detail.
def _sanitize_for_json(obj: Any) -> Any:
    """Recursively replace NaN/Inf float values with string representations."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(item) for item in obj]
    return obj


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return a clean 422 response even when the invalid input contains NaN/Inf."""
    sanitized_errors = _sanitize_for_json(exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": sanitized_errors},
    )


# Register routers
app.include_router(health_router)
app.include_router(prediction_router)
app.include_router(repository_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Merge Conflict Resolution Predictor API",
        "version": "v3",
        "docs_url": "/docs",
        "health_url": "/health",
    }
