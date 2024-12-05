

import frappe
import requests

def get_evaluator_settings():
    """
    Fetches Evaluator configuration from the Evaluator Evaluation Settings Doctype.
    Returns:
        dict: Configuration containing base URL, access token, and enabled status.
    """
    settings = frappe.get_single("Evaluator Evaluation Settings")
    if not settings.enabled:
        frappe.throw("Evaluator integration is disabled. Please enable it in the Evaluator Settings.")
    
    return {
        "base_url": settings.evaluator_base_url, 
        "access_token": settings.evaluator_access_token
    }



def create_evaluation_request(request_params):
    """
    Create a request for evaluator .
    Returns:
        dict: response for evaluator json.
    """
    try: 
        # Fetch Evaluator settings
        settings = get_evaluator_settings()

        endpoint = f"{settings['base_url']}/api/EvaluationRequests/Create"
        headers = {
            "Authorization": f"Bearer {settings['access_token']}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        # Prepare the data for the API request
        form_data = request_params
        # TODO : Handle deed doc attachements on request
        form_data ["deed_document"] = None
        
        # Perform the first API call
        response = requests.post(endpoint,data=form_data, headers=headers )
        response_json = response.json()
        if (not response_json.get("status") and response_json.get("errorMessage") != 'Request already exists'): 
            frappe.local.response.http_status_code = 500
            return {
                "status" : False,
                "message" : f"API Error: {response_json.get('errorMessage')}" 
            }
            
        
        # Store request and response in Evaluator Evaluation Request Doctype
        request_doc = frappe.get_doc({
            "doctype": "Evaluator Evaluation Request",
            "request_id": response_json["data"]["request_id"],
            "status": response_json["data"]["status"],
            "internal_id": response_json["data"]["internal_id"],
            "request_body": frappe.as_json(form_data),
            "response_body": frappe.as_json(response_json),
        })
        request_doc.insert(ignore_permissions=True)
        
        return {"status": "success", "message": "Evaluation requested successfully"}
    
    except Exception as e:
        frappe.log_error(message=str(e), title="Evaluation API Error")
        return {"status": "error", "message": str(e)}
