"""Deterministic invoice totals — never delegated to AI."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Sequence

MONEY = Decimal("0.01")
QTY = Decimal("0.0001")
RATE = Decimal("0.0001")


def money(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def compute_line_amounts(
    quantity: Decimal | str | int | float,
    unit_price: Decimal | str | int | float,
    tax_rate: Decimal | str | int | float = Decimal("0"),
) -> tuple[Decimal, Decimal, Decimal]:
    """Return (line_subtotal, line_tax, line_total) quantized to cents."""
    qty = Decimal(str(quantity)).quantize(QTY, rounding=ROUND_HALF_UP)
    price = money(unit_price)
    rate = Decimal(str(tax_rate)).quantize(RATE, rounding=ROUND_HALF_UP)
    line_subtotal = money(qty * price)
    line_tax = money(line_subtotal * rate)
    line_total = money(line_subtotal + line_tax)
    return line_subtotal, line_tax, line_total


def compute_invoice_totals(
    lines: Sequence[tuple[Decimal | str | int | float, Decimal | str | int | float, Decimal | str | int | float]],
) -> tuple[Decimal, Decimal, Decimal, list[tuple[Decimal, Decimal, Decimal]]]:
    """Aggregate subtotal, tax_total, total from (qty, unit_price, tax_rate) lines.

    Returns (subtotal, tax_total, total, per_line_amounts).
    """
    if not lines:
        zero = money(0)
        return zero, zero, zero, []

    per_line: list[tuple[Decimal, Decimal, Decimal]] = []
    subtotal = Decimal("0.00")
    tax_total = Decimal("0.00")
    for qty, unit_price, tax_rate in lines:
        line_sub, line_tax, line_total = compute_line_amounts(qty, unit_price, tax_rate)
        per_line.append((line_sub, line_tax, line_total))
        subtotal += line_sub
        tax_total += line_tax
    subtotal = money(subtotal)
    tax_total = money(tax_total)
    total = money(subtotal + tax_total)
    return subtotal, tax_total, total, per_line


def validate_header_totals(
    subtotal: Decimal,
    tax_total: Decimal,
    total: Decimal,
) -> list[str]:
    """Return validation issue codes; empty means OK."""
    issues: list[str] = []
    expected = money(subtotal + tax_total)
    if money(total) != expected:
        issues.append("total_mismatch")
    return issues
