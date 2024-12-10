

import frappe
import math
from pypika import Case , functions as fn
from fikak_app.utils.global_utils import translate 

@frappe.whitelist(methods=["GET"])
def get_deeds_stats():
    return {
        "all_deeds_number" : frappe.db.count("WATHEQ Deed" , filters = {"deed_owner" : frappe.session.user}),
        "not_eligible" : get_number_deeds_by_status("Not Eligible"),
        "eligible_for_loan" : get_number_deeds_by_status("Eligible For Loan"),
        "eligible_for_split" : get_number_deeds_by_status("Eligible For Split"),
        "pending" : get_number_deeds_by_status("NEW"),
    }

def get_number_deeds_by_status(status):
    eligibility_dt = frappe.qb.DocType("Eligibility Check Request")
    eligibility_deed_item_dt = frappe.qb.DocType("Eligibility Check Request Deed Item")

    query = (
        frappe.qb.from_(eligibility_dt)
        .inner_join(eligibility_deed_item_dt)
        .on(eligibility_dt.name == eligibility_deed_item_dt.parent)
        .select(
            eligibility_deed_item_dt.name
        ).where((eligibility_deed_item_dt.status == status) & (eligibility_dt.user == frappe.session.user))
    )
    res = query.run(as_dict=True)
    return len(res)


@frappe.whitelist(methods=["GET"])
def get_deeds_list(global_filter = None , filter_by_request = None , offset = 0 , page_size = 10 , order_direction = -1 , order_by = "creation" , **kw):
    
    
    if isinstance(offset, str):
        offset = int(offset)
    
    if isinstance(page_size, str):
        page_size = int(page_size)

    watheq_deed_dt = frappe.qb.DocType("WATHEQ Deed")
    deed_item_dt = frappe.qb.DocType("Eligibility Check Request Deed Item")
    deed_real_estate_details_dt = frappe.qb.DocType("WATHEQ Real Estate Details Item")
    # Get the deeds that are not deleted
    query = (
        frappe.qb.from_(watheq_deed_dt)
        .left_join(deed_real_estate_details_dt)
        .on(watheq_deed_dt.name == deed_real_estate_details_dt.parent)
        .left_join(deed_item_dt)
        .on((watheq_deed_dt.name == deed_item_dt.deed) & (deed_item_dt.is_active == 1))
        .select(
            watheq_deed_dt.name.as_("deed_id"),
            watheq_deed_dt.deed_number,
            watheq_deed_dt.deed_serial,
            watheq_deed_dt.deed_area,
            watheq_deed_dt.deed_status,
            watheq_deed_dt.deed_price.as_("last_price_registred"),
            watheq_deed_dt.is_real_estate_mortgaged,
            watheq_deed_dt.service,
            watheq_deed_dt.service_status,
            deed_real_estate_details_dt.city_name.as_("deed_city"),
            deed_real_estate_details_dt.region_name.as_("deed_region"),
            deed_item_dt.parent.as_("request_id"),
            Case()
            .when(deed_item_dt.status == "NEW", "PENDING")
            .when(deed_item_dt.status.isnotnull(), deed_item_dt.status)
            .else_("Not Requested Yet").as_("status"),
            Case()
            .when(deed_item_dt.status == "NEW", "PENDING")
            .when(deed_item_dt.status.isnotnull(), deed_item_dt.status)
            .else_("Not Requested Yet").as_("status_label"),
            deed_item_dt.loan_eligibility,
            deed_item_dt.current_market_deed_price.as_("bursa_price"),
            deed_item_dt.customer_equity.as_("equity_percent"),
            deed_item_dt.new_loan.as_("loan_amount"),
            deed_item_dt.split_eligibility,
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
            f"%{global_filter.lower()}%"))
        )
    if kw.get("request_status_filter"):
        status_filter = "Pending" if kw.get("request_status_filter") == "NEW" else kw.get("request_status_filter")
        query = query.where(watheq_deed_dt.service_status == status_filter)

    if kw.get("split_filter"):
        split_filter = 1 if kw.get("split_filter") == "eligible" else 0
        query = query.where(deed_item_dt.split_eligibility == split_filter)
    if filter_by_request:
        query = query.where(deed_item_dt.parent == filter_by_request)
    if kw.get("loan_filter"):
        loan_filter = 1 if kw.get("loan_filter") == "eligible" else 0
        query = query.where(deed_item_dt.loan_eligibility == loan_filter)

    if kw.get("service_filter"):
        if (kw.get("service_filter") == "NEW") :
            query = query.where(watheq_deed_dt.service.isnull())
        else : 
            query = query.where(watheq_deed_dt.service == kw.get("service_filter"))

    if kw.get("mortgage"):
        mortgage = 1 if kw.get("mortgage") == "1" else 0
        query = query.where(watheq_deed_dt.is_real_estate_mortgaged == mortgage)


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

@frappe.whitelist(methods=["GET"])
def get_deed_details(deed_id):
    try:
        deed_doc = frappe.get_doc("WATHEQ Deed", {"name" : deed_id , "deed_owner" : frappe.session.user})
        return {
            "status": True,
            "data": deed_doc.as_dict(),
            "message": "Deed details retrieved successfully"
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "status": False,
            "message": str(e)
        }
    

@frappe.whitelist(methods=["DELETE"])
def delete_deed(deed_id):
    
    try:
        if frappe.get_all("Eligibility Check Request Deed Item", {"deed": deed_id}):
            frappe.local.response.http_status_code = 400
            return {
                "status": False,
                "message": "Deed can't be deleted as it has requests associated with it"
            }
        deed_doc = frappe.get_doc("WATHEQ Deed", {"name" : deed_id , "deed_owner" : frappe.session.user})
        deed_doc.delete(ignore_permissions=True)
        frappe.db.commit()
        return {
            "status": True,
            "message": "Deed deleted successfully"
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "status": False,
            "message": str(e)
        }