"""
Seed Invoice AI demo data (fictional only).

Creates:
- 2 organizations (demo + tenant-isolation org)
- Users across Admin/Finance Manager, Reviewer, Approver, Staff
- 10 suppliers (demo org)
- 25 invoices with line items
- Duplicate + anomaly examples
- Varied payment states

Usage (from backend/):
  python -m scripts.seed
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

# Allow `python scripts/seed.py` from backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import delete, select

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import (
    AccountingCategory,
    ApprovalStep,
    AuditEvent,
    Invoice,
    InvoiceDocument,
    InvoiceLine,
    InvoiceReview,
    Organization,
    Payment,
    PurchaseOrderReference,
    Supplier,
    User,
)
from app.models.enums import (
    ApprovalDecision,
    InvoiceStatus,
    PaymentMethod,
    ReviewFlag,
    UserRole,
)

DEMO_PASSWORD = "demo"
TODAY = date(2026, 11, 26)


SUPPLIER_DEFS = [
    ("SUP-001", "Northwind Office Supply", "ap@northwind-demo.example", "ACH *4421"),
    ("SUP-002", "Contoso Freight LLC", "billing@contoso-freight.example", "Wire Contoso"),
    ("SUP-003", "Fabrikam Cleaning Co", "invoices@fabrikam-clean.example", "ACH *8890"),
    ("SUP-004", "Adventure Works Soft", "ar@adventureworks-soft.example", "ACH *1102"),
    ("SUP-005", "Tailspin Utilities", "payments@tailspin-util.example", "ACH *5566"),
    ("SUP-006", "Wide World Packaging", "ap@wwpack.example", "Check WW Pack"),
    ("SUP-007", "Litware Cloud Hosting", "billing@litware-cloud.example", "ACH *7788"),
    ("SUP-008", "Blue Yonder Catering", "orders@blueyonder-cater.example", "ACH *3344"),
    ("SUP-009", "Alpine HVAC Parts", "sales@alpine-hvac.example", "Wire Alpine"),
    ("SUP-010", "Sunrise Print Shop", "hello@sunrise-print.example", "ACH *2211"),
]


def _money(value: str | float | int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def clear_demo_data(db) -> None:
    """Idempotent wipe of seedable tables (dev only)."""
    for model in (
        AuditEvent,
        Payment,
        ApprovalStep,
        InvoiceReview,
        InvoiceDocument,
        InvoiceLine,
        Invoice,
        PurchaseOrderReference,
        AccountingCategory,
        Supplier,
        User,
        Organization,
    ):
        db.execute(delete(model))
    db.commit()


def seed() -> None:
    db = SessionLocal()
    try:
        clear_demo_data(db)

        demo_org = Organization(name="Acme Payables Demo", slug="acme-payables")
        other_org = Organization(name="Other Co Isolation", slug="other-co")
        db.add_all([demo_org, other_org])
        db.flush()

        users = [
            User(
                organization_id=demo_org.id,
                email="demo@invoiceai.local",
                full_name="Dana Finance",
                hashed_password=hash_password(DEMO_PASSWORD),
                role=UserRole.ADMIN,
            ),
            User(
                organization_id=demo_org.id,
                email="reviewer@invoiceai.local",
                full_name="Riley Reviewer",
                hashed_password=hash_password(DEMO_PASSWORD),
                role=UserRole.REVIEWER,
            ),
            User(
                organization_id=demo_org.id,
                email="approver@invoiceai.local",
                full_name="Avery Approver",
                hashed_password=hash_password(DEMO_PASSWORD),
                role=UserRole.APPROVER,
            ),
            User(
                organization_id=demo_org.id,
                email="staff@invoiceai.local",
                full_name="Sam Staff",
                hashed_password=hash_password(DEMO_PASSWORD),
                role=UserRole.STAFF,
            ),
            User(
                organization_id=other_org.id,
                email="other@otherco.local",
                full_name="Olivia Other",
                hashed_password=hash_password(DEMO_PASSWORD),
                role=UserRole.ADMIN,
            ),
        ]
        db.add_all(users)
        db.flush()
        admin, reviewer, approver, staff, other_admin = users

        categories = [
            AccountingCategory(
                organization_id=demo_org.id,
                code="OFFICE",
                name="Office Supplies",
                description="Stationery and consumables",
            ),
            AccountingCategory(
                organization_id=demo_org.id,
                code="UTIL",
                name="Utilities",
                description="Power, water, telecom",
            ),
            AccountingCategory(
                organization_id=demo_org.id,
                code="SOFT",
                name="Software & SaaS",
                description="Subscriptions and licenses",
            ),
            AccountingCategory(
                organization_id=demo_org.id,
                code="LOGISTICS",
                name="Freight & Logistics",
            ),
        ]
        db.add_all(categories)
        db.flush()

        suppliers: list[Supplier] = []
        for code, name, email, pay in SUPPLIER_DEFS:
            suppliers.append(
                Supplier(
                    organization_id=demo_org.id,
                    code=code,
                    name=name,
                    email=email,
                    payment_details=pay,
                )
            )
        db.add_all(suppliers)
        db.flush()

        # Isolation org gets one supplier so tenant tests have contrast
        other_supplier = Supplier(
            organization_id=other_org.id,
            code="OTH-001",
            name="Other Co Only Vendor",
            email="vendor@otherco.example",
            payment_details="ACH *9999",
        )
        db.add(other_supplier)
        db.flush()

        po_refs = [
            PurchaseOrderReference(
                organization_id=demo_org.id,
                po_number="PO-2026-0101",
                supplier_id=suppliers[0].id,
                amount=_money("1200.00"),
            ),
            PurchaseOrderReference(
                organization_id=demo_org.id,
                po_number="PO-2026-0144",
                supplier_id=suppliers[3].id,
                amount=_money("4800.00"),
            ),
            PurchaseOrderReference(
                organization_id=demo_org.id,
                po_number="PO-2026-0200",
                supplier_id=suppliers[6].id,
                amount=_money("990.00"),
            ),
        ]
        db.add_all(po_refs)
        db.flush()

        # Invoice blueprints: (supplier_idx, number, days_ago, due_in, status,
        #   lines[(desc, qty, unit, tax_rate)], paid, flags, notes, cat_idx, po)
        blueprints: list[dict] = []

        # 20 "normal" varied invoices
        catalog = [
            ("Paper ream case", "12", "24.50", "0.08"),
            ("Freight lane A", "1", "450.00", "0.00"),
            ("Monthly cleaning", "1", "875.00", "0.05"),
            ("License seats", "10", "49.00", "0.00"),
            ("Electricity Nov", "1", "612.40", "0.00"),
            ("Corrugated boxes", "50", "3.25", "0.08"),
            ("Hosting plan Pro", "1", "299.00", "0.00"),
            ("Catering lunch", "25", "18.00", "0.08"),
            ("Filter kit", "4", "85.00", "0.08"),
            ("Business cards", "500", "0.12", "0.08"),
        ]
        statuses_cycle = [
            InvoiceStatus.NEEDS_REVIEW,
            InvoiceStatus.PENDING_APPROVAL,
            InvoiceStatus.APPROVED,
            InvoiceStatus.PARTIALLY_PAID,
            InvoiceStatus.PAID,
            InvoiceStatus.UPLOADED,
            InvoiceStatus.PROCESSING,
            InvoiceStatus.APPROVED,
            InvoiceStatus.PAID,
            InvoiceStatus.REJECTED,
        ]
        for i in range(20):
            qty = Decimal(catalog[i % 10][1])
            unit = _money(catalog[i % 10][2])
            tax_rate = Decimal(catalog[i % 10][3])
            base = (qty * unit).quantize(Decimal("0.01"))
            tax = (base * tax_rate).quantize(Decimal("0.01"))
            total = (base + tax).quantize(Decimal("0.01"))
            status = statuses_cycle[i % len(statuses_cycle)]
            if status == InvoiceStatus.PAID:
                paid = total
            elif status == InvoiceStatus.PARTIALLY_PAID:
                paid = (total * Decimal("0.40")).quantize(Decimal("0.01"))
            else:
                paid = _money("0")
            blueprints.append(
                {
                    "supplier_idx": i % 10,
                    "number": f"INV-2026-{1000 + i}",
                    "days_ago": 5 + i * 3,
                    "due_in": 15 if i % 3 else -5,  # some overdue
                    "status": status,
                    "lines": [catalog[i % 10]],
                    "paid": paid,
                    "dup": False,
                    "anomaly": False,
                    "notes": None,
                    "cat_idx": i % 4,
                    "po": po_refs[i % 3].po_number if i % 4 == 0 else None,
                    "po_id": po_refs[i % 3].id if i % 4 == 0 else None,
                }
            )

        # Exact duplicate pair (same supplier + number) — M2 validation flags these
        blueprints.append(
            {
                "supplier_idx": 0,
                "number": "INV-DUP-5500",
                "days_ago": 12,
                "due_in": 18,
                "status": InvoiceStatus.NEEDS_REVIEW,
                "lines": [("Duplicate paper run A", "10", "20.00", "0.08")],
                "paid": _money("0"),
                "dup": True,
                "anomaly": False,
                "notes": "Duplicate of INV-DUP-5500 (same supplier + number)",
                "cat_idx": 0,
                "po": None,
                "po_id": None,
            }
        )
        blueprints.append(
            {
                "supplier_idx": 0,
                "number": "INV-DUP-5500",
                "days_ago": 11,
                "due_in": 19,
                "status": InvoiceStatus.UPLOADED,
                "lines": [("Duplicate paper run B", "10", "20.00", "0.08")],
                "paid": _money("0"),
                "dup": True,
                "anomaly": False,
                "notes": "Second capture of INV-DUP-5500 — duplicate example",
                "cat_idx": 0,
                "po": None,
                "po_id": None,
            }
        )

        # Anomaly: total/tax discrepancy (header total != line math)
        blueprints.append(
            {
                "supplier_idx": 4,
                "number": "INV-ANOM-TAX-01",
                "days_ago": 8,
                "due_in": 10,
                "status": InvoiceStatus.NEEDS_REVIEW,
                "lines": [("Utility anomaly bill", "1", "500.00", "0.10")],
                "paid": _money("0"),
                "dup": False,
                "anomaly": True,
                "notes": "Header total inflated vs line math (tax discrepancy signal)",
                "cat_idx": 1,
                "po": None,
                "po_id": None,
                "force_total": _money("650.00"),  # lines would be 550.00
                "force_tax": _money("50.00"),
                "force_subtotal": _money("500.00"),
            }
        )

        # Anomaly: unusual supplier amount vs peers
        blueprints.append(
            {
                "supplier_idx": 7,
                "number": "INV-ANOM-AMT-02",
                "days_ago": 4,
                "due_in": 20,
                "status": InvoiceStatus.PENDING_APPROVAL,
                "lines": [("Executive catering event", "1", "12500.00", "0.08")],
                "paid": _money("0"),
                "dup": False,
                "anomaly": True,
                "notes": "Amount far above typical catering invoices for this supplier",
                "cat_idx": 0,
                "po": None,
                "po_id": None,
            }
        )

        # Anomaly: changed payment details signal (noted; rules in M3)
        blueprints.append(
            {
                "supplier_idx": 2,
                "number": "INV-ANOM-PAY-03",
                "days_ago": 6,
                "due_in": 14,
                "status": InvoiceStatus.NEEDS_REVIEW,
                "lines": [("Deep clean package", "1", "920.00", "0.05")],
                "paid": _money("0"),
                "dup": False,
                "anomaly": True,
                "notes": "Supplier remittance account differs from directory payment_details",
                "cat_idx": 0,
                "po": None,
                "po_id": None,
            }
        )

        assert len(blueprints) == 25

        invoices: list[Invoice] = []
        for bp in blueprints:
            lines_raw = bp["lines"]
            computed_sub = _money("0")
            computed_tax = _money("0")
            line_rows = []
            for ln, (desc, qty_s, unit_s, tax_s) in enumerate(lines_raw, start=1):
                qty = Decimal(qty_s)
                unit = _money(unit_s)
                tax_rate = Decimal(tax_s)
                base = (qty * unit).quantize(Decimal("0.01"))
                tax = (base * tax_rate).quantize(Decimal("0.01"))
                lt = (base + tax).quantize(Decimal("0.01"))
                computed_sub += base
                computed_tax += tax
                line_rows.append((ln, desc, qty, unit, tax_rate, lt))

            subtotal = bp.get("force_subtotal", computed_sub)
            tax_total = bp.get("force_tax", computed_tax)
            total = bp.get("force_total", (subtotal + tax_total).quantize(Decimal("0.01")))
            paid = bp["paid"]
            balance = (total - paid).quantize(Decimal("0.01"))
            inv_date = TODAY - timedelta(days=bp["days_ago"])
            due = inv_date + timedelta(days=bp["due_in"])

            inv = Invoice(
                organization_id=demo_org.id,
                supplier_id=suppliers[bp["supplier_idx"]].id,
                invoice_number=bp["number"],
                invoice_date=inv_date,
                due_date=due,
                currency="USD",
                subtotal=subtotal,
                tax_total=tax_total,
                total=total,
                amount_paid=paid,
                balance_due=balance,
                po_reference=bp.get("po"),
                purchase_order_reference_id=bp.get("po_id"),
                terms="Net 30",
                status=bp["status"],
                accounting_category_id=categories[bp["cat_idx"]].id,
                has_duplicate_warning=bp["dup"],
                has_anomaly_signal=bp["anomaly"],
                anomaly_notes=bp["notes"],
                created_by_id=staff.id,
            )
            db.add(inv)
            db.flush()
            invoices.append(inv)

            for ln, desc, qty, unit, tax_rate, lt in line_rows:
                db.add(
                    InvoiceLine(
                        organization_id=demo_org.id,
                        invoice_id=inv.id,
                        line_number=ln,
                        description=desc,
                        quantity=qty,
                        unit_price=unit,
                        tax_rate=tax_rate,
                        line_total=lt,
                    )
                )

            # Sample OCR text for extract demos (unverified until user review)
            sample_ocr = None
            if bp["number"] in ("INV-2026-1000", "INV-ANOM-TAX-01", "INV-ANOM-PAY-03"):
                line0 = bp["lines"][0]
                sample_ocr = (
                    f"Supplier: {suppliers[bp['supplier_idx']].name}\n"
                    f"Invoice Number: {bp['number']}\n"
                    f"Invoice Date: {inv_date.isoformat()}\n"
                    f"Due Date: {due.isoformat()}\n"
                    f"PO: {bp.get('po') or 'PO-2026-0101'}\n"
                    f"Description: {line0[0]}\n"
                    f"{line0[0]} x {line0[1]} @ ${line0[2]} tax {float(line0[3])*100:.0f}%\n"
                    f"Subtotal: ${subtotal}\n"
                    f"Tax: ${tax_total}\n"
                    f"Total: ${total}\n"
                    f"Currency: USD\n"
                )
                if bp["number"] == "INV-ANOM-PAY-03":
                    sample_ocr += "Remit to: ACH *0000 NEW ACCOUNT\n"

            db.add(
                InvoiceDocument(
                    organization_id=demo_org.id,
                    invoice_id=inv.id,
                    filename=f"{bp['number']}.pdf",
                    content_type="application/pdf",
                    storage_path=f"demo/{demo_org.slug}/{bp['number']}.pdf",
                    byte_size=12_345,
                    ocr_text=sample_ocr,
                )
            )

            if bp["status"] in (
                InvoiceStatus.NEEDS_REVIEW,
                InvoiceStatus.PENDING_APPROVAL,
            ) or bp["dup"] or bp["anomaly"]:
                flag = ReviewFlag.NONE
                if bp["dup"]:
                    flag = ReviewFlag.DUPLICATE
                elif bp["anomaly"]:
                    flag = ReviewFlag.ANOMALY
                db.add(
                    InvoiceReview(
                        organization_id=demo_org.id,
                        invoice_id=inv.id,
                        reviewer_id=reviewer.id if bp["status"] != InvoiceStatus.UPLOADED else None,
                        flag=flag,
                        notes=bp["notes"] or "Seeded review flag",
                        is_resolved=False,
                    )
                )

            if bp["status"] in (
                InvoiceStatus.APPROVED,
                InvoiceStatus.PARTIALLY_PAID,
                InvoiceStatus.PAID,
                InvoiceStatus.REJECTED,
                InvoiceStatus.PENDING_APPROVAL,
            ):
                decision = ApprovalDecision.PENDING
                comment = None
                decided_at = None
                if bp["status"] == InvoiceStatus.REJECTED:
                    decision = ApprovalDecision.REJECTED
                    comment = "Rejected in seed: missing PO match"
                    decided_at = inv_date + timedelta(days=1)
                elif bp["status"] != InvoiceStatus.PENDING_APPROVAL:
                    decision = ApprovalDecision.APPROVED
                    comment = "Approved in seed"
                    decided_at = inv_date + timedelta(days=1)
                db.add(
                    ApprovalStep(
                        organization_id=demo_org.id,
                        invoice_id=inv.id,
                        step_order=1,
                        approver_id=approver.id,
                        decision=decision,
                        comment=comment,
                        decided_at=decided_at,
                    )
                )

            if paid > 0:
                db.add(
                    Payment(
                        organization_id=demo_org.id,
                        invoice_id=inv.id,
                        amount=paid,
                        payment_date=inv_date + timedelta(days=3),
                        method=PaymentMethod.ACH,
                        reference=f"PMT-{bp['number']}",
                        recorded_by_id=approver.id,
                    )
                )

            db.add(
                AuditEvent(
                    organization_id=demo_org.id,
                    actor_id=admin.id,
                    entity_type="invoice",
                    entity_id=inv.id,
                    action="seed_created",
                    details={"invoice_number": bp["number"], "status": bp["status"].value},
                )
            )

        # One invoice on other org for tenant isolation
        other_inv = Invoice(
            organization_id=other_org.id,
            supplier_id=other_supplier.id,
            invoice_number="OTH-INV-1",
            invoice_date=TODAY - timedelta(days=2),
            due_date=TODAY + timedelta(days=28),
            currency="USD",
            subtotal=_money("100.00"),
            tax_total=_money("0"),
            total=_money("100.00"),
            amount_paid=_money("0"),
            balance_due=_money("100.00"),
            status=InvoiceStatus.APPROVED,
            created_by_id=other_admin.id,
        )
        db.add(other_inv)
        db.flush()
        db.add(
            InvoiceLine(
                organization_id=other_org.id,
                invoice_id=other_inv.id,
                line_number=1,
                description="Other org only line",
                quantity=Decimal("1"),
                unit_price=_money("100.00"),
                tax_rate=Decimal("0"),
                line_total=_money("100.00"),
            )
        )

        db.commit()

        from sqlalchemy import func

        demo_inv = db.scalar(
            select(func.count()).select_from(Invoice).where(
                Invoice.organization_id == demo_org.id
            )
        )
        demo_sup = db.scalar(
            select(func.count()).select_from(Supplier).where(
                Supplier.organization_id == demo_org.id
            )
        )

        print("Invoice AI seed complete (fictional data).")
        print(f"  Demo org: {demo_org.name} ({demo_org.slug})")
        print(f"  Suppliers: {demo_sup}")
        print(f"  Invoices:  {demo_inv}")
        print("  Demo credentials (password for all: demo):")
        print("    demo@invoiceai.local      — admin (Finance Manager)")
        print("    reviewer@invoiceai.local  — reviewer")
        print("    approver@invoiceai.local  — approver")
        print("    staff@invoiceai.local     — staff")
        print("    other@otherco.local       — admin (Other Co Isolation)")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    seed()


if __name__ == "__main__":
    main()
