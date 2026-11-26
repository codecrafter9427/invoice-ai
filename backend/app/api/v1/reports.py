"""Payables reports — aging, supplier spend, CSV export."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.api.deps import CurrentUser, DbSession
from app.core.errors import ApiError
from app.services.reports import (
    aging_report,
    aging_to_csv,
    supplier_spend_report,
    supplier_spend_to_csv,
)

router = APIRouter()


@router.get("/payables")
def payables_overview(
    user: CurrentUser,
    db: DbSession,
    as_of: date | None = None,
) -> dict:
    """Combined payables snapshot: aging summary + supplier spend totals."""
    aging = aging_report(db, organization_id=user.organization_id, as_of=as_of)
    spend = supplier_spend_report(
        db, organization_id=user.organization_id, as_of=as_of
    )
    return {
        "as_of": aging["as_of"],
        "aging": {
            "total_balance_due": aging["total_balance_due"],
            "invoice_count": aging["invoice_count"],
            "buckets": aging["buckets"],
        },
        "supplier_spend": {
            "supplier_count": spend["supplier_count"],
            "total_spend": spend["total_spend"],
            "total_outstanding": spend["total_outstanding"],
        },
    }


@router.get("/payables/aging")
def payables_aging(
    user: CurrentUser,
    db: DbSession,
    as_of: date | None = None,
) -> dict:
    return aging_report(db, organization_id=user.organization_id, as_of=as_of)


@router.get("/payables/supplier-spend")
def payables_supplier_spend(
    user: CurrentUser,
    db: DbSession,
    as_of: date | None = None,
) -> dict:
    return supplier_spend_report(
        db, organization_id=user.organization_id, as_of=as_of
    )


@router.get("/payables/export.csv")
def payables_csv_export(
    user: CurrentUser,
    db: DbSession,
    report: str = Query(
        "aging",
        description="aging | supplier_spend",
    ),
    as_of: date | None = None,
) -> Response:
    key = report.strip().lower().replace("-", "_")
    if key == "aging":
        data = aging_report(db, organization_id=user.organization_id, as_of=as_of)
        csv_body = aging_to_csv(data)
        filename = f"payables-aging-{data['as_of']}.csv"
    elif key in {"supplier_spend", "supplierspend", "spend"}:
        data = supplier_spend_report(
            db, organization_id=user.organization_id, as_of=as_of
        )
        csv_body = supplier_spend_to_csv(data)
        filename = f"payables-supplier-spend-{data['as_of']}.csv"
    else:
        raise ApiError(
            status_code=400,
            code="invalid_report",
            message="report must be aging or supplier_spend",
            details={"report": report},
        )
    return Response(
        content=csv_body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
