"""AI endpoints — stubbed via AIProvider (no real extraction)."""

from fastapi import APIRouter

from app.ai import get_ai_provider
from app.schemas.common import AIRequest, AIResponse

router = APIRouter()


@router.post("/invoice-extract", response_model=AIResponse)
async def invoice_extract(body: AIRequest) -> AIResponse:
    provider = get_ai_provider()
    return await provider.invoice_extract(body)


@router.post("/invoice-anomalies", response_model=AIResponse)
async def invoice_anomalies(body: AIRequest) -> AIResponse:
    provider = get_ai_provider()
    return await provider.invoice_anomalies(body)


@router.post("/category-suggestion", response_model=AIResponse)
async def category_suggestion(body: AIRequest) -> AIResponse:
    provider = get_ai_provider()
    return await provider.category_suggestion(body)
