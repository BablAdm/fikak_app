

import frappe
import math
from pypika import functions as fn
import json

@frappe.whitelist(methods=["GET"])
def get_deeds_list(global_filter = None, status_filter = None , offset = 0 , page_size = 10 , order_direction = -1 , order_by = "creation"):
    if isinstance(status_filter, str):
        status_filter = json.loads(status_filter)
    
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
            deed_real_estate_details_dt.city_name.as_("deed_city"),
            deed_item_dt.parent.as_("request_id"),
            deed_item_dt.status,
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
    
    if status_filter:
        query = query.where(deed_item_dt.status == status_filter)

    res = query.run(as_dict=True)

    
    return {
        "data" : res,
        "meta": {
            "current_page": int((offset/page_size)+1),
            "total_items": len(res),
            "items_per_page": page_size,
            "total_pages": math.ceil(len(res) / page_size)
        },
    }