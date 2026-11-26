"""Invoice reviews API — Coming Soon stubs."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.errors import coming_soon

router = APIRouter()


@router.api_route("", methods=["GET", "POST"])
@router.api_route("/{review_id}", methods=["GET", "PATCH"])
async def reviews_stub(review_id: str | None = None) -> JSONResponse:
    return coming_soon("invoice-reviews")
