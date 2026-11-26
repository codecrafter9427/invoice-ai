"""Invoice Anomaly Radar — rules-first review signals.

Signals are transparent review hints. This module NEVER declares fraud.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Invoice, Supplier
from app.services.invoices import find_duplicate_invoices
from app.services.totals import money, validate_header_totals


def _signal(
    *,
    code: str,
    severity: str,
    message: str,
    evidence: dict[str, Any] | None = None,
    explanation: str,
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "evidence": evidence or {},
        "explanation": explanation,
        "is_fraud_verdict": False,  # hard rule — never fraud
    }


def _normalize_pay(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.lower().split())


def evaluate_anomaly_signals(
    *,
    invoice: Invoice,
    supplier: Supplier | None,
    peer_totals: list[Decimal],
    stated_payment_details: str | None = None,
    duplicates: list[Invoice] | None = None,
) -> list[dict[str, Any]]:
    """Run deterministic anomaly rules against one invoice."""
    signals: list[dict[str, Any]] = []

    # 1) Total / tax discrepancy (header vs subtotal+tax)
    header_issues = validate_header_totals(
        invoice.subtotal, invoice.tax_total, invoice.total
    )
    if "total_mismatch" in header_issues:
        expected = money(invoice.subtotal + invoice.tax_total)
        signals.append(
            _signal(
                code="total_tax_discrepancy",
                severity="high",
                message="Header total does not match subtotal + tax.",
                evidence={
                    "subtotal": str(invoice.subtotal),
                    "tax_total": str(invoice.tax_total),
                    "total": str(invoice.total),
                    "expected_total": str(expected),
                },
                explanation=(
                    "Rule: money(subtotal + tax_total) must equal money(total). "
                    "Mismatch is a review signal (possible OCR or entry error), "
                    "not a fraud verdict."
                ),
            )
        )

    # Also compare line sum when lines are loaded
    if invoice.lines:
        line_sum = money(sum((ln.line_total for ln in invoice.lines), Decimal("0")))
        if line_sum != money(invoice.total) and "total_tax_discrepancy" not in {
            s["code"] for s in signals
        }:
            # Only add if meaningfully different from already flagged header issue
            if line_sum != money(invoice.subtotal + invoice.tax_total) or line_sum != money(
                invoice.total
            ):
                signals.append(
                    _signal(
                        code="total_tax_discrepancy",
                        severity="high",
                        message="Sum of line totals differs from invoice total.",
                        evidence={
                            "line_sum": str(line_sum),
                            "invoice_total": str(invoice.total),
                        },
                        explanation=(
                            "Rule: sum(line_total) should equal invoice total. "
                            "Investigate before payment. Not a fraud declaration."
                        ),
                    )
                )

    # 2) Duplicate-like invoice
    dups = duplicates if duplicates is not None else []
    if invoice.has_duplicate_warning or dups:
        signals.append(
            _signal(
                code="duplicate_like",
                severity="high",
                message="Duplicate-like invoice: same supplier and invoice number exists.",
                evidence={
                    "supplier_id": str(invoice.supplier_id),
                    "invoice_number": invoice.invoice_number,
                    "other_invoice_ids": [str(d.id) for d in dups],
                    "seed_flag": invoice.has_duplicate_warning,
                },
                explanation=(
                    "Rule: another non-archived invoice shares supplier_id + invoice_number. "
                    "Confirm this is not a double capture. This is a review signal only."
                ),
            )
        )

    # 3) Unusual amount vs supplier peers
    peers = [money(t) for t in peer_totals if t is not None]
    # exclude self if accidentally included
    peers = [t for t in peers if t != money(invoice.total)] or peers
    if peers:
        avg = money(sum(peers, Decimal("0")) / Decimal(len(peers)))
        current = money(invoice.total)
        # Flag when current is >= 3x peer average and absolute gap is material
        if avg > Decimal("0") and current >= money(avg * Decimal("3")) and current - avg >= Decimal(
            "500"
        ):
            signals.append(
                _signal(
                    code="unusual_amount",
                    severity="medium",
                    message="Invoice amount is unusually high versus recent supplier invoices.",
                    evidence={
                        "invoice_total": str(current),
                        "peer_average": str(avg),
                        "peer_count": len(peers),
                        "threshold": ">= 3x peer average and gap >= 500",
                    },
                    explanation=(
                        "Rule: total >= 3 × average of other invoices for this supplier "
                        "and absolute gap ≥ 500. Unusual relative to history — "
                        "review before approve/pay. Never treated as fraud proof."
                    ),
                )
            )
    elif invoice.has_anomaly_signal and invoice.anomaly_notes and "amount" in (
        invoice.anomaly_notes or ""
    ).lower():
        signals.append(
            _signal(
                code="unusual_amount",
                severity="medium",
                message="Seeded unusual-amount note present; few peer invoices to compare.",
                evidence={"anomaly_notes": invoice.anomaly_notes},
                explanation=(
                    "Rule: insufficient peer history; surfaced from stored review note. "
                    "Human judgment required. Not a fraud verdict."
                ),
            )
        )

    # 4) Changed payment details
    stated = stated_payment_details
    if not stated and invoice.anomaly_notes:
        notes_l = invoice.anomaly_notes.lower()
        if "remittance" in notes_l or "payment_details" in notes_l or "payment detail" in notes_l:
            stated = "DIFFERS_FROM_DIRECTORY"  # seed path marker

    directory = supplier.payment_details if supplier else None
    if stated and directory:
        if stated == "DIFFERS_FROM_DIRECTORY" or _normalize_pay(stated) != _normalize_pay(
            directory
        ):
            signals.append(
                _signal(
                    code="changed_payment_details",
                    severity="high",
                    message="Payment / remittance details differ from supplier directory.",
                    evidence={
                        "directory_payment_details": directory,
                        "stated_payment_details": (
                            None if stated == "DIFFERS_FROM_DIRECTORY" else stated
                        ),
                        "from_seed_note": stated == "DIFFERS_FROM_DIRECTORY",
                    },
                    explanation=(
                        "Rule: remittance instructions on the invoice (or review note) "
                        "do not match the supplier directory payment_details. "
                        "Verify bank/ACH details with a known contact before paying. "
                        "This is a review signal — not a fraud verdict."
                    ),
                )
            )
    elif stated == "DIFFERS_FROM_DIRECTORY":
        signals.append(
            _signal(
                code="changed_payment_details",
                severity="high",
                message="Payment details change flagged in review notes.",
                evidence={"anomaly_notes": invoice.anomaly_notes},
                explanation=(
                    "Rule: review notes indicate remittance differs from directory. "
                    "Confirm payment destination. Not a fraud declaration."
                ),
            )
        )

    # Ensure is_fraud_verdict is always False
    for s in signals:
        s["is_fraud_verdict"] = False

    return signals


def load_and_evaluate(
    db: Session,
    *,
    organization_id: UUID,
    invoice_id: UUID,
    stated_payment_details: str | None = None,
) -> tuple[Invoice | None, list[dict[str, Any]]]:
    """Load org-scoped invoice and return anomaly signals."""
    inv = db.scalar(
        select(Invoice)
        .where(
            Invoice.id == invoice_id,
            Invoice.organization_id == organization_id,
            Invoice.archived.is_(False),
        )
        .options(selectinload(Invoice.lines))
    )
    if inv is None:
        return None, []

    supplier = db.get(Supplier, inv.supplier_id)
    peers = list(
        db.scalars(
            select(Invoice.total).where(
                Invoice.organization_id == organization_id,
                Invoice.supplier_id == inv.supplier_id,
                Invoice.id != inv.id,
                Invoice.archived.is_(False),
            )
        ).all()
    )
    dups = find_duplicate_invoices(
        db,
        organization_id=organization_id,
        supplier_id=inv.supplier_id,
        invoice_number=inv.invoice_number,
        exclude_invoice_id=inv.id,
    )
    signals = evaluate_anomaly_signals(
        invoice=inv,
        supplier=supplier,
        peer_totals=peers,
        stated_payment_details=stated_payment_details,
        duplicates=dups,
    )
    return inv, signals


def summarize_radar(signals: list[dict[str, Any]]) -> str:
    if not signals:
        return (
            "No anomaly rules fired for this invoice. Absence of signals is not a "
            "guarantee of correctness — still complete normal review."
        )
    codes = ", ".join(s["code"] for s in signals)
    return (
        f"Invoice Anomaly Radar found {len(signals)} review signal(s): {codes}. "
        "These are transparent, rules-first hints for human review. "
        "The system never declares fraud."
    )
