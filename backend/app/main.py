"""Invoice AI FastAPI application entrypoint."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings, validate_production_secrets
from app.core.errors import ApiError, error_body
from app.schemas.common import HealthResponse

settings = get_settings()
validate_production_secrets(settings)

APP_VERSION = settings.app_version

app = FastAPI(
    title=settings.app_name,
    version=APP_VERSION,
    description=(
        "Supplier invoice capture, review, approval, and payables visibility. "
        "Milestone 6: invoice-reviews queue, human-confirmed PO match, "
        "Insights connector, auth/AI rate limits, backup/CI hardening. "
        "Totals remain deterministic code. DemoAI default. No paid OCR/LLM."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.exception_handler(ApiError)
async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, dict) else error_body(
        "error", str(exc.detail)
    )
    return JSONResponse(status_code=exc.status_code, content=detail)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_body(
            code="validation_error",
            message="Request validation failed",
            details=exc.errors(),
        ),
    )


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(version=APP_VERSION)
