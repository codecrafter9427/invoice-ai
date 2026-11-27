"""Aggregate /api/v1 routers."""

from fastapi import APIRouter

from app.api.v1 import (
    ai,
    approvals,
    audit,
    auth,
    connectors,
    documents,
    invoices,
    payments,
    reports,
    reviews,
    suppliers,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
api_router.include_router(
    invoices.lines_router, prefix="/invoice-lines", tags=["invoice-lines"]
)
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(
    reviews.router, prefix="/invoice-reviews", tags=["invoice-reviews"]
)
api_router.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(audit.router, prefix="/audit-events", tags=["audit"])
api_router.include_router(
    connectors.router,
    prefix="/connectors/insights/v1",
    tags=["insights-connector"],
)
