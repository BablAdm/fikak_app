

import frappe

def insert_new_lba_request(deed_id):
    # Insert a new LBA request
    deed = frappe.get_doc("WATHEQ Deed", deed_id)
    lba_source = check_lba_source(deed)
    data = {
        "doctype" : "Loan Service Request",
        "requester" : frappe.session.user,
        "deed" : deed_id,
        "source" : lba_source["source"],
        "split_service_request" : lba_source["split_request"],
        "is_active" : 1,
        "submission_date" : frappe.utils.now_datetime(),
    }
    if lba_source["split_request"]:
        split_service_doc = frappe.get_doc("Split Service Request" , lba_source["split_request"])
        data["current_market_deed_price"] = split_service_doc.current_market_deed_price
        data["bank_equity"] = split_service_doc.bank_equity
        data["customer_equity"] = split_service_doc.customer_equity
        data["status"] = "Eligible For Loan"

    lba_request = frappe.get_doc(data)
    lba_request.insert(ignore_permissions=True)
    return lba_request


def check_lba_source(deed):
    if not deed.is_real_estate_mortgaged:
        return {
            "split_request" : None,
            "source": "Free Deed" 
        }
    split_request = frappe.db.exists("Split Service Request" , {"deed" : deed.name , "status" : "Accepted"})
    if split_request:
        return {
            "split_request" : split_request,
            "source": "Split Mortgage" 
        }

    return None

def create_split_service_request(deed_id , eligibility_check_request):
    split_service_request = frappe.get_doc({
        "doctype": "Loan Service Request",
        "requester": frappe.session.user,
        "deed": deed_id,
        "submission_date": frappe.utils.now_datetime(),
        "status": "Pending",
        "eligibility_check_request" : eligibility_check_request
    })
    split_service_request.insert(ignore_permissions=True)
    frappe.db.commit()
    return split_service_request

def get_lba_evaluation_by_split_service(split_service_request ):
    return frappe.get_doc("Evaluation Request" , {"request" : split_service_request, "source" : "Split Service Request"})

