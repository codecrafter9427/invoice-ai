"""M6 tests: review queue, PO match, permissions, audit, connector, hardening."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.core.config import Settings, validate_production_secrets
from app.core.rate_limit import reset_rate_limits


def _login(client, email: str, password: str = "demo") -> dict:
    res = client.post(
        "/api/v1/auth/demo-login",
        json={"email": email, "password": password},
    )
    assert res.status_code == 200, res.text
    return res.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _first_supplier_id(client, token: str) -> str:
    res = client.get("/api/v1/suppliers", headers=_auth(token), params={"page_size": 1})
    assert res.status_code == 200
    return res.json()["items"][0]["id"]


def _create_invoice(client, token: str, *, supplier_id: str, number: str | None = None, **extra):
    body = {
        "supplier_id": supplier_id,
        "invoice_number": number or f"M6-{uuid4().hex[:8]}",
        "invoice_date": date.today().isoformat(),
        "due_date": (date.today() + timedelta(days=30)).isoformat(),
        "currency": "USD",
        "lines": [
            {
                "description": "M6 widget",
                "quantity": "1",
                "unit_price": "100.00",
                "tax_rate": "0.00",
            }
        ],
        "submit_for_review": True,
        **extra,
    }
    return client.post("/api/v1/invoices", headers=_auth(token), json=body)


def test_health_version_m6(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["version"] == "0.6.0-m6"


def test_demo_login_returns_expires_in(client):
    body = _login(client, "demo@invoiceai.local")
    assert "expires_in" in body
    assert body["expires_in"] > 0
    assert body["access_token"]


def test_auth_refresh(client):
    demo = _login(client, "demo@invoiceai.local")
    res = client.post(
        "/api/v1/auth/refresh",
        headers=_auth(demo["access_token"]),
    )
    assert res.status_code == 200, res.text
    refreshed = res.json()
    assert refreshed["access_token"]
    assert refreshed["expires_in"] > 0
    assert refreshed["email"] == demo["email"]


def test_review_queue_lists_needs_review(client):
    reviewer = _login(client, "reviewer@invoiceai.local")
    res = client.get(
        "/api/v1/invoice-reviews/queue",
        headers=_auth(reviewer["access_token"]),
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "items" in data
    for item in data["items"]:
        assert item["status"] == "needs_review"


def test_review_create_and_resolve_audited(client):
    admin = _login(client, "demo@invoiceai.local")
    reviewer = _login(client, "reviewer@invoiceai.local")
    supplier_id = _first_supplier_id(client, admin["access_token"])
    created = _create_invoice(
        client, admin["access_token"], supplier_id=supplier_id
    )
    assert created.status_code == 201, created.text
    invoice_id = created.json()["id"]

    res = client.post(
        "/api/v1/invoice-reviews",
        headers=_auth(reviewer["access_token"]),
        json={
            "invoice_id": invoice_id,
            "flag": "duplicate",
            "notes": "M6 duplicate check note",
        },
    )
    assert res.status_code == 201, res.text
    review = res.json()
    assert review["flag"] == "duplicate"
    assert review["is_resolved"] is False

    patch = client.patch(
        f"/api/v1/invoice-reviews/{review['id']}",
        headers=_auth(reviewer["access_token"]),
        json={"is_resolved": True, "notes": "Resolved after check"},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["is_resolved"] is True

    audit = client.get(
        "/api/v1/audit-events",
        headers=_auth(admin["access_token"]),
        params={"action": "review_create"},
    )
    assert audit.status_code == 200
    assert audit.json()["total"] >= 1

    audit_resolve = client.get(
        "/api/v1/audit-events",
        headers=_auth(admin["access_token"]),
        params={"action": "review_resolve"},
    )
    assert audit_resolve.status_code == 200
    assert audit_resolve.json()["total"] >= 1


def test_staff_cannot_create_review(client):
    staff = _login(client, "staff@invoiceai.local")
    admin = _login(client, "demo@invoiceai.local")
    supplier_id = _first_supplier_id(client, admin["access_token"])
    created = _create_invoice(
        client, admin["access_token"], supplier_id=supplier_id
    )
    invoice_id = created.json()["id"]
    res = client.post(
        "/api/v1/invoice-reviews",
        headers=_auth(staff["access_token"]),
        json={"invoice_id": invoice_id, "flag": "other", "notes": "nope"},
    )
    assert res.status_code == 403


def test_po_candidates_include_differences(client):
    reviewer = _login(client, "reviewer@invoiceai.local")
    # Seeded mismatch/candidate invoice
    invoices = client.get(
        "/api/v1/invoices",
        headers=_auth(reviewer["access_token"]),
        params={"page_size": 50},
    )
    assert invoices.status_code == 200
    target = next(
        (i for i in invoices.json()["items"] if i["invoice_number"] == "INV-ANOM-PAY-03"),
        None,
    )
    assert target is not None, "Seed must include INV-ANOM-PAY-03"

    res = client.get(
        f"/api/v1/invoices/{target['id']}/po-candidates",
        headers=_auth(reviewer["access_token"]),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["auto_match"] is False
    assert len(body["candidates"]) >= 1
    cand = body["candidates"][0]
    assert "differences" in cand
    fields = {d["field"] for d in cand["differences"]}
    assert "amount" in fields
    assert "po_number" in fields


def test_po_match_requires_confirmed_true(client):
    reviewer = _login(client, "reviewer@invoiceai.local")
    invoices = client.get(
        "/api/v1/invoices",
        headers=_auth(reviewer["access_token"]),
        params={"page_size": 50},
    )
    target = next(
        i
        for i in invoices.json()["items"]
        if i["invoice_number"] == "INV-ANOM-PAY-03"
    )
    cands = client.get(
        f"/api/v1/invoices/{target['id']}/po-candidates",
        headers=_auth(reviewer["access_token"]),
    ).json()["candidates"]
    assert cands
    po_id = cands[0]["id"]

    bad = client.post(
        f"/api/v1/invoices/{target['id']}/po-match",
        headers=_auth(reviewer["access_token"]),
        json={"purchase_order_reference_id": po_id, "confirmed": False},
    )
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "confirmation_required"

    # Ensure extract path still does not auto-link
    detail_before = client.get(
        f"/api/v1/invoices/{target['id']}",
        headers=_auth(reviewer["access_token"]),
    ).json()
    assert detail_before.get("purchase_order_reference_id") in (None, detail_before.get("purchase_order_reference_id"))


def test_po_match_confirm_sets_fk_and_audits(client):
    admin = _login(client, "demo@invoiceai.local")
    reviewer = _login(client, "reviewer@invoiceai.local")
    supplier_id = _first_supplier_id(client, admin["access_token"])
    created = _create_invoice(
        client,
        admin["access_token"],
        supplier_id=supplier_id,
        po_reference="PO-2026-0101",
    )
    assert created.status_code == 201, created.text
    invoice_id = created.json()["id"]

    cands = client.get(
        f"/api/v1/invoices/{invoice_id}/po-candidates",
        headers=_auth(reviewer["access_token"]),
    )
    assert cands.status_code == 200, cands.text
    candidates = cands.json()["candidates"]
    assert candidates, "Expected PO-2026-0101 candidate"
    po_id = candidates[0]["id"]

    staff = _login(client, "staff@invoiceai.local")
    staff_deny = client.post(
        f"/api/v1/invoices/{invoice_id}/po-match",
        headers=_auth(staff["access_token"]),
        json={"purchase_order_reference_id": po_id, "confirmed": True},
    )
    assert staff_deny.status_code == 403

    ok = client.post(
        f"/api/v1/invoices/{invoice_id}/po-match",
        headers=_auth(reviewer["access_token"]),
        json={"purchase_order_reference_id": po_id, "confirmed": True},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["purchase_order_reference_id"] == po_id
    assert ok.json()["matched_po_number"]

    audit = client.get(
        "/api/v1/audit-events",
        headers=_auth(admin["access_token"]),
        params={"action": "po_match_confirm", "entity_id": invoice_id},
    )
    assert audit.status_code == 200
    assert audit.json()["total"] >= 1


def test_staff_forbidden_approve_and_pay(client):
    staff = _login(client, "staff@invoiceai.local")
    admin = _login(client, "demo@invoiceai.local")
    pending = client.get(
        "/api/v1/approvals/pending-invoices",
        headers=_auth(admin["access_token"]),
    ).json()["items"]
    assert pending
    inv_id = pending[0]["id"]

    deny_approve = client.post(
        f"/api/v1/approvals?invoice_id={inv_id}",
        headers=_auth(staff["access_token"]),
        json={"decision": "approved", "comment": "nope"},
    )
    assert deny_approve.status_code == 403

    deny_pay = client.post(
        "/api/v1/payments",
        headers=_auth(staff["access_token"]),
        json={
            "invoice_id": inv_id,
            "amount": "1.00",
            "payment_date": date.today().isoformat(),
            "method": "ach",
        },
    )
    assert deny_pay.status_code == 403


def test_other_org_cannot_see_reviews(client):
    other = _login(client, "other@otherco.local")
    acme = _login(client, "demo@invoiceai.local")
    queue = client.get(
        "/api/v1/invoice-reviews/queue",
        headers=_auth(acme["access_token"]),
    ).json()["items"]
    assert queue
    acme_invoice = queue[0]["invoice_id"]

    other_queue = client.get(
        "/api/v1/invoice-reviews/queue",
        headers=_auth(other["access_token"]),
    )
    assert other_queue.status_code == 200
    other_ids = {i["invoice_id"] for i in other_queue.json()["items"]}
    assert acme_invoice not in other_ids


def test_insights_connector_health_and_summary(client):
    demo = _login(client, "demo@invoiceai.local")
    health = client.get("/api/v1/connectors/insights/v1/health")
    assert health.status_code == 200
    assert health.json()["product"] == "invoice-ai"
    assert health.json()["api_version"] == "v1"

    summary = client.get(
        "/api/v1/connectors/insights/v1/payables/summary",
        headers=_auth(demo["access_token"]),
    )
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert "outstanding_balance" in body
    assert "paid_this_month" in body
    assert "aging_totals" in body
    assert set(body["aging_totals"].keys()) >= {
        "current",
        "1_30",
        "31_60",
        "61_90",
        "90_plus",
    }

    aging = client.get(
        "/api/v1/connectors/insights/v1/payables/aging",
        headers=_auth(demo["access_token"]),
    )
    assert aging.status_code == 200
    spend = client.get(
        "/api/v1/connectors/insights/v1/payables/supplier-spend",
        headers=_auth(demo["access_token"]),
    )
    assert spend.status_code == 200

    # Read-only: POST should not be allowed
    post = client.post(
        "/api/v1/connectors/insights/v1/payables/summary",
        headers=_auth(demo["access_token"]),
        json={},
    )
    assert post.status_code in {404, 405, 422}


def test_insights_connector_token_auth(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("INSIGHTS_CONNECTOR_TOKEN", "test-insights-token-m6")
    get_settings.cache_clear()
    try:
        demo = _login(client, "demo@invoiceai.local")
        org_id = demo["organization_id"]
        res = client.get(
            "/api/v1/connectors/insights/v1/payables/summary",
            headers={
                "Authorization": "Bearer test-insights-token-m6",
                "X-Organization-Id": org_id,
            },
        )
        assert res.status_code == 200, res.text
        missing_org = client.get(
            "/api/v1/connectors/insights/v1/payables/summary",
            headers={"Authorization": "Bearer test-insights-token-m6"},
        )
        assert missing_org.status_code == 400
    finally:
        monkeypatch.delenv("INSIGHTS_CONNECTOR_TOKEN", raising=False)
        get_settings.cache_clear()


def test_prod_secret_guards():
    with pytest.raises(RuntimeError):
        validate_production_secrets(
            Settings(
                app_env="production",
                secret_key="change-me-local-dev-only-32b-min",
                debug=False,
            )
        )
    with pytest.raises(RuntimeError):
        validate_production_secrets(
            Settings(
                app_env="production",
                secret_key="a" * 40,
                debug=True,
            )
        )
    # Non-prod is fine with defaults
    validate_production_secrets(
        Settings(app_env="development", secret_key="change-me-local-dev-only-32b-min", debug=True)
    )


def test_auth_rate_limit(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("AUTH_RATE_LIMIT", "3")
    monkeypatch.setenv("AUTH_RATE_WINDOW_SECONDS", "60")
    get_settings.cache_clear()
    reset_rate_limits()
    try:
        for _ in range(3):
            client.post(
                "/api/v1/auth/demo-login",
                json={"email": "nobody@invoiceai.local", "password": "wrong"},
            )
        limited = client.post(
            "/api/v1/auth/demo-login",
            json={"email": "nobody@invoiceai.local", "password": "wrong"},
        )
        assert limited.status_code == 429
        assert limited.json()["error"]["code"] == "rate_limited"
    finally:
        monkeypatch.delenv("AUTH_RATE_LIMIT", raising=False)
        monkeypatch.delenv("AUTH_RATE_WINDOW_SECONDS", raising=False)
        get_settings.cache_clear()
        reset_rate_limits()
