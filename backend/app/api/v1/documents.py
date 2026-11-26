"""Invoice documents API — Coming Soon (no OCR upload pipeline yet)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.errors import coming_soon

router = APIRouter()


@router.api_route("", methods=["GET", "POST"])
@router.api_route("/{document_id}", methods=["GET", "DELETE"])
async def documents_stub(document_id: str | None = None) -> JSONResponse:
    return coming_soon("documents")
