

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
    

def call_lba_bank_request_api(mortgage_data):
    """
    Create a request for evaluator .
    Returns:
        dict: response for evaluator json.
    """
    try:

        # Fetch Evaluator settings
        
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
    


def get_lba_bank_offer(mortgage_data):

    return {"status": True,"data" :  {
        "loan_amount" : mortgage_data.get("new_market_price") * (1-mortgage_data.get("bank_equity_percentage"))/100,
        "mortgage_number_months" : 10 * 12,
        "end_date_of_new_mortgage" : "12-12-2034",
        "mortgage_duration" : 10,
        "mortgage_start_payment_date" : "12-12-2024",
        "mortgage_installement" :  (mortgage_data.get("new_market_price") * (1-mortgage_data.get("bank_equity_percentage"))/100) / (10 * 12),
        "lba_bank_id" : "test0001"
    } ,  "message": "Split Request Created successfully"}
