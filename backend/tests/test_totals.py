"""Unit tests for deterministic invoice totals (no DB)."""

from decimal import Decimal

from app.services.totals import (
    compute_invoice_totals,
    compute_line_amounts,
    money,
    validate_header_totals,
)


def test_line_amounts_basic():
    sub, tax, total = compute_line_amounts(
        quantity="2", unit_price="10.00", tax_rate="0.10"
    )
    assert sub == Decimal("20.00")
    assert tax == Decimal("2.00")
    assert total == Decimal("22.00")


def test_invoice_totals_aggregate():
    sub, tax, total, per = compute_invoice_totals(
        [
            ("1", "100.00", "0.10"),
            ("2", "25.50", "0"),
        ]
    )
    assert sub == Decimal("151.00")
    assert tax == Decimal("10.00")
    assert total == Decimal("161.00")
    assert len(per) == 2
    assert per[0][2] == Decimal("110.00")
    assert per[1][2] == Decimal("51.00")


def test_header_total_mismatch():
    issues = validate_header_totals(
        Decimal("100.00"), Decimal("10.00"), Decimal("109.00")
    )
    assert "total_mismatch" in issues


def test_header_total_ok():
    assert validate_header_totals(
        Decimal("100.00"), Decimal("10.00"), Decimal("110.00")
    ) == []


def test_money_quantize():
    assert money("10.005") == Decimal("10.01")
    assert money("10.004") == Decimal("10.00")
