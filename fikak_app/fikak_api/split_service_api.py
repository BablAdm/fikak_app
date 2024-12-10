import frappe

from frappe import _
from fikak_app.utils.global_utils import translate 
from pypika import functions as fn
import math

from fikak_app.external_requests.split_service_requests import call_split_bank_request_api

@frappe.whitelist(methods=["GET"])
def get_split_requests_list(global_filter = None , filter_by_request = None , offset = 0 , page_size = 10 , order_direction = -1 , order_by = "creation" , **kw):
    
    
    if isinstance(offset, str):
        offset = int(offset)
    
    if isinstance(page_size, str):
        page_size = int(page_size)

    watheq_deed_dt = frappe.qb.DocType("WATHEQ Deed")
    split_service_dt = frappe.qb.DocType("Split Service Request")
    deed_real_estate_details_dt = frappe.qb.DocType("WATHEQ Real Estate Details Item")
    # Get the deeds that are not deleted
    query = (
        frappe.qb.from_(watheq_deed_dt)
        .inner_join(deed_real_estate_details_dt)
        .on(watheq_deed_dt.name == deed_real_estate_details_dt.parent)
        .inner_join(split_service_dt)
        .on((watheq_deed_dt.name == split_service_dt.deed) & (split_service_dt.is_active == 1))
        .select(
            watheq_deed_dt.name.as_("deed_id"),
            watheq_deed_dt.deed_number,
            watheq_deed_dt.deed_area,
            watheq_deed_dt.creation.as_("request_date"),
            deed_real_estate_details_dt.location_description,
            deed_real_estate_details_dt.city_name.as_("deed_city"),
            deed_real_estate_details_dt.region_name.as_("deed_region"),
            split_service_dt.name.as_("request_id"),
            split_service_dt.status,
            split_service_dt.status.as_("status_label"),
            split_service_dt.split_eligibility,
            split_service_dt.current_market_deed_price.as_("bursa_price"),
            split_service_dt.customer_equity.as_("equity_percent")
            
        )
        .where(watheq_deed_dt.deed_owner == frappe.session.user)  
    )
    # Apply the global filter
    if global_filter:
        query = query.where(
             (fn.Lower(watheq_deed_dt.name).like(
            f"%{global_filter}%"))|
            (fn.Lower(watheq_deed_dt.deed_number).like(
            f"%{global_filter}%"))|
            (fn.Lower(watheq_deed_dt.deed_serial).like(
            f"%{global_filter}%"))|
            (fn.Lower(watheq_deed_dt.deed_area).like(
            f"%{global_filter}%"))|
            (fn.Lower(deed_real_estate_details_dt.city_name).like(
            f"%{global_filter}%"))|
             (fn.Lower(split_service_dt.name).like(
            f"%{global_filter}%"))
        )
    if kw.get("request_status_filter"):
        query = query.where(split_service_dt.status == kw.get("request_status_filter"))

    if kw.get("filter_by_status"):
        query = query.where(split_service_dt.status == kw.get("filter_by_status"))

    data_len = len(query.run(as_dict=True))
    
    data = query.offset(offset).limit(page_size).run(as_dict=True)

    return {
        "data" : translate(data , ["status"]),  
        "meta": {
            "current_page": int((offset/page_size)+1),
            "total_items": data_len,
            "items_per_page": page_size,
            "total_pages": math.ceil(data_len / page_size)
        },
    }


@frappe.whitelist(methods=['POST'])
def create_bank_split_request(split_service_request_id , deed_id):

    try:

        split_service_request = frappe.get_doc("Split Service Request", split_service_request_id)
        if split_service_request.requester != frappe.session.user:
            frappe.local.response.http_status_code = 404
            return {
                "status": False,
                "message": "You are not authorized to create a bank request for this split service request"
            }
        deed = frappe.get_doc("WATHEQ Deed", deed_id)
        if deed.deed_owner != frappe.session.user:
            frappe.local.response.http_status_code = 404
            return {
                "status": False,
                "message": "You are not authorized to create a bank request for this deed"
            }
        if split_service_request.status != "Eligible For Split":
            frappe.local.response.http_status_code = 400
            return {
                "status": False,
                "message": "This split service request is not approved"
            }
        if split_service_request.split_eligibility == False:
            frappe.local.response.http_status_code = 400
            return {
                "status": False,
                "message": "This split service request is not eligible for split"
            }
        if split_service_request.is_active == 0:
            frappe.local.response.http_status_code = 400
            return {
                "status": False,
                "message": "This split service request is not active"
            }
        
        person_data = frappe.get_doc("Person Data", frappe.session.user)


        mortgage_data = {
            "current_mortgage_id": "", #TODO: Get from deed mortgage info
            "current_due_amount": split_service_request.current_due_amount,
            "new_market_price": split_service_request.current_market_deed_price,
            "bank_equity_percentage": split_service_request.bank_equity,
            "bank_holder": {
                "cr": "",
                "bank_name": ""
            },
            "deed_number": deed.deed_number,
            "owner_national_id": person_data.nin,
            "smr_id": split_service_request.name,
            "status": "New",  # Possible values: New, Old, Negotiation
            "wakala_number": "12345", #TODO: Get from settings
            "update": split_service_request.split_service_update  # Only for demo
        }


        result = call_split_bank_request_api(mortgage_data)
        if result.get("status"):    
            bank_request = frappe.get_doc({
                "doctype": "Split Bank Request",
                "requester": frappe.session.user,
                "split_service_request": split_service_request_id,
                "deed_id": deed_id,
                "submission_date": frappe.utils.now_datetime(),
                "status": "Pending"
            })
            bank_request.insert(ignore_permissions=True)
            frappe.db.commit()
        else:
            return result
        return {
            "status": True,
            "data" : {
                "result" : result,
                "bank_request" : bank_request
            },
            "message": "Bank request created successfully"
        }

    
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "status": False,
            "message": str(e)
        }




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
            "data" : split_service_request,
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
                "split_request_status" : split_service_request.status,
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