import frappe


def execute():
    """
    fikak_app.api stores a full JWT (well over 140 chars) in the core
    OAuth Bearer Token DocType's access_token field, which defaults to a
    Data field (140-char varchar). Without this, token generation
    silently truncated the JWT to fit, producing an invalid/unverifiable
    token. Widen the field to Text so the full token can be persisted.
    """
    frappe.reload_doctype("OAuth Bearer Token")
    frappe.make_property_setter(
        {
            "doctype": "OAuth Bearer Token",
            "fieldname": "access_token",
            "property": "fieldtype",
            "value": "Text",
            "property_type": "Select",
        },
        validate_fields_for_doctype=False,
    )
    frappe.reload_doctype("OAuth Bearer Token")
