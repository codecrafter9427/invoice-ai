"""Auth + organization-scoping smoke tests (requires migrated + seeded DB)."""

from __future__ import annotations


def _login(client, email: str, password: str = "demo") -> dict:
    res = client.post(
        "/api/v1/auth/demo-login",
        json={"email": email, "password": password},
    )
    assert res.status_code == 200, res.text
    return res.json()


def test_demo_login_rejects_bad_password(client):
    res = client.post(
        "/api/v1/auth/demo-login",
        json={"email": "demo@invoiceai.local", "password": "wrong"},
    )
    assert res.status_code == 401
    body = res.json()
    assert body["error"]["code"] == "invalid_credentials"


def test_demo_login_admin_and_me(client):
    data = _login(client, "demo@invoiceai.local")
    assert data["role"] == "admin"
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["organization_name"]

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me.status_code == 200
    me_body = me.json()
    assert me_body["email"] == "demo@invoiceai.local"
    assert me_body["role"] == "admin"
    assert me_body["organization_id"] == data["organization_id"]


def test_second_role_login(client):
    data = _login(client, "reviewer@invoiceai.local")
    assert data["role"] == "reviewer"


def test_me_requires_auth(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_tenant_isolation_suppliers(client):
    demo = _login(client, "demo@invoiceai.local")
    other = _login(client, "other@otherco.local")

    demo_sup = client.get(
        "/api/v1/suppliers",
        headers={"Authorization": f"Bearer {demo['access_token']}"},
    )
    other_sup = client.get(
        "/api/v1/suppliers",
        headers={"Authorization": f"Bearer {other['access_token']}"},
    )
    assert demo_sup.status_code == 200
    assert other_sup.status_code == 200

    demo_body = demo_sup.json()
    other_body = other_sup.json()
    assert demo_body["total"] >= 10
    assert other_body["total"] >= 1

    demo_ids = {item["id"] for item in demo_body["items"]}
    other_ids = {item["id"] for item in other_body["items"]}
    assert demo_ids.isdisjoint(other_ids)

    for item in demo_body["items"]:
        assert item["organization_id"] == demo["organization_id"]
    for item in other_body["items"]:
        assert item["organization_id"] == other["organization_id"]


def test_tenant_isolation_invoices(client):
    demo = _login(client, "demo@invoiceai.local")
    other = _login(client, "other@otherco.local")

    demo_inv = client.get(
        "/api/v1/invoices",
        headers={"Authorization": f"Bearer {demo['access_token']}"},
    )
    other_inv = client.get(
        "/api/v1/invoices",
        headers={"Authorization": f"Bearer {other['access_token']}"},
    )
    assert demo_inv.status_code == 200
    assert other_inv.status_code == 200

    demo_body = demo_inv.json()
    other_body = other_inv.json()
    assert demo_body["total"] >= 25
    assert other_body["total"] >= 1

    demo_numbers = {i["invoice_number"] for i in demo_body["items"]}
    other_numbers = {i["invoice_number"] for i in other_body["items"]}
    assert "OTH-INV-1" not in demo_numbers
    assert demo_numbers.isdisjoint(other_numbers) or "OTH-INV-1" in other_numbers

    for item in demo_body["items"]:
        assert item["organization_id"] == demo["organization_id"]
    for item in other_body["items"]:
        assert item["organization_id"] == other["organization_id"]


def test_seeded_duplicate_and_anomaly_flags(client):
    demo = _login(client, "demo@invoiceai.local")
    res = client.get(
        "/api/v1/invoices",
        headers={"Authorization": f"Bearer {demo['access_token']}"},
        params={"page_size": 100},
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert any(i["has_duplicate_warning"] for i in items)
    assert any(i["has_anomaly_signal"] for i in items)
