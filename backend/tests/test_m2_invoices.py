"""M2 API tests: totals validation, duplicates, tenant, approvals, payments."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4


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
    items = res.json()["items"]
    assert items
    return items[0]["id"]


def _create_invoice(
    client,
    token: str,
    *,
    supplier_id: str,
    invoice_number: str,
    lines: list | None = None,
    subtotal=None,
    tax_total=None,
    total=None,
    submit_for_review: bool = False,
):
    body = {
        "supplier_id": supplier_id,
        "invoice_number": invoice_number,
        "invoice_date": date.today().isoformat(),
        "due_date": (date.today() + timedelta(days=30)).isoformat(),
        "currency": "USD",
        "lines": lines
        or [
            {
                "description": "Widget",
                "quantity": "2",
                "unit_price": "50.00",
                "tax_rate": "0.10",
            }
        ],
        "submit_for_review": submit_for_review,
    }
    if subtotal is not None:
        body["subtotal"] = subtotal
    if tax_total is not None:
        body["tax_total"] = tax_total
    if total is not None:
        body["total"] = total
    return client.post("/api/v1/invoices", headers=_auth(token), json=body)


def test_create_invoice_computes_totals(client):
    demo = _login(client, "demo@invoiceai.local")
    supplier_id = _first_supplier_id(client, demo["access_token"])
    number = f"M2-TOT-{uuid4().hex[:8]}"
    res = _create_invoice(client, demo["access_token"], supplier_id=supplier_id, invoice_number=number)
    assert res.status_code == 201, res.text
    body = res.json()
    # 2 * 50 = 100 subtotal; tax 10; total 110
    assert body["subtotal"] == "100.00"
    assert body["tax_total"] == "10.00"
    assert body["total"] == "110.00"
    assert body["balance_due"] == "110.00"
    assert body["status"] == "uploaded"
    assert len(body["lines"]) == 1
    assert body["lines"][0]["line_total"] == "110.00"


def test_total_mismatch_rejected(client):
    demo = _login(client, "demo@invoiceai.local")
    supplier_id = _first_supplier_id(client, demo["access_token"])
    number = f"M2-BAD-{uuid4().hex[:8]}"
    res = _create_invoice(
        client,
        demo["access_token"],
        supplier_id=supplier_id,
        invoice_number=number,
        total="999.00",
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "total_mismatch"


def test_duplicate_supplier_invoice_number_flagged(client):
    demo = _login(client, "demo@invoiceai.local")
    token = demo["access_token"]
    supplier_id = _first_supplier_id(client, token)
    number = f"M2-DUP-{uuid4().hex[:8]}"

    first = _create_invoice(client, token, supplier_id=supplier_id, invoice_number=number)
    assert first.status_code == 201, first.text
    assert first.json()["has_duplicate_warning"] is False

    second = _create_invoice(client, token, supplier_id=supplier_id, invoice_number=number)
    assert second.status_code == 201, second.text
    assert second.json()["has_duplicate_warning"] is True
    assert "duplicate_invoice" in second.json()["validation_issues"]

    # Original should also be flagged after second create
    get_first = client.get(
        f"/api/v1/invoices/{first.json()['id']}", headers=_auth(token)
    )
    assert get_first.status_code == 200
    assert get_first.json()["has_duplicate_warning"] is True


def test_due_before_invoice_date_rejected(client):
    demo = _login(client, "demo@invoiceai.local")
    supplier_id = _first_supplier_id(client, demo["access_token"])
    body = {
        "supplier_id": supplier_id,
        "invoice_number": f"M2-DATE-{uuid4().hex[:8]}",
        "invoice_date": date.today().isoformat(),
        "due_date": (date.today() - timedelta(days=1)).isoformat(),
        "lines": [
            {"description": "X", "quantity": "1", "unit_price": "10.00", "tax_rate": "0"}
        ],
    }
    res = client.post(
        "/api/v1/invoices", headers=_auth(demo["access_token"]), json=body
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "date_validation"


def test_tenant_cannot_read_other_org_invoice(client):
    demo = _login(client, "demo@invoiceai.local")
    other = _login(client, "other@otherco.local")
    supplier_id = _first_supplier_id(client, demo["access_token"])
    created = _create_invoice(
        client,
        demo["access_token"],
        supplier_id=supplier_id,
        invoice_number=f"M2-TEN-{uuid4().hex[:8]}",
    )
    assert created.status_code == 201
    inv_id = created.json()["id"]

    res = client.get(
        f"/api/v1/invoices/{inv_id}", headers=_auth(other["access_token"])
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "tenant_forbidden"


def test_supplier_crud_admin_and_tenant(client):
    demo = _login(client, "demo@invoiceai.local")
    other = _login(client, "other@otherco.local")
    code = f"M2S-{uuid4().hex[:6]}"
    create = client.post(
        "/api/v1/suppliers",
        headers=_auth(demo["access_token"]),
        json={"code": code, "name": "M2 Test Supplier", "email": "m2@example.com"},
    )
    assert create.status_code == 201, create.text
    sid = create.json()["id"]

    # other org cannot read
    forbidden = client.get(
        f"/api/v1/suppliers/{sid}", headers=_auth(other["access_token"])
    )
    assert forbidden.status_code == 403

    # staff cannot create
    staff = _login(client, "staff@invoiceai.local")
    denied = client.post(
        "/api/v1/suppliers",
        headers=_auth(staff["access_token"]),
        json={"code": f"NO-{uuid4().hex[:6]}", "name": "Nope"},
    )
    assert denied.status_code == 403


def test_approval_role_checked_and_audited(client):
    admin = _login(client, "demo@invoiceai.local")
    staff = _login(client, "staff@invoiceai.local")
    reviewer = _login(client, "reviewer@invoiceai.local")
    approver = _login(client, "approver@invoiceai.local")
    supplier_id = _first_supplier_id(client, admin["access_token"])

    created = _create_invoice(
        client,
        staff["access_token"],
        supplier_id=supplier_id,
        invoice_number=f"M2-APR-{uuid4().hex[:8]}",
        submit_for_review=True,
    )
    assert created.status_code == 201
    inv_id = created.json()["id"]
    assert created.json()["status"] == "needs_review"

    # staff cannot submit for approval
    staff_submit = client.post(
        f"/api/v1/invoices/{inv_id}/workflow",
        headers=_auth(staff["access_token"]),
        json={"action": "submit_approval"},
    )
    assert staff_submit.status_code == 403

    # reviewer can
    submit = client.post(
        f"/api/v1/invoices/{inv_id}/workflow",
        headers=_auth(reviewer["access_token"]),
        json={"action": "submit_approval"},
    )
    assert submit.status_code == 200, submit.text
    assert submit.json()["status"] == "pending_approval"

    # staff cannot approve
    staff_approve = client.post(
        "/api/v1/approvals",
        headers=_auth(staff["access_token"]),
        params={"invoice_id": inv_id},
        json={"decision": "approved", "comment": "nope"},
    )
    assert staff_approve.status_code == 403

    # approver can
    approve = client.post(
        "/api/v1/approvals",
        headers=_auth(approver["access_token"]),
        params={"invoice_id": inv_id},
        json={"decision": "approved", "comment": "Looks good"},
    )
    assert approve.status_code == 201, approve.text
    assert approve.json()["decision"] == "approved"

    get_inv = client.get(f"/api/v1/invoices/{inv_id}", headers=_auth(admin["access_token"]))
    assert get_inv.json()["status"] == "approved"


def test_reject_requires_reason(client):
    admin = _login(client, "demo@invoiceai.local")
    reviewer = _login(client, "reviewer@invoiceai.local")
    approver = _login(client, "approver@invoiceai.local")
    supplier_id = _first_supplier_id(client, admin["access_token"])

    created = _create_invoice(
        client,
        admin["access_token"],
        supplier_id=supplier_id,
        invoice_number=f"M2-REJ-{uuid4().hex[:8]}",
        submit_for_review=True,
    )
    inv_id = created.json()["id"]
    client.post(
        f"/api/v1/invoices/{inv_id}/workflow",
        headers=_auth(reviewer["access_token"]),
        json={"action": "submit_approval"},
    )
    res = client.post(
        "/api/v1/approvals",
        headers=_auth(approver["access_token"]),
        params={"invoice_id": inv_id},
        json={"decision": "rejected", "comment": ""},
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "rejection_reason_required"


def test_partial_and_full_payment_updates_balance(client):
    admin = _login(client, "demo@invoiceai.local")
    reviewer = _login(client, "reviewer@invoiceai.local")
    approver = _login(client, "approver@invoiceai.local")
    supplier_id = _first_supplier_id(client, admin["access_token"])

    created = _create_invoice(
        client,
        admin["access_token"],
        supplier_id=supplier_id,
        invoice_number=f"M2-PAY-{uuid4().hex[:8]}",
        submit_for_review=True,
    )
    inv_id = created.json()["id"]
    client.post(
        f"/api/v1/invoices/{inv_id}/workflow",
        headers=_auth(reviewer["access_token"]),
        json={"action": "submit_approval"},
    )
    client.post(
        "/api/v1/approvals",
        headers=_auth(approver["access_token"]),
        params={"invoice_id": inv_id},
        json={"decision": "approved", "comment": "OK"},
    )

    # partial: total 110, pay 40
    partial = client.post(
        "/api/v1/payments",
        headers=_auth(approver["access_token"]),
        json={
            "invoice_id": inv_id,
            "amount": "40.00",
            "payment_date": date.today().isoformat(),
            "method": "ach",
            "reference": "ACH-PARTIAL-1",
        },
    )
    assert partial.status_code == 201, partial.text
    assert partial.json()["invoice_status"] == "partially_paid"
    assert partial.json()["invoice_balance_due"] == "70.00"
    assert partial.json()["invoice_amount_paid"] == "40.00"

    # staff cannot pay
    staff = _login(client, "staff@invoiceai.local")
    denied = client.post(
        "/api/v1/payments",
        headers=_auth(staff["access_token"]),
        json={
            "invoice_id": inv_id,
            "amount": "10.00",
            "payment_date": date.today().isoformat(),
            "method": "ach",
        },
    )
    assert denied.status_code == 403

    # full remaining
    full = client.post(
        "/api/v1/payments",
        headers=_auth(admin["access_token"]),
        json={
            "invoice_id": inv_id,
            "amount": "70.00",
            "payment_date": date.today().isoformat(),
            "method": "wire",
            "reference": "WIRE-FULL",
        },
    )
    assert full.status_code == 201, full.text
    assert full.json()["invoice_status"] == "paid"
    assert full.json()["invoice_balance_due"] == "0.00"

    # overpay rejected
    over = client.post(
        "/api/v1/payments",
        headers=_auth(admin["access_token"]),
        json={
            "invoice_id": inv_id,
            "amount": "1.00",
            "payment_date": date.today().isoformat(),
            "method": "ach",
        },
    )
    assert over.status_code in (409, 422)
