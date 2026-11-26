"""Suppliers API — Coming Soon stubs."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.errors import coming_soon

router = APIRouter()


@router.api_route("", methods=["GET", "POST"])
@router.api_route("/{supplier_id}", methods=["GET", "PATCH", "DELETE"])
async def suppliers_stub(supplier_id: str | None = None) -> JSONResponse:
    return coming_soon("suppliers")
