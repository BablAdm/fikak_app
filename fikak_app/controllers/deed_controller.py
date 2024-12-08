
import frappe
from frappe.utils import now


def update_deed_workflow(deed_name ,service, status):
    """
    Update the 'Deed' Doctype based on changes in 'Eligibility Check Request Deed Item'
    """	
	## 1. get deed doctype
    deed_dt = frappe.get_doc("WATHEQ Deed", deed_name)

    if not deed_dt:
        frappe.throw(f"Deed with name '{deed_name}' not found.")

    # 2.Update the Deed status and services
    deed_dt.service_status = status
    deed_dt.service = service

    # 3. Add a new entry to the Watheq Deed Status Item table
    deed_dt.append("statuses", {
        "submission_date": now(),
        "service": service,
        "status": status
    })

    # Save the changes to the Deed Doctype
    deed_dt.save(ignore_permissions=True)
