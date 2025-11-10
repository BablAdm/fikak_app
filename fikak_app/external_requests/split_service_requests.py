

import frappe
import requests
import json

def call_split_bank_request_api(mortgage_data):
    """
    Create a request for evaluator .
    Returns:
        dict: response for evaluator json.
    """
    try:

        # Fetch Evaluator settings
        
        endpoint = "http://dev-api.waseera.sa/smr/api/v1/bankSplitUpdate"
        headers = {
            "Content-Type": "application/json",
        }
        ## TODO FAKE API TO REMOVE 
        # Ensure values are numbers
        new_market_price = float(mortgage_data["new_market_price"])
        bank_equity_percentage = float(mortgage_data["bank_equity_percentage"])

        # Perform calculations
        percentage = bank_equity_percentage / 100
        base_amount = new_market_price * percentage
        total_estimated_amount = base_amount * 1.1
        mortgage_installment = total_estimated_amount / (12 * 10) 
        response_json = {
                "negociated_due_amount_for_update": total_estimated_amount,
                "update_mortgage_date": "09-12-2024",
                "end_date_of_new_mortgage": "12-09-2034",
                "mortgage_installement": mortgage_installment,
                "mortgage_duration": 10,
                "mortgage_number_months": 120,
                "mortgage_start_payment_date": "09-12-2024",
                "smr_id": "idsmrrequest1",
                "smr_bank_id": "1438"
            }
        return {"status": True,"data" : response_json ,  "message": "Split Request Created successfully"}

        # Perform the first API call
        response = requests.post(endpoint,data=json.dumps(mortgage_data), headers=headers )
        response_json = response.json()
        if response.status_code != 200: 
            frappe.local.response.http_status_code = 500
            return {
                "status" : False,
                "message" : f"API Error: {response_json.get('error')}" 
            }
    
        return {"status": True,"data" : response_json ,  "message": "Split Request Created successfully"}
    
    except Exception as e:
        frappe.log_error(message=str(e), title="Evaluation API Error")
        return {"status": False, "message": str(e)}
    


import frappe
from frappe import _

def call_lba_banks_request_api(mortgage_data):
    """
    Fetches all bank providers with loan proposal enabled and sends the mortgage data
    to each bank's loan proposal endpoint.

    Args:
        mortgage_data (dict): Data to send to the banks for loan proposals.

    Returns:
        list: A list of responses from all bank providers.
    """
    global_result = []

    # Fetch bank providers with loan proposal enabled
    bank_providers = frappe.get_all(
        "Bank Provider",
        filters={"is_loan_proposal_enabled": 1},
        fields=["name","bank_name", "bank_code","logo","loan_proposal_end_point"]
    )

    if not bank_providers:
        frappe.log_error(_("No bank providers with loan proposals enabled."), "Bank API Error")
        return []

    for bank in bank_providers:
        try:
            endpoint = bank.get("loan_proposal_end_point")

            # Call the bank API
            response = call_lba_bank_request_api(mortgage_data, endpoint)

            # Append the response to the global result list
            global_result.append({
                "bank":bank.name,
                "bank_code": bank.bank_code,
                "bank_name": bank.bank_name,
                "logo": bank.logo,
                "endpoint": endpoint,
                "response": response
            })

        except Exception as e:
            # Log the error for debugging
            frappe.log_error(
                title=_("Failed to call bank API for {0}").format(bank.name),
                message=str(e)
            )
            global_result.append({
                "bank_code": bank.bank_code,
                "bank_name": bank.bank_name,
                "logo": bank.logo,
                "endpoint": endpoint,
                "response": {
                    "error": str(e),
                    "success": False
                }
            })

    return global_result



def call_lba_bank_request_api(mortgage_data,endpoint=""):
    """
    Create a request for evaluator .
    Returns:
        dict: response for evaluator json.
    """
    try:

        # Fetch Evaluator settings
        if(endpoint == None or endpoint == ""):
            endpoint = "http://dev-api.waseera.sa/smr/api/v1/loanBackedByAsset"
        
        headers = {
            "Content-Type": "application/json",
        }
        
        # Perform the first API call
        response = requests.post(endpoint,data=json.dumps(mortgage_data), headers=headers )
        response_json = response.json()
        if response.status_code != 200: 
            frappe.local.response.http_status_code = 500
            return {
                "status" : False,
                "message" : f"API Error: {response_json.get('error')}" 
            }
    
        return {"status": True,"data" : response_json ,  "message": "Split Request Created successfully"}
    
    except Exception as e:
        frappe.log_error(message=str(e), title="Evaluation API Error")
        return {"status": False, "message": str(e)}
    


def get_lba_bank_offer(offer_data):

    return {"status": True,"data" :  {
        "loan_amount" : (offer_data.get("equity") * 0.7) ,#(1-mortgage_data.get("bank_equity_percentage")/100),
        "offered_equity" : 70,
        "mortgage_number_months" : 10 * 12,
        "end_date_of_new_mortgage" : "12-12-2034",
        "mortgage_duration" : 10,
        "mortgage_start_payment_date" : "12-12-2024",
        "mortgage_installement" :  (offer_data.get("negociatedAmount") * 0.7) / (10 * 12),
        "lba_bank_id" : "test0001"
    } ,  "message": "Split Request Created successfully"}
