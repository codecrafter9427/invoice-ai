"""Invoices and invoice-lines API — Coming Soon stubs."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.errors import coming_soon

router = APIRouter()
lines_router = APIRouter()


@router.api_route("", methods=["GET", "POST"])
@router.api_route("/{invoice_id}", methods=["GET", "PATCH", "DELETE"])
async def invoices_stub(invoice_id: str | None = None) -> JSONResponse:
    return coming_soon("invoices")


@lines_router.api_route("", methods=["GET", "POST"])
@lines_router.api_route("/{line_id}", methods=["GET", "PATCH", "DELETE"])
async def invoice_lines_stub(line_id: str | None = None) -> JSONResponse:
    return coming_soon("invoice-lines")
