


import frappe
from fikak_app.controllers.lba_controller import  check_lba_source , create_banks_loan_request
from frappe import _
from datetime import datetime
# from fikak_app.external_requests.split_service_requests import call_lba_bank_request_api , get_lba_bank_offer
import math
from pypika import Order, Case , functions as fn
from fikak_app.utils.global_utils import translate 
from fikak_app.external_requests.split_service_requests import call_lba_banks_request_api



@frappe.whitelist(methods=["GET"])
def get_lba_requests_list(global_filter = None , filter_by_request = None , offset = 0 , page_size = 10 , order_direction = -1 , order_by = "creation" , **kw):
    
    
    if isinstance(offset, str):
        offset = int(offset)
    
    if isinstance(page_size, str):
        page_size = int(page_size)

    watheq_deed_dt = frappe.qb.DocType("WATHEQ Deed")
    loan_service_dt = frappe.qb.DocType("Loan Service Request")
    deed_real_estate_details_dt = frappe.qb.DocType("WATHEQ Real Estate Details Item")
    # Get the deeds that are not deleted
    query = (
        frappe.qb.from_(watheq_deed_dt)
        .inner_join(deed_real_estate_details_dt)
        .on(watheq_deed_dt.name == deed_real_estate_details_dt.parent)
        .inner_join(loan_service_dt)
        .on((watheq_deed_dt.name == loan_service_dt.deed) & (loan_service_dt.is_active == 1))
        .select(
            watheq_deed_dt.name.as_("deed_id"),
            watheq_deed_dt.deed_number,
            watheq_deed_dt.deed_area,
            watheq_deed_dt.creation.as_("request_date"),
            deed_real_estate_details_dt.location_description,
            deed_real_estate_details_dt.city_name.as_("deed_city"),
            deed_real_estate_details_dt.region_name.as_("deed_region"),
            loan_service_dt.name.as_("request_id"),
            loan_service_dt.status,
            loan_service_dt.status.as_("status_label"),
            loan_service_dt.current_market_deed_price.as_("bursa_price"),
            loan_service_dt.customer_equity.as_("equity_percent")
            
        )
        .where(watheq_deed_dt.deed_owner == frappe.session.user)  
    )
    # Apply the global filter
    if global_filter:
        query = query.where(
             (fn.Lower(watheq_deed_dt.name).like(
            f"%{global_filter.lower()}%"))|
            (fn.Lower(watheq_deed_dt.deed_number).like(
            f"%{global_filter.lower()}%"))|
            (fn.Lower(watheq_deed_dt.deed_serial).like(
            f"%{global_filter.lower()}%"))|
            (fn.Lower(watheq_deed_dt.deed_area).like(
            f"%{global_filter.lower()}%"))|
            (fn.Lower(deed_real_estate_details_dt.city_name).like(
            f"%{global_filter.lower()}%"))|
             (fn.Lower(loan_service_dt.name).like(
            f"%{global_filter.lower()}%"))
        )
    if kw.get("request_status_filter"):
        query = query.where(loan_service_dt.status == kw.get("request_status_filter"))

    if kw.get("filter_by_status"):
        query = query.where(loan_service_dt.status == kw.get("filter_by_status"))

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


@frappe.whitelist(methods=['GET'])
def get_deed_lba_status(deed_id):
    try:
        deed = frappe.get_doc("WATHEQ Deed", deed_id)
        lba_source = check_lba_source(deed)

        if deed.deed_owner != frappe.session.user:
            frappe.local.response.http_status_code = 404
            return {
                "status": False,
                "message": "You are not authorized to view this deed"
            }
        try:
            lba_service_request = frappe.get_doc("Loan Service Request", {"deed": deed_id, "requester": frappe.session.user})
            if lba_source["split_request"]:
                evaluation_request = frappe.get_doc("Evaluation Request", {"request" : lba_source["split_request"] , "evaluation_source" : "Split Service Request"})
            else:
                evaluation_request = frappe.get_doc("Evaluation Request", {"request" : lba_service_request.name , "evaluation_source" : "Loan Service Request"})
            return {
                "status": True,
                "data" : {
                    "lba_service_status" : lba_service_request.status,
                    "lba_source" : lba_source,
                    "lba_service_request" : lba_service_request.name,
                    "evaluation_request_status" : evaluation_request.status,
                    "evaluation_request" : evaluation_request.name,
                    "payment_type" : evaluation_request.payment_type,
                    "is_paid" : evaluation_request.is_paid
                    
                },
                "message": "Lba service request retrieved successfully"
            }
        except frappe.DoesNotExistError:
            return {
                "status": False,
                "data" : {
                    "lba_service_status" : False, 
                    "lba_service_request" : False,
                    "lba_source" : lba_source,
                    "evaluation_request_status" : False,
                    "evaluation_request" : False,
                    "payment_type" : False,
                    "is_paid" : False

                },
                "message": "No lba service request found for this deed"
            }
        
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "status": False,
            "message": str(e)
        }
    


@frappe.whitelist(methods=['GET'])
def get_lba_service_result(lba_service_request_id):
    try:
        
        lba_service_request = frappe.get_doc("Loan Service Request", lba_service_request_id).as_dict()
        
        if frappe.session.user != lba_service_request.requester:
            frappe.local.response.http_status_code = 404
            return {
                "status": False,
                "message": _("You are not authorized to view this split service request")
            }
        deed_doc = frappe.get_doc("WATHEQ Deed", lba_service_request.deed).as_dict()

        fikak_settings = frappe.get_single("Fikak Settings")



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
                "status" : "Eligible For Loan",
                "split_request_status" : lba_service_request.status,
                "bursa_price" : lba_service_request.current_market_deed_price,
                "equity_percent" : lba_service_request.customer_equity,
                "loan_amount" : lba_service_request.max_new_loan,
                "max_loan_percent" : fikak_settings.max_new_loan,
                "waseera_fees" : fikak_settings.waseera_fees
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
    
@frappe.whitelist(methods=['POST'])
def create_bank_lba_request(loan_service_request_id , deed_id , offer_data = None):
    try:
        loan_service_request = frappe.get_doc("Loan Service Request", loan_service_request_id)
        if loan_service_request.requester != frappe.session.user:
            frappe.local.response.http_status_code = 404
            return {
                "status": False,
                "message": "You are not authorized to create a bank request for this loan service request"
            }
        
        deed = frappe.get_doc("WATHEQ Deed", deed_id)
        lba_source = check_lba_source(deed)

        if deed.deed_owner != frappe.session.user:
            frappe.local.response.http_status_code = 404
            return {
                "status": False,
                "message": "You are not authorized to create a bank request for this deed"
            }
        if loan_service_request.status != "Eligible For Loan":
            frappe.local.response.http_status_code = 400
            return {
                "status": False,
                "message": "This loan service request is not approved"
            }
        
        if loan_service_request.is_active == 0:
            frappe.local.response.http_status_code = 400
            return {
                "status": False,
                "message": "This split service request is not active"
            }
        # USED FOR FAKE API : see the code of this request   
        # result = get_lba_bank_offer(mortgage_data)
        person_data = frappe.get_doc("Person Data", frappe.session.user)
        mortgage_data = {
            "current_mortgage_id": "", #TODO: Get from deed mortgage info
            "current_due_amount": offer_data.get("negociatedAmount") if offer_data else 0 ,## TODO : see with mohamed this value not exist loan_service_request.current_due_amount,
            "new_market_price": loan_service_request.current_market_deed_price,
            "bank_equity_percentage": offer_data.get("equity") if offer_data else 0,
            "bank_holder": {
                "cr": "",
                "bank_name": ""
            },
            "deed_number": deed.deed_number,
            "owner_national_id": person_data.nin,
            "smr_id": loan_service_request.name,
            "status": "New",  # Possible values: New, Old, Negotiation
            "wakala_number": "12345", #TODO: Get from settings
            "update": "0" # TODO : see with moh we create new loan_service_request.split_service_update  # Only for demo
        }
        # Create many requests to banks in order to get offers
        banks_responses = call_lba_banks_request_api(mortgage_data)
        # Create the bank loan request doctype with all offers
        bank_request = create_banks_loan_request(loan_service_request_id,deed_id,lba_source,offer_data, banks_responses)

        return {
            "status": True,
            "data" : {
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
def get_lba_service_offers(lba_service_request_id ,  global_filter = None , filter_by_request = None , offset = 0 , page_size = 10 , order_direction = -1 , order_by = "creation" , **kw):
    
    if isinstance(offset, str):
        offset = int(offset)
    
    if isinstance(page_size, str):
        page_size = int(page_size)
    
    bank_request_dt = frappe.qb.DocType("Bank Loan Request")
    bank_request_response_dt = frappe.qb.DocType("Bank Loan Request Offer Item")
    watheq_deed = frappe.qb.DocType("WATHEQ Deed")
    bank_dt = frappe.qb.DocType("Bank Provider")

    query = (
        frappe.qb.from_(bank_request_dt)
        .inner_join(bank_request_response_dt)
        .on(bank_request_dt.name == bank_request_response_dt.parent)
        .inner_join(watheq_deed)
        .on(bank_request_dt.deed_id == watheq_deed.name)
        .inner_join(bank_dt)
        .on(bank_request_response_dt.bank == bank_dt.name)        
        .select(
            bank_request_dt.name.as_("bank_request_id"),
            Case()
            .when(bank_request_dt.status == "Waiting For Customer Validation", "Customer Review")
            .else_(bank_request_dt.status).as_("bank_request_status"),
            watheq_deed.deed_number,
            watheq_deed.deed_serial,
            watheq_deed.deed_area,
            bank_request_dt.submission_date.as_("bank_request_submission_date"),
            bank_request_response_dt.offered_equity,
            bank_request_response_dt.requested_amount,
            bank_request_response_dt.requested_equity,
            bank_request_response_dt.name.as_('offer_id'),
            bank_request_response_dt.negociated_loan_amount,
            bank_request_response_dt.mortgage_number_months,
            bank_request_response_dt.offer_date,
            bank_dt.name,
            bank_dt.logo,
            bank_request_response_dt.new_mortgage_end_date,
            Case()
            .when(bank_request_response_dt.status == "Waiting For Customer Validation", "Customer Review")
            .else_(bank_request_response_dt.status).as_("bank_offer_status"),
            bank_request_response_dt.mortgage_start_payment_date,
            bank_request_response_dt.mortgage_installement,
            # bank_request_response_dt.type,
            bank_request_response_dt.mortgage_duration,
            bank_request_response_dt.lba_bank_id
        )
        .where(bank_request_dt.loan_service_request == lba_service_request_id)
        .orderby(bank_request_response_dt.idx ,order = Order.asc)
    )

    if global_filter :
        query = query.where(
            (fn.Lower(bank_request_response_dt.status).like(
            f"%{global_filter.lower()}%"))|
            (fn.Lower(bank_request_response_dt.type).like(
            f"%{global_filter.lower()}%"))
            )
    data = query.run(as_dict=True)
    data_len = len(data)
    data = data[offset:offset+page_size]
    
    fikak_settings = frappe.get_single("Fikak Settings")
    loan_service_request_doc = frappe.get_doc("Loan Service Request", lba_service_request_id)

    return {
        "data" : data,
        "settings": {
            "bursa_price" : loan_service_request_doc.get("current_market_deed_price"),
            "equity_percent" : loan_service_request_doc.get("customer_equity"),
            "loan_amount" : loan_service_request_doc.get("max_new_loan"),
            "max_loan_percent" : fikak_settings.max_new_loan,
            "waseera_fees" : fikak_settings.waseera_fees

        },
        "meta": {
            "current_page": offset,
            "total_items": data_len,
            "items_per_page": page_size,
            "total_pages": math.ceil(data_len / page_size)
        },
        "message" : _("Bank offers retrieved successfully")
    }


@frappe.whitelist(methods=["POST"])
def update_bank_offer_status(bank_offer_id , bank_lba_request_id , status , offer_data = None):
#Status : Accepted , Rejected , Negociation
    try:
        bank_split_request = frappe.get_doc("Bank Loan Request" , bank_lba_request_id)
        if bank_split_request.status != "Waiting For Customer Validation":
            frappe.local.response.http_status_code = 400
            return {
                "status": False,
                "message": _("You can't update this Bank Offer Status  , it must be Under customer Review")
            }

        if frappe.session.user != bank_split_request.requester:
            frappe.local.response.http_status_code = 404
            return {
                "status": False,
                "message": _("You can't update this Bank Offer Status  , You are not authorized to update this bank offer")
            }
        
        bank_offer = frappe.get_doc("Bank Loan Request Offer Item" , bank_offer_id)
        if bank_offer.status != "Waiting For Customer Validation":
            frappe.local.response.http_status_code = 400
            return {
                "status": False,
                "message": _("You can't update this Bank Offer Status  , it must be Under customer Review")
            }
        bank_offer.status = status
        

        bank_offer.save(ignore_permissions=True)

        bank_split_request_new_doc = frappe.get_doc("Bank Loan Request", bank_lba_request_id)
        bank_split_request_new_doc.status = status



        if status == "Negociation":
            bank_split_request_new_doc.append("bank_offers", {
                "status": "Pending" , 
                "requested_equity" : offer_data.get("equity") ,
                "requested_amount" : offer_data.get("negociatedAmount"),
                "bank": bank_offer.bank ,
            })
        # TODO : if the status = accept so refuse all other response
        if status == "Accepted":
            # Loop through the bank_offers child table
            for offer in bank_split_request_new_doc.bank_offers:
                # Update the status if it is neither "none" nor "accept"
                if offer.status == "Waiting For Customer Validation":
                    offer.status = "Rejected"

        # Save the document after updating the child table       
        bank_split_request_new_doc.save(ignore_permissions=True)

        return {
            "status": True,
            "data" : bank_offer,
            "message" : _("bank_request_created" if status not in ("Accepted" , "Rejected") else "bank_request_updated")
        }
    
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "status" : False,
            "message" : str(e)
        }