

import frappe
import requests


def create_new_mortgage_request_api(deed_info, organization_info, mortgage_info):
    """
    Sends a POST request to the external API.
    """
    try:
        endpoint = "http://dev-api.waseera.sa/smr/api/v1/createNewMortgage"
        payload = {
            "deedInfo": deed_info,
            "organizationInfo": organization_info,
            "mortgageInfo": mortgage_info,
        }
        headers = {"Content-Type": "application/json"}

        # Send the request
        response = requests.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()

 
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
    
 
    
def release_mortgage_request_api(deed_info, organization_info):
    """
    Sends a POST request to the external API.
    """
    try:
        endpoint = "http://dev-api.waseera.sa/smr/api/v1/releaseMortgage"
        payload = {
            "deedInfo": deed_info,
            "organizationInfo": organization_info
        }
        headers = {"Content-Type": "application/json"}

        # Send the request
        response = requests.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()

 
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
 


def handle_hook_response(mortgage_request_id, status):
    """
    Updates the status of the Mortgage Registration Request based on the external API response.
    """
    try:
        # Fetch the Mortgage Registration Request
        mortgage_request = frappe.get_doc("Mortgage Registration Request", mortgage_request_id)

        # Update the status
        mortgage_request.status = status
        
        # TODO : Add some other informations
        
        
        mortgage_request.save()
        frappe.db.commit()

        return {"status": "success", "message": "Mortgage Registration Request status updated successfully."}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Hook Response Error"))
        return {"status": "error", "message": str(e)}