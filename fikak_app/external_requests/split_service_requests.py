

import frappe
import requests


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
            "Content-Type": "application/x-www-form-urlencoded",
        }
        # Perform the first API call
        response = requests.post(endpoint,data=mortgage_data, headers=headers )
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
        return {"status": "error", "message": str(e)}