"""Approvals API — Coming Soon stubs (no workflow yet)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.errors import coming_soon

router = APIRouter()


@router.api_route("", methods=["GET", "POST"])
@router.api_route("/{approval_id}", methods=["GET", "PATCH"])
async def approvals_stub(approval_id: str | None = None) -> JSONResponse:
    return coming_soon("approvals")
