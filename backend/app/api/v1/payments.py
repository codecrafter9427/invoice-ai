"""Payments API — Coming Soon stubs (no payment recording yet)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.errors import coming_soon

router = APIRouter()


@router.api_route("", methods=["GET", "POST"])
@router.api_route("/{payment_id}", methods=["GET", "PATCH"])
async def payments_stub(payment_id: str | None = None) -> JSONResponse:
    return coming_soon("payments")
