"""Demo invoice text → structured JSON extraction (no paid OCR/LLM).

Parses pasted OCR/document text with deterministic heuristics. Extracted fields
are always unverified until a human reviews them.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any


def _money_str(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.replace(",", "").strip()
    try:
        return f"{Decimal(cleaned).quantize(Decimal('0.01'))}"
    except (InvalidOperation, ValueError):
        return None


def _first_match(pattern: str, text: str, flags: int = re.IGNORECASE) -> str | None:
    m = re.search(pattern, text, flags)
    if not m:
        return None
    return m.group(1).strip()


def extract_invoice_from_text(text: str) -> dict[str, Any]:
    """Return structured header/lines + per-field confidence.

    Confidence is heuristic (not model-calibrated). OCR remains unverified.
    """
    raw = (text or "").strip()
    if not raw:
        return {
            "header": {},
            "line_items": [],
            "field_confidence": {},
            "ocr_verified": False,
            "requires_user_review": True,
            "validation_issues": ["empty_input"],
            "validation_explanations": [
                {
                    "code": "empty_input",
                    "explanation": "No OCR/document text was provided to extract.",
                }
            ],
            "po_candidates": [],
        }

    header: dict[str, Any] = {}
    confidence: dict[str, float] = {}

    inv_num = _first_match(
        r"(?:invoice\s*(?:number|no\.?|#)\s*[:#]?\s*)([A-Z0-9][A-Z0-9\-/]+)",
        raw,
    ) or _first_match(r"\b(INV-[A-Z0-9\-]+)\b", raw)
    if inv_num:
        header["invoice_number"] = inv_num
        confidence["invoice_number"] = 0.92

    supplier = _first_match(
        r"(?:supplier|vendor|from)\s*[:\-]\s*(.+)",
        raw,
    )
    if supplier:
        # stop at newline
        supplier = supplier.splitlines()[0].strip()
        header["supplier_name"] = supplier
        confidence["supplier_name"] = 0.75

    inv_date = _first_match(
        r"(?:invoice\s*date|date)\s*[:\-]\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        raw,
    )
    if inv_date:
        header["invoice_date"] = inv_date
        confidence["invoice_date"] = 0.8

    due_date = _first_match(
        r"(?:due\s*date)\s*[:\-]\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        raw,
    )
    if due_date:
        header["due_date"] = due_date
        confidence["due_date"] = 0.78

    currency = _first_match(r"\b(USD|EUR|GBP|INR|CAD|AUD)\b", raw)
    if currency:
        header["currency"] = currency.upper()
        confidence["currency"] = 0.85
    else:
        header["currency"] = "USD"
        confidence["currency"] = 0.4

    subtotal = _money_str(_first_match(r"(?:subtotal)\s*[:\-]?\s*\$?\s*([\d,]+\.?\d*)", raw))
    if subtotal:
        header["subtotal"] = subtotal
        confidence["subtotal"] = 0.7

    tax = _money_str(
        _first_match(r"(?:tax(?:\s*total)?|vat)\s*[:\-]?\s*\$?\s*([\d,]+\.?\d*)", raw)
    )
    if tax:
        header["tax_total"] = tax
        confidence["tax_total"] = 0.7

    total = _money_str(
        _first_match(r"(?:grand\s*)?total\s*(?:due)?\s*[:\-]?\s*\$?\s*([\d,]+\.?\d*)", raw)
    )
    if total:
        header["total"] = total
        confidence["total"] = 0.82

    po = _first_match(r"(?:PO|P\.O\.|purchase\s*order)\s*(?:#|no\.?|number)?\s*[:\-]?\s*([A-Z0-9\-]+)", raw)
    if po:
        header["po_reference"] = po
        confidence["po_reference"] = 0.7

    remittance = _first_match(
        r"(?:remit(?:tance)?\s*to|pay\s*to|bank|ACH|wire)\s*[:\-]?\s*(.+)",
        raw,
    )
    if remittance:
        remittance = remittance.splitlines()[0].strip()
        header["stated_payment_details"] = remittance
        confidence["stated_payment_details"] = 0.55

    line_items: list[dict[str, Any]] = []
    # Lines like: ITEM | qty | unit | tax%   or  desc  qty x price
    for m in re.finditer(
        r"(?m)^\s*[-*]?\s*(.+?)\s+[x×]\s*([\d.]+)\s*@\s*\$?([\d,]+\.?\d*)(?:\s+tax\s*([\d.]+%?))?",
        raw,
    ):
        desc, qty, price, tax_raw = m.groups()
        tax_rate = "0"
        if tax_raw:
            tax_rate = tax_raw.replace("%", "")
            try:
                tr = Decimal(tax_rate)
                if tr > 1:
                    tax_rate = str((tr / Decimal("100")).quantize(Decimal("0.0001")))
            except InvalidOperation:
                tax_rate = "0"
        line_items.append(
            {
                "description": desc.strip(),
                "quantity": qty,
                "unit_price": _money_str(price) or price,
                "tax_rate": tax_rate,
                "confidence": 0.65,
            }
        )

    if not line_items:
        # Fallback single line from description keyword
        desc_line = _first_match(r"(?:description|item)\s*[:\-]\s*(.+)", raw)
        if desc_line and total:
            line_items.append(
                {
                    "description": desc_line.splitlines()[0].strip(),
                    "quantity": "1",
                    "unit_price": total,
                    "tax_rate": "0",
                    "confidence": 0.45,
                }
            )

    validation_issues: list[str] = []
    explanations: list[dict[str, str]] = []

    if not header.get("invoice_number"):
        validation_issues.append("missing_invoice_number")
        explanations.append(
            {
                "code": "missing_invoice_number",
                "explanation": "Could not find an invoice number in the text — enter it manually.",
            }
        )
    if not header.get("supplier_name"):
        validation_issues.append("missing_supplier")
        explanations.append(
            {
                "code": "missing_supplier",
                "explanation": "Supplier/vendor name was not detected — select the supplier during review.",
            }
        )

    if header.get("subtotal") and header.get("tax_total") and header.get("total"):
        try:
            expected = Decimal(header["subtotal"]) + Decimal(header["tax_total"])
            if expected.quantize(Decimal("0.01")) != Decimal(header["total"]):
                validation_issues.append("total_mismatch")
                explanations.append(
                    {
                        "code": "total_mismatch",
                        "explanation": (
                            f"Header total {header['total']} does not equal "
                            f"subtotal {header['subtotal']} + tax {header['tax_total']} "
                            f"(expected {expected.quantize(Decimal('0.01'))}). "
                            "Totals are verified by deterministic code, not AI."
                        ),
                    }
                )
        except InvalidOperation:
            pass

    # Ensure every extracted header field has a confidence entry
    for key in header:
        confidence.setdefault(key, 0.5)

    return {
        "header": header,
        "line_items": line_items,
        "field_confidence": confidence,
        "ocr_verified": False,
        "requires_user_review": True,
        "validation_issues": validation_issues,
        "validation_explanations": explanations,
        "po_candidates": [],  # filled by API with DB context
        "note": "Extracted fields are suggestions only. OCR is unverified until user review.",
    }


def explain_validation_issues(issue_codes: list[str]) -> list[dict[str, str]]:
    """Human-readable explanations for deterministic validation codes."""
    catalog = {
        "total_mismatch": (
            "Invoice total does not equal subtotal + tax. "
            "Fix amounts using deterministic totals; do not trust OCR totals blindly."
        ),
        "duplicate_invoice": (
            "Another invoice already exists with the same supplier and invoice number. "
            "Confirm this is not a double capture before approving."
        ),
        "due_before_invoice_date": (
            "Due date is earlier than the invoice date, which is usually a data-entry error."
        ),
        "missing_invoice_number": "Invoice number is required.",
        "missing_supplier": "Supplier is required.",
        "empty_input": "No text was provided for extraction.",
        "missing_fields": "One or more required header fields are blank.",
    }
    out: list[dict[str, str]] = []
    for code in issue_codes:
        out.append(
            {
                "code": code,
                "explanation": catalog.get(
                    code, f"Validation issue '{code}' needs human review."
                ),
            }
        )
    return out
