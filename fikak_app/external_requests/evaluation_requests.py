

import frappe
import requests
from fikak_app.controllers.evaluation_request_controller import get_evaluator_settings

from fikak_app.utils.global_utils import convert_hijri_to_gregorian


def create_evaluation_request(deed_id , requester , evaluation_request_id ):
    """
    Create a request for evaluator .
    Returns:
        dict: response for evaluator json.
    """
    try:

        # Fetch necessary documents
        deed_doc = frappe.get_doc("WATHEQ Deed", deed_id)
        user_data = frappe.get_doc("User", requester)
        user_person_data = frappe.get_doc("Person Data", {"user": user_data.name})
        
        # Prepare request parameters
        request_params = _prepare_create_evaluation_request_params(evaluation_request_id , deed_doc, user_data, user_person_data)
            
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
    
def _prepare_create_evaluation_request_params(evaluation_request_id, deed_doc, user_data, user_person_data):
    """Prepares the request parameters for the evaluation API."""
    try:
        deed_date_gregorian = convert_hijri_to_gregorian(deed_doc.deed_date)
        real_estate_details = deed_doc.real_estate_details[0] if deed_doc.real_estate_details else {}

        return {
            "request_id": evaluation_request_id,
            "deed_date": deed_date_gregorian,
            "deed_no": deed_doc.deed_number,
            "request_type_id": "1",  # TODO: Map correct request_type_id
            "sector_no": real_estate_details.get("plan_number", ""),
            "land_no": real_estate_details.get("land_number", ""),
            "land_area": deed_doc.deed_area,
            "city_id": "000001",  # TODO: Fetch actual city_id
            "area_id": "000001",  # TODO: Fetch actual area_id
            "client_name": user_data.full_name,
            "phone": user_person_data.phone_number,
        }
    except KeyError as e:
        frappe.throw(f"Missing required data: {e}")