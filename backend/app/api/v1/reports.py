"""Payables reports API — Coming Soon stubs."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.errors import coming_soon

router = APIRouter()


@router.get("/payables")
async def payables_report_stub() -> JSONResponse:
    return coming_soon("reports/payables")
