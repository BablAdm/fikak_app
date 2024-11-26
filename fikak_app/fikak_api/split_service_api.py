import frappe


@frappe.whitelist(methods=['POST'])
def create_evaluation_request(deed_id):
    try:
        if frappe.db.exists("Evaluation Request", {"deed": deed_id, "status": "Pending"}):
            frappe.local.response.http_status_code = 400
            return {
                "status": False,
                "message": "An active evaluation request already exists for this deed"
            }
        deed = frappe.get_doc("WATHEQ Deed", deed_id)
        if deed.deed_owner != frappe.session.user:
            frappe.local.response.http_status_code = 404
            return {
                "status": False,
                "message": "You are not authorized to create an evaluation request for this deed"
            }
        current_request = get_active_deed_request(deed_id)
        if not current_request:
            frappe.local.response.http_status_code = 400
            return {
                "status": False,
                "message": "No active request found for this deed"
            }
        split_service_request = create_split_service_request(deed_id , current_request[0])

        evaluation_request = frappe.get_doc({
            "doctype": "Evaluation Request",
            "requester": frappe.session.user,
            "request" : split_service_request.name,
            "deed": deed_id,
            "submission_date": frappe.utils.now_datetime(),
            "evaluation_source" : "Split Service Request",
            "status": "Pending"
        })
        evaluation_request.insert(ignore_permissions=True)
        frappe.db.commit()
        return {
            "status": True,
            "message": "Evaluation request created successfully"
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "status": False,
            "message": str(e)
        }
    
def get_active_deed_request(deed_id):
    return frappe.get_all("Eligibility Check Request Deed Item", {"deed": deed_id, "status": "Eligible For Split" , "is_active" : 1},["parent"] ,pluck = "parent",  order_by="creation desc" , limit=1)


def create_split_service_request(deed_id , eligibility_check_request):
    split_service_request = frappe.get_doc({
        "doctype": "Split Service Request",
        "requester": frappe.session.user,
        "deed": deed_id,
        "submission_date": frappe.utils.now_datetime(),
        "status": "Pending",
        "eligibility_check_request" : eligibility_check_request
    })
    split_service_request.insert(ignore_permissions=True)
    frappe.db.commit()
    return split_service_request