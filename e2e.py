import logging
import os

import frappe

_logger = logging.getLogger(__name__)

def run():
    results = []
    def check(name, ok, detail=""):
        results.append(ok)
        print(("PASS  " if ok else "FAIL  ") + name + ((" -> " + detail) if detail and not ok else ""))

    for name, ar, ptype, amt, rate, term in [
        ("Home Loan", "قرض العقار", "Financing", 1000000, 4.25, 240),
        ("Asset Finance", "تمويل الأصول", "Financing", 500000, 3.5, 60),
        ("Investment", "الاستثمار", "Investment", 5000000, 5.0, 120),
        ("Savings", "الادخار", "Savings", 1000000, 2.5, 60)]:
        if not frappe.db.exists("Financial Product", name):
            frappe.get_doc({"doctype": "Financial Product", "product_name": name,
                "product_name_ar": ar, "product_type": ptype, "max_amount": amt,
                "interest_rate": rate, "term_months": term}).insert()
    check("Seed 4 financial products", frappe.db.count("Financial Product") >= 4)

    cg = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
    if not cg:
        frappe.get_doc({"doctype": "Customer Group", "customer_group_name": "Individual",
            "parent_customer_group": "All Customer Groups"}).insert()
        cg = "Individual"
    terr = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"
    if not frappe.db.exists("Customer", {"customer_name": "Ahmed Al-Suwaiyan"}):
        frappe.get_doc({"doctype": "Customer", "customer_name": "Ahmed Al-Suwaiyan",
            "customer_type": "Individual", "customer_group": cg, "territory": terr}).insert()
    cust = frappe.db.get_value("Customer", {"customer_name": "Ahmed Al-Suwaiyan"})
    check("Seed customer Ahmed Al-Suwaiyan", bool(cust))

    app = frappe.get_doc({"doctype": "Financing Application", "customer": cust,
        "product": "Home Loan", "amount": 400000, "status": "Submitted"}).insert()
    check("Create application SAR 400K", app.name.startswith("APP-"))

    try:
        frappe.get_doc({"doctype": "Financing Application", "customer": cust,
            "product": "Home Loan", "amount": 10000}).insert()
        check("Reject below-min amount (10K)", False, "was accepted!")
    except frappe.ValidationError as exc:
        _logger.debug("Expected rejection for low amount", exc_info=exc)
        check("Reject below-min amount (10K)", True)

    try:
        app.status = "Disbursed"
        app.save()
        check("Block disburse before approve", False, "was allowed!")
    except frappe.ValidationError as exc:
        _logger.debug("Expected rejection for premature disburse", exc_info=exc)
        check("Block disburse before approve", True)
        app.reload()

    app.status = "Approved"; app.save()
    check("Approve auto-sets approval_date", bool(app.approval_date))
    app.status = "Disbursed"; app.save()
    check("Disburse auto-sets disbursement_date", bool(app.disbursement_date))

    pay = frappe.get_doc({"doctype": "Payment Transaction", "application": app.name,
        "amount": 15000, "method": "Bank Transfer", "status": "Completed"}).insert()
    check("Payment TXN reference auto-generated", (pay.gateway_reference or "").startswith("TXN-"))

    frappe.db.commit()

    user = frappe.get_doc("User", "Administrator")
    if not user.api_key:
        user.api_key = frappe.generate_hash(length=15)
    secret = frappe.generate_hash(length=15)
    user.api_secret = secret
    user.save(ignore_permissions=True)
    frappe.db.commit()

    # Write credentials to a private, non-committed file rather than stdout -
    # this script's output is routinely captured into shared logs/terminal
    # pastes (see fix-and-test.sh), and these rotate the Administrator's
    # live API secret on every run.
    creds_path = frappe.get_site_path("private", "files", "fikak_e2e_api_credentials.txt")
    with open(creds_path, "w") as f:
        f.write(f"API_KEY={user.api_key}\nAPI_SECRET={secret}\n")
    os.chmod(creds_path, 0o600)

    print("")
    print("RESULTS: %d/%d passed" % (sum(results), len(results)))
    print("")
    print("REST API CREDENTIALS (rotated on Administrator - do not paste these into shared logs):")
    print(f"  Retrieve with: cat {creds_path}")
