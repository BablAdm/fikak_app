
import frappe
from frappe.utils import now


def update_deed_workflow(deed_name ,service, status, result_dt = None):
    """
    Update the 'Deed' Doctype based on changes in 'Eligibility Check Request Deed Item'
    """	
	## 1. get deed doctype
    deed_dt = frappe.get_doc("WATHEQ Deed", deed_name)

    # 2.Update the Deed status and services
    deed_dt.service_status = status
    deed_dt.service = service

    # 3. Add a new entry to the Watheq Deed Status Item table
    deed_dt.append("statuses", {
        "submission_date": now(),
        "service": service,
        "status": status
    })
    # 4. Should update the deed result info
    if ((status=="Eligible For Split" or status == "Eligible For Loan" ) and result_dt != None ):
        if (service == "Eligibility Check"):
            deed_dt.eligibility_check_customer_equity = result_dt.customer_equity
            deed_dt.eligibility_check_max_loan = result_dt.new_loan
            deed_dt.last_bursa_price = result_dt.current_market_deed_price
        if (service == "Split Service" or service == "Asset-Backed Loan"):
            deed_dt.split_service_customer_equity = result_dt.customer_equity
            deed_dt.split_service_max_loan = result_dt.max_new_loan if service == "Asset-Backed Loan" else result_dt.new_loan
            deed_dt.last_evaluator_price = result_dt.current_market_deed_price

    
    # Save the changes to the Deed Doctype
    deed_dt.save(ignore_permissions=True)
