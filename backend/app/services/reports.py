"""Deterministic payables aging and supplier-spend reports."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Invoice, InvoiceStatus
from app.services.totals import money

OPEN_STATUSES = {
    InvoiceStatus.UPLOADED,
    InvoiceStatus.PROCESSING,
    InvoiceStatus.NEEDS_REVIEW,
    InvoiceStatus.PENDING_APPROVAL,
    InvoiceStatus.APPROVED,
    InvoiceStatus.PARTIALLY_PAID,
    InvoiceStatus.REJECTED,
}

BUCKETS = ("current", "1_30", "31_60", "61_90", "90_plus")


def _as_of(as_of: date | None) -> date:
    return as_of or datetime.now(timezone.utc).date()


def _days_past_due(due: date | None, as_of: date, invoice_date: date) -> int:
    """Days past due; use invoice_date when due is missing."""
    ref = due or invoice_date
    return (as_of - ref).days


def _bucket_for(days_past: int) -> str:
    if days_past <= 0:
        return "current"
    if days_past <= 30:
        return "1_30"
    if days_past <= 60:
        return "31_60"
    if days_past <= 90:
        return "61_90"
    return "90_plus"


def _open_invoices(db: Session, organization_id: UUID) -> list[Invoice]:
    return list(
        db.scalars(
            select(Invoice)
            .where(
                Invoice.organization_id == organization_id,
                Invoice.archived.is_(False),
                Invoice.balance_due > 0,
                Invoice.status.in_(list(OPEN_STATUSES)),
            )
            .options(selectinload(Invoice.supplier))
            .order_by(Invoice.due_date.asc().nulls_last(), Invoice.invoice_date.asc())
        ).all()
    )


def aging_report(
    db: Session,
    *,
    organization_id: UUID,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Aging buckets by outstanding balance_due (deterministic)."""
    as_of_date = _as_of(as_of)
    invoices = _open_invoices(db, organization_id)

    buckets: dict[str, dict[str, Any]] = {
        b: {"bucket": b, "invoice_count": 0, "balance_due": "0.00", "_sum": Decimal("0")}
        for b in BUCKETS
    }
    rows: list[dict[str, Any]] = []

    for inv in invoices:
        days = _days_past_due(inv.due_date, as_of_date, inv.invoice_date)
        bucket = _bucket_for(days)
        bal = money(inv.balance_due)
        buckets[bucket]["invoice_count"] += 1
        buckets[bucket]["_sum"] = money(buckets[bucket]["_sum"] + bal)
        supplier_name = inv.supplier.name if inv.supplier else None
        rows.append(
            {
                "invoice_id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "supplier_id": str(inv.supplier_id),
                "supplier_name": supplier_name,
                "status": inv.status.value,
                "invoice_date": inv.invoice_date.isoformat(),
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "days_past_due": days,
                "bucket": bucket,
                "currency": inv.currency,
                "total": str(money(inv.total)),
                "balance_due": str(bal),
            }
        )

    for b in BUCKETS:
        buckets[b]["balance_due"] = str(buckets[b].pop("_sum"))

    total_balance = money(sum((Decimal(buckets[b]["balance_due"]) for b in BUCKETS), Decimal("0")))
    return {
        "as_of": as_of_date.isoformat(),
        "currency": "USD",
        "total_balance_due": str(total_balance),
        "invoice_count": len(rows),
        "buckets": [buckets[b] for b in BUCKETS],
        "rows": rows,
    }


def supplier_spend_report(
    db: Session,
    *,
    organization_id: UUID,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Aggregate spend (invoice totals) and outstanding by supplier."""
    as_of_date = _as_of(as_of)
    invoices = list(
        db.scalars(
            select(Invoice)
            .where(
                Invoice.organization_id == organization_id,
                Invoice.archived.is_(False),
                Invoice.status != InvoiceStatus.ARCHIVED,
            )
            .options(selectinload(Invoice.supplier))
        ).all()
    )

    by_supplier: dict[UUID, dict[str, Any]] = {}
    for inv in invoices:
        entry = by_supplier.get(inv.supplier_id)
        if entry is None:
            entry = {
                "supplier_id": str(inv.supplier_id),
                "supplier_name": inv.supplier.name if inv.supplier else None,
                "supplier_code": inv.supplier.code if inv.supplier else None,
                "invoice_count": 0,
                "total_spend": Decimal("0"),
                "outstanding": Decimal("0"),
                "currency": inv.currency,
            }
            by_supplier[inv.supplier_id] = entry
        entry["invoice_count"] += 1
        entry["total_spend"] = money(entry["total_spend"] + inv.total)
        if inv.balance_due > 0:
            entry["outstanding"] = money(entry["outstanding"] + inv.balance_due)

    rows = []
    for entry in by_supplier.values():
        rows.append(
            {
                "supplier_id": entry["supplier_id"],
                "supplier_name": entry["supplier_name"],
                "supplier_code": entry["supplier_code"],
                "invoice_count": entry["invoice_count"],
                "currency": entry["currency"],
                "total_spend": str(entry["total_spend"]),
                "outstanding": str(entry["outstanding"]),
            }
        )
    rows.sort(key=lambda r: Decimal(r["total_spend"]), reverse=True)

    return {
        "as_of": as_of_date.isoformat(),
        "supplier_count": len(rows),
        "total_spend": str(
            money(sum((Decimal(r["total_spend"]) for r in rows), Decimal("0")))
        ),
        "total_outstanding": str(
            money(sum((Decimal(r["outstanding"]) for r in rows), Decimal("0")))
        ),
        "rows": rows,
    }


def aging_to_csv(report: dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "invoice_number",
            "supplier_name",
            "status",
            "invoice_date",
            "due_date",
            "days_past_due",
            "bucket",
            "currency",
            "total",
            "balance_due",
        ]
    )
    for row in report.get("rows", []):
        writer.writerow(
            [
                row.get("invoice_number"),
                row.get("supplier_name"),
                row.get("status"),
                row.get("invoice_date"),
                row.get("due_date") or "",
                row.get("days_past_due"),
                row.get("bucket"),
                row.get("currency"),
                row.get("total"),
                row.get("balance_due"),
            ]
        )
    return buf.getvalue()


def supplier_spend_to_csv(report: dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "supplier_code",
            "supplier_name",
            "invoice_count",
            "currency",
            "total_spend",
            "outstanding",
        ]
    )
    for row in report.get("rows", []):
        writer.writerow(
            [
                row.get("supplier_code"),
                row.get("supplier_name"),
                row.get("invoice_count"),
                row.get("currency"),
                row.get("total_spend"),
                row.get("outstanding"),
            ]
        )
    return buf.getvalue()

