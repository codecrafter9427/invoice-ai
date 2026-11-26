"""M3 tests: demo extract, anomaly radar, category, auth on AI routes."""

from __future__ import annotations

from decimal import Decimal

from app.services.extract import extract_invoice_from_text
from app.services.totals import compute_invoice_totals, money


def _login(client, email: str, password: str = "demo") -> dict:
    res = client.post(
        "/api/v1/auth/demo-login",
        json={"email": email, "password": password},
    )
    assert res.status_code == 200, res.text
    return res.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


SAMPLE_OCR = """
Supplier: Northwind Office Supply
Invoice Number: INV-M3-EXTRACT-99
Invoice Date: 2026-11-10
Due Date: 2026-12-10
PO: PO-2026-0101
Paper ream case x 12 @ $24.50 tax 8%
Subtotal: $294.00
Tax: $23.52
Total: $317.52
Currency: USD
"""


def test_ai_endpoints_require_auth(client):
    for path in (
        "/api/v1/ai/invoice-extract",
        "/api/v1/ai/invoice-anomalies",
        "/api/v1/ai/category-suggestion",
    ):
        res = client.post(path, json={"input": {}})
        assert res.status_code == 401, path


def test_demo_extract_from_text(client):
    demo = _login(client, "demo@invoiceai.local")
    res = client.post(
        "/api/v1/ai/invoice-extract",
        headers=_auth(demo["access_token"]),
        json={"input": {"text": SAMPLE_OCR}, "context_ids": [], "options": {}},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["requires_confirmation"] is True
    result = body["result"]
    assert result["ocr_verified"] is False
    assert result["requires_user_review"] is True
    assert result["header"]["invoice_number"] == "INV-M3-EXTRACT-99"
    assert "invoice_number" in result["field_confidence"]
    assert isinstance(result.get("po_candidates"), list)
    # Totals in extract are suggestions; deterministic code is source of truth
    sub, tax, total, _ = compute_invoice_totals(
        [(Decimal("12"), Decimal("24.50"), Decimal("0.08"))]
    )
    assert money(sub) == money("294.00")
    assert money(tax) == money("23.52")
    assert money(total) == money("317.52")


def test_extract_unit_unverified():
    out = extract_invoice_from_text(SAMPLE_OCR)
    assert out["ocr_verified"] is False
    assert out["requires_user_review"] is True
    assert out["header"]["invoice_number"] == "INV-M3-EXTRACT-99"
    assert out["line_items"]


def test_anomaly_radar_never_fraud(client):
    demo = _login(client, "demo@invoiceai.local")
    # Find a seeded anomaly invoice
    listing = client.get(
        "/api/v1/invoices",
        headers=_auth(demo["access_token"]),
        params={"page_size": 50, "has_anomaly": True},
    )
    assert listing.status_code == 200, listing.text
    items = listing.json()["items"]
    assert items, "expected seeded anomaly/duplicate invoices"
    invoice_id = items[0]["id"]

    res = client.post(
        "/api/v1/ai/invoice-anomalies",
        headers=_auth(demo["access_token"]),
        json={
            "input": {"invoice_id": invoice_id},
            "context_ids": [invoice_id],
            "options": {},
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    result = body["result"]
    assert result.get("never_declares_fraud") is True
    assert result.get("fraud_verdict") is None
    signals = result.get("signals") or []
    for s in signals:
        assert s.get("is_fraud_verdict") is False
        msg = (s.get("message") or "").lower()
        assert "is fraud" not in msg
    assert "fraud" not in body["explanation"].lower() or "never" in body[
        "explanation"
    ].lower()


def test_anomaly_tax_discrepancy_signal(client):
    demo = _login(client, "demo@invoiceai.local")
    listing = client.get(
        "/api/v1/invoices",
        headers=_auth(demo["access_token"]),
        params={"search": "INV-ANOM-TAX-01", "page_size": 10},
    )
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert items
    invoice_id = items[0]["id"]

    res = client.post(
        "/api/v1/ai/invoice-anomalies",
        headers=_auth(demo["access_token"]),
        json={"input": {"invoice_id": invoice_id}},
    )
    assert res.status_code == 200, res.text
    codes = {s["code"] for s in res.json()["result"]["signals"]}
    assert "total_tax_discrepancy" in codes


def test_anomaly_tenant_isolation(client):
    demo = _login(client, "demo@invoiceai.local")
    other = _login(client, "other@otherco.local")
    listing = client.get(
        "/api/v1/invoices",
        headers=_auth(demo["access_token"]),
        params={"page_size": 1},
    )
    invoice_id = listing.json()["items"][0]["id"]

    res = client.post(
        "/api/v1/ai/invoice-anomalies",
        headers=_auth(other["access_token"]),
        json={"input": {"invoice_id": invoice_id}},
    )
    assert res.status_code == 404


def test_category_suggestion_requires_confirmation(client):
    demo = _login(client, "demo@invoiceai.local")
    res = client.post(
        "/api/v1/ai/category-suggestion",
        headers=_auth(demo["access_token"]),
        json={
            "input": {
                "description": "Monthly software license seats",
                "line_descriptions": ["Hosting plan Pro"],
            }
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["requires_confirmation"] is True
    suggested = body["result"].get("suggested_category")
    assert suggested is not None
    assert suggested.get("code") in {"SOFT", "OFFICE", "UTIL", "LOGISTICS"}


def test_stateless_anomaly_unusual_amount(client):
    demo = _login(client, "staff@invoiceai.local")
    res = client.post(
        "/api/v1/ai/invoice-anomalies",
        headers=_auth(demo["access_token"]),
        json={
            "input": {
                "subtotal": "10000.00",
                "tax_total": "800.00",
                "total": "10800.00",
                "peer_totals": ["100.00", "120.00", "90.00"],
                "invoice_number": "STATLESS-1",
            }
        },
    )
    assert res.status_code == 200, res.text
    codes = {s["code"] for s in res.json()["result"]["signals"]}
    assert "unusual_amount" in codes
    for s in res.json()["result"]["signals"]:
        assert s["is_fraud_verdict"] is False
