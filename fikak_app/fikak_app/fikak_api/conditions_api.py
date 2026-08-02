import frappe
from frappe import _


def _get_active_terms():
    """Returns the single enabled Terms And Conditions doc, or None."""
    terms = frappe.get_all("Terms And Conditions", filters={"enabled": 1}, fields=["name"], limit=1)
    if not terms:
        return None
    return frappe.get_doc("Terms And Conditions", terms[0].name)


@frappe.whitelist()
def get_terms_and_conditions():
    """
    Returns the currently active (enabled=1) Terms And Conditions document.
    Matches src/views/pages/terms-and-conditions/index.jsx, which expects
    {message: {data: {name, title, conditions}}}.
    """
    terms = _get_active_terms()
    if not terms:
        frappe.throw(_("No active Terms And Conditions are configured"))

    return {"data": {
        "name": terms.name,
        "title": terms.title,
        "conditions": terms.conditions,
    }}


@frappe.whitelist()
def submit_conditions(terms_and_conditions):
    """
    Records that the current session user accepted the given Terms And
    Conditions version. Matches
    src/services/terms_and_conditions/useSubmitTermsAndConditions.jsx,
    which posts {terms_and_conditions: <name>}.

    Idempotent: re-accepting the same version doesn't create duplicate
    rows, it just returns the existing acceptance record.
    """
    if not frappe.db.exists("Terms And Conditions", terms_and_conditions):
        frappe.throw(_("Unknown Terms And Conditions: {0}").format(terms_and_conditions))

    user = frappe.session.user

    existing = frappe.db.exists("Terms Acceptance", {
        "user": user,
        "terms_and_conditions": terms_and_conditions,
    })

    if existing:
        return {"status": "success", "message": _("Terms already accepted"), "name": existing}

    acceptance = frappe.get_doc({
        "doctype": "Terms Acceptance",
        "user": user,
        "terms_and_conditions": terms_and_conditions,
        "accepted_on": frappe.utils.now_datetime(),
        "ip_address": frappe.local.request_ip if frappe.local.request_ip else None,
    })
    acceptance.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"status": "success", "message": _("Terms accepted"), "name": acceptance.name}
