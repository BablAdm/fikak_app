

import frappe
import math
from pypika import functions as fn

@frappe.whitelist(methods=["GET"])
def get_deeds_list(global_filter = None , offset = 0 , page_size = 10 , order_direction = -1 , order_by = "creation" , **kw):
    
    
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
            deed_real_estate_details_dt.city_name.as_("deed_city"),
            deed_item_dt.parent.as_("request_id"),
            deed_item_dt.status,
            deed_item_dt.customer_equity.as_("equity_percent"),
            deed_item_dt.new_loan.as_("loan_bba"),
            deed_item_dt.current_market_deed_price.as_("bursa_price"),
            deed_item_dt.loan_eligibility,
            deed_item_dt.split_eligibility
        )
        .where(watheq_deed_dt.deed_owner == frappe.session.user)  
    )
    # Apply the global filter
    if global_filter:
        query = query.where(
            (fn.Lower(watheq_deed_dt.deed_number).like(
            f"%{global_filter}%"))|
            (fn.Lower(watheq_deed_dt.deed_serial).like(
            f"%{global_filter}%"))|
            (fn.Lower(watheq_deed_dt.deed_area).like(
            f"%{global_filter}%"))|
            (fn.Lower(deed_real_estate_details_dt.city_name).like(
            f"%{global_filter}%"))
        )
    if kw.get("request_status_filter"):
        query = query.where(deed_item_dt.status == kw.get("request_status_filter"))

    if kw.get("split_filter"):
        split_filter = 1 if kw.get("split_filter") == "eligible" else 0
        query = query.where(deed_item_dt.split_eligibility == split_filter)
    
    if kw.get("loan_filter"):
        loan_filter = 1 if kw.get("loan_filter") == "eligible" else 0
        query = query.where(deed_item_dt.loan_eligibility == loan_filter)

    data_len = len(query.run(as_dict=True))
    
    data = query.offset(offset).limit(page_size).run(as_dict=True)
    
    return {
        "data" : data,
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
    

@frappe.whitelist(methods=["GET"])
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