

import frappe

@frappe.whitelist(methods="GET")
def get_terms_and_conditions(type = "General"):
    conditions = frappe.get_all("Terms And Conditions" , fields=["name", "title", "conditions" , "type"] , filters={"enabled": 1 , "type" : type})
    if conditions:
        return {
            "status": 200,
            "message": "Success",
            "data": conditions[0]
        }
    else:
        return {
            "status": 404,
            "message": "No conditions found",
            "data": {}
        }
    
@frappe.whitelist(methods="POST")
def submit_conditions(terms_and_conditions , deed_id = None):
    filters = {"terms_and_conditions": terms_and_conditions , "user": frappe.session.user}
    if deed_id:
        filters["deed_id"] = deed_id

    if frappe.db.exists("Terms And Conditions Submission", filters):
        frappe.local.response.http_status_code = 200
        return {
            "status": True,
            "message": "Submitted"
        }

    frappe.get_doc({
        "doctype": "Terms And Conditions Submission",
        "terms_and_conditions": terms_and_conditions,
        "user": frappe.session.user,
        "deed_id": deed_id
    }).insert(ignore_permissions=True)
    return {
        "status": True,
        "message": "Success"
    }
    