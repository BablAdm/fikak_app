

import frappe
from datetime import datetime


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
        data["max_new_loan"] = split_service_doc.new_loan
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



def create_banks_loan_request(loan_service_request_id, deed_id, lba_source,requested_offer_data, banks_response):
    """
    Creates a Bank Loan Request document and inserts banks offers into the bank_offers child table.

    Args:
        loan_service_request_id (str): ID of the loan service request.
        deed_id (str): ID of the deed.
        lba_source (dict): Source information including `source` and `split_request`.
        bank_responses (list): List of bank response dictionaries containing offer details.

    Returns:
        str: Name of the created Bank Loan Request document.
    """
    try:
        # Prepare the bank offers data
        bank_offers = []
        for bank_response in banks_response:
            if(bank_response["response"]["status"]):
                response_offer = bank_response["response"]["data"]
                bank_offers.append({
                    "status": "Waiting For Customer Validation",
                    "requested_equity" : requested_offer_data.get("equity") ,
                    "requested_amount" : requested_offer_data.get("negociatedAmount"),
                    "negociated_loan_amount": int(response_offer["loan_amount"]),
                    "offered_equity": int(response_offer["bank_equity_percent"]),
                    "new_mortgage_end_date": datetime.strptime( response_offer.get("end_date_of_new_mortgage"), "%d-%m-%Y").strftime("%Y-%m-%d"),
                    "mortgage_start_payment_date": datetime.strptime( response_offer.get("mortgage_start_payment_date"), "%d-%m-%Y").strftime("%Y-%m-%d"),
                    "mortgage_installement": int(response_offer["mortgage_installement"]),
                    "mortgage_number_months": int(response_offer["mortgage_number_months"]),
                    "mortgage_duration":int(response_offer["mortgage_duration"]),
                    "offer_date": frappe.utils.now_datetime(),
                    "bank": bank_response.get("bank")
                    # Include other necessary result fields as needed
                })

        # Create the Bank Loan Request document
        bank_request = frappe.get_doc({
            "doctype": "Bank Loan Request",
            "requester": frappe.session.user,
            "loan_service_request": loan_service_request_id,
            "deed_id": deed_id,
            "submission_date": frappe.utils.now_datetime(),
            "status": "Pending",
            "source": lba_source.get("source"),
            "split_service_request": lba_source.get("split_request"),
            "bank_offers": bank_offers  # Add the prepared bank offers
        })

        # Insert the document into the database
        bank_request.insert(ignore_permissions=True)
        frappe.db.commit()

        frappe.msgprint(f"Bank Loan Request {bank_request.name} created successfully.")
        return bank_request.name

    except Exception as e:
        frappe.log_error(
            message=f"Error while creating Bank Loan Request: {str(e)}",
            title="Bank Loan Request Creation Error"
        )
        frappe.throw(_("An error occurred while creating the Bank Loan Request."))


