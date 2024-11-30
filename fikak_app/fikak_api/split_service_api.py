import frappe

from frappe import _

@frappe.whitelist(methods=['GET'])
def get_deed_split_service_status(deed_id):
    try:
        deed = frappe.get_doc("WATHEQ Deed", deed_id)
        if deed.deed_owner != frappe.session.user:
            frappe.local.response.http_status_code = 404
            return {
                "status": False,
                "message": "You are not authorized to view this deed"
            }
        try:
            split_service_request = frappe.get_doc("Split Service Request", {"deed": deed_id, "requester": frappe.session.user})
            evaluation_request = frappe.get_doc("Evaluation Request", {"request" : split_service_request.name})
            return {
                "status": True,
                "data" : {
                    "split_service_status" : split_service_request.status,
                    "split_service_request" : split_service_request.name,
                    "evaluation_request_status" : evaluation_request.status,
                    "evaluation_request" : evaluation_request.name
                },
                "message": "Split service request retrieved successfully"
            }
        except frappe.DoesNotExistError:
            return {
                "status": False,
                "data" : {
                    "split_service_status" : False, 
                    "split_service_request" : False,
                    "evaluation_request_status" : False,
                    "evaluation_request" : False

                },
                "message": "No split service request found for this deed"
            }
        
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "status": False,
            "message": str(e)
        }


@frappe.whitelist(methods=['POST'])
def create_evaluation_request(deed_id):
    try:
        if frappe.db.exists("Evaluation Request", {"deed": deed_id, "status": "Pending"}):
            return {
                "status": True,
                "message": "An active evaluation request already exists for this deed"
            }
        deed = frappe.get_doc("WATHEQ Deed", deed_id)
        if deed.deed_owner != frappe.session.user:
            frappe.local.response.http_status_code = 404
            return {
                "status": False,
                "message": "You are not authorized to create an evaluation request for this deed"
            }
        current_request = get_active_deed_eligibility_request(deed_id)
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
    
def get_active_deed_eligibility_request(deed_id):
    return frappe.get_all("Eligibility Check Request Deed Item", {"deed": deed_id, "status": "Eligible For Split" , "is_active" : 1},["parent"] ,pluck = "parent",  order_by="creation desc" , limit=1)

def get_deed_active_split_service_request(deed_id):
    return frappe.get_all("Split Service Request", {"deed": deed_id},["name"], pluck="name", order_by="creation desc", limit=1)

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



@frappe.whitelist(methods=['GET'])
def get_split_service_result(split_service_request_id):
    try:
        
        split_service_request = frappe.get_doc("Split Service Request", split_service_request_id).as_dict()
        
        if frappe.session.user != split_service_request.requester:
            frappe.local.response.http_status_code = 404
            return {
                "status": False,
                "message": _("You are not authorized to view this split service request")
            }
        deed_doc = frappe.get_doc("WATHEQ Deed", split_service_request.deed).as_dict()
        # split_service_request["deed_details"] = deed_doc.as_dict()
        # current_mortgage =(deed_doc.deed_price + deed_doc.interest_amount - deed_doc.down_price)  - (split_service_request.total_interest_payment + split_service_request.total_principal_payment)
        # split_service_request["current_mortgage"] = current_mortgage
        # split_service_request["per_month"] = round(split_service_request.new_loan / 30 / 12 , 2)
        data = [
            {
                "deed_id" : deed_doc.name,
                "deed_number" : deed_doc.deed_number,
                "deed_serial" : deed_doc.deed_serial,
                "deed_area" : deed_doc.deed_area,
                # "deed_status" : deed_doc.status,
                "last_price_registred" : deed_doc.deed_price,
                "is_real_estate_mortgaged" : deed_doc.is_real_estate_mortgaged,
                "deed_city" : deed_doc.real_estate_details[0]["city_name"],
                "deed_region" : deed_doc.real_estate_details[0]["region_name"],
                "status" : "Eligible For Split" if split_service_request.split_eligibility else "Not Eligible",
                "split_eligibility" : split_service_request.split_eligibility,
                "bursa_price" : split_service_request.current_market_deed_price,
                "equity_percent" : split_service_request.customer_equity,
                "loan_amount" : split_service_request.new_loan
            }
        ]
        return {
            "status": True,
            "data" : data,
            "meta": {
                "current_page": 1,
                "total_items": 1,
                "items_per_page": 1,
                "total_pages": 1
            },
            "message": _("Split service request retrieved successfully")
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "status": False,
            "message": str(e)
        }