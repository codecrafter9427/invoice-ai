"""M4 tests: aging/spend reports, CSV, category confirm PATCH, document preview."""

from __future__ import annotations

from datetime import date, timedelta


def _login(client, email: str, password: str = "demo") -> dict:
    res = client.post(
        "/api/v1/auth/demo-login",
        json={"email": email, "password": password},
    )
    assert res.status_code == 200, res.text
    return res.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_health_m4(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    # M6 bumped health version; keep assertion current
    assert body["version"] == "0.6.0-m6"


def test_reports_require_auth(client):
    for path in (
        "/api/v1/reports/payables",
        "/api/v1/reports/payables/aging",
        "/api/v1/reports/payables/supplier-spend",
        "/api/v1/reports/payables/export.csv?report=aging",
    ):
        res = client.get(path)
        assert res.status_code == 401, path


def test_aging_report_buckets(client):
    demo = _login(client, "demo@invoiceai.local")
    res = client.get(
        "/api/v1/reports/payables/aging",
        headers=_auth(demo["access_token"]),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert "buckets" in body
    assert len(body["buckets"]) == 5
    codes = {b["bucket"] for b in body["buckets"]}
    assert codes == {"current", "1_30", "31_60", "61_90", "90_plus"}
    assert body["invoice_count"] >= 1
    assert "total_balance_due" in body
    assert isinstance(body["rows"], list)


def test_supplier_spend_report(client):
    demo = _login(client, "demo@invoiceai.local")
    res = client.get(
        "/api/v1/reports/payables/supplier-spend",
        headers=_auth(demo["access_token"]),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["supplier_count"] >= 1
    assert len(body["rows"]) >= 1
    row = body["rows"][0]
    assert "total_spend" in row
    assert "outstanding" in row
    assert "supplier_name" in row


def test_payables_overview(client):
    demo = _login(client, "demo@invoiceai.local")
    res = client.get(
        "/api/v1/reports/payables",
        headers=_auth(demo["access_token"]),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert "aging" in body and "supplier_spend" in body


def test_csv_export_aging_and_spend(client):
    demo = _login(client, "demo@invoiceai.local")
    aging = client.get(
        "/api/v1/reports/payables/export.csv",
        headers=_auth(demo["access_token"]),
        params={"report": "aging"},
    )
    assert aging.status_code == 200, aging.text
    assert "text/csv" in aging.headers.get("content-type", "")
    assert "invoice_number" in aging.text.splitlines()[0]

    spend = client.get(
        "/api/v1/reports/payables/export.csv",
        headers=_auth(demo["access_token"]),
        params={"report": "supplier_spend"},
    )
    assert spend.status_code == 200, spend.text
    assert "supplier_code" in spend.text.splitlines()[0]


def test_category_confirm_patch(client):
    demo = _login(client, "demo@invoiceai.local")
    # Suggest category to get an id
    suggest = client.post(
        "/api/v1/ai/category-suggestion",
        headers=_auth(demo["access_token"]),
        json={"input": {"description": "Monthly software license seats"}},
    )
    assert suggest.status_code == 200, suggest.text
    suggested = suggest.json()["result"]["suggested_category"]
    assert suggested and suggested.get("id")

    listing = client.get(
        "/api/v1/invoices",
        headers=_auth(demo["access_token"]),
        params={"page_size": 5, "status": "needs_review"},
    )
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert items, "expected seeded needs_review invoices"
    invoice_id = items[0]["id"]

    # Dedicated category confirm endpoint
    conf = client.patch(
        f"/api/v1/invoices/{invoice_id}/category",
        headers=_auth(demo["access_token"]),
        json={"accounting_category_id": suggested["id"], "confirmed": True},
    )
    assert conf.status_code == 200, conf.text
    body = conf.json()
    assert body["accounting_category_id"] == suggested["id"]
    assert body["accounting_category_code"] == suggested["code"]

    # Also via general PATCH with category_confirmed
    conf2 = client.patch(
        f"/api/v1/invoices/{invoice_id}",
        headers=_auth(demo["access_token"]),
        json={
            "accounting_category_id": suggested["id"],
            "category_confirmed": True,
        },
    )
    assert conf2.status_code == 200, conf2.text
    assert conf2.json()["accounting_category_id"] == suggested["id"]


def test_category_confirm_requires_true(client):
    demo = _login(client, "demo@invoiceai.local")
    suggest = client.post(
        "/api/v1/ai/category-suggestion",
        headers=_auth(demo["access_token"]),
        json={"input": {"description": "office paper"}},
    )
    cat_id = suggest.json()["result"]["suggested_category"]["id"]
    listing = client.get(
        "/api/v1/invoices",
        headers=_auth(demo["access_token"]),
        params={"page_size": 1},
    )
    invoice_id = listing.json()["items"][0]["id"]
    res = client.patch(
        f"/api/v1/invoices/{invoice_id}/category",
        headers=_auth(demo["access_token"]),
        json={"accounting_category_id": cat_id, "confirmed": False},
    )
    assert res.status_code == 422


def test_document_preview_metadata(client):
    demo = _login(client, "demo@invoiceai.local")
    listing = client.get(
        "/api/v1/documents",
        headers=_auth(demo["access_token"]),
        params={"page_size": 20},
    )
    assert listing.status_code == 200, listing.text
    items = listing.json()["items"]
    assert items, "seed should include documents"
    doc = items[0]
    assert "has_ocr_text" in doc
    assert "ocr_char_count" in doc
    assert "ocr_text_preview" in doc
    assert "created_at" in doc
    assert "byte_size" in doc
    assert "storage_path" in doc

    detail = client.get(
        f"/api/v1/invoices/{doc['invoice_id']}",
        headers=_auth(demo["access_token"]),
    )
    assert detail.status_code == 200, detail.text
    docs = detail.json().get("documents") or []
    assert isinstance(docs, list)
    if docs:
        assert "filename" in docs[0]
        assert "ocr_char_count" in docs[0]


def test_aging_as_of_param(client):
    demo = _login(client, "demo@invoiceai.local")
    as_of = (date.today() + timedelta(days=120)).isoformat()
    res = client.get(
        "/api/v1/reports/payables/aging",
        headers=_auth(demo["access_token"]),
        params={"as_of": as_of},
    )
    assert res.status_code == 200, res.text
    assert res.json()["as_of"] == as_of
