import frappe
import requests
from fikak_app.controllers.evaluation_request_controller import get_evaluator_settings

def handle_evaluator_response_webhook(request_id, response = ""):
    try: 
        # Fetch Evaluator settings
        settings = get_evaluator_settings()
        
        # Perform the second API call to fetch the request result
        endpoint = f"{settings['base_url']}/api/EvaluationRequests/{request_id}"
        headers = {
            "Authorization": f"Bearer {settings['access_token']}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        # TODO : should uncoment this and replace it by response from the evaluator
        result_response = requests.get(endpoint, headers=headers)
        result_json = result_response.json()
        # Validate the result response
        if not result_json.get("status"):
            frappe.throw(f"API Result Error: {result_json.get('errorMessage')}")
        # 1. get the amount from json and save evaluation doc 
        # evaluated_price = fetch_value_from_evaluator_response(result_json["data"]["evaluation"]) #result_json["data"]["evaluation"]["all_fields_from_reports"][0]
        evaluated_price = result_json.get("data").get("evaluation").get("market_average_price_m2")
        evaluated_price = evaluated_price if evaluated_price >0 else 1000
        # 2. Update evaluation request document status with done
        update_evaluation_request(request_id,evaluated_price, "Done")
    
        # Store the result in Evaluator Evaluation Result Doctype
        result_doc = frappe.get_doc({
            "doctype": "Evaluator Evaluation Hook Response",
            "request_id": result_json["data"]["request_id"],
            "status": result_json["data"]["status"],
            "internal_id": result_json["data"]["internal_id"],
            "evaluation_data": frappe.as_json(result_json["data"]["evaluation"])
        })
        result_doc.insert(ignore_permissions=True)
        
        frappe.db.commit()

        return {"status": "success", "message": "Evaluation processed successfully"}
    

    
    except Exception as e:
        frappe.log_error(message=str(e), title="Evaluation API Error")
        return {"status": "error", "message": str(e)}

evaluationObject = {
    "date_of_evaluation" : "تاريخ التقييم",
    "market_average_price_m2": "السعر المتوسط للمتر المربع",
    "market_price" : "السعر السوقي",
    "status" : "الحالة",
    "report_url" : "رابط التقرير",
}

@frappe.whitelist()
def generate_evaluator_report(deed_id):
    """
    Generate a report for the evaluator result .
    :param docname: The name of the Doctype record to fetch.
    :return: A dictionary containing report data.
    """
    deed = frappe.get_doc("WATHEQ Deed", deed_id)
    if deed.deed_owner != frappe.session.user:
        frappe.local.response.http_status_code = 404
        return {
            "status": False,
            "message": "You are not authorized to view this deed"
        }
    try:
        split_service_request = frappe.get_doc("Split Service Request", {"deed": deed_id, "requester": frappe.session.user})
        # Fetch the Evaluation Request Doctype document
        evaluation_request_dt = frappe.get_doc("Evaluation Request", {"request" : split_service_request.name})

        # Extract specific properties
        report_data = {
            "name": evaluation_request_dt.name,

            "status": evaluation_request_dt.status,  # Replace with actual field name
            "evaluation_price": evaluation_request_dt.evaluation_price,  # Replace with actual field name
        }
        # get response from evaluator doc
        evaluator_response_dt = frappe.get_doc("Evaluator Evaluation Hook Response" , {"request_id" : evaluation_request_dt.name})

        # Parse the JSON field
        json_field = frappe.parse_json(evaluator_response_dt.evaluation_data) 
        extracted_values = {
            evaluationObject[key]: value
            for key ,value in json_field.items() if value is not None
        }

        # Combine the data
        report_data["report_props"] = extracted_values
        report_data["date"] = evaluator_response_dt.creation.strftime('%d/%m/%Y')

        # Fetch Deed details information
        deed_name = evaluation_request_dt.deed
        deed_dt = frappe.get_doc("WATHEQ Deed", deed_name)
        report_data["deed_details"] = {
            "deedNumber" : deed_name,
            "real_estate_type_name" : deed_dt.real_estate_details[0].real_estate_type_name,
            "area" : deed_dt.real_estate_details[0].area,
            "location_description" : deed_dt.real_estate_details[0].location_description
        }
        # Return the report data
        return {"status": "success", "report": report_data}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def update_evaluation_request(request_name,evaluated_price, new_status):
    """
    Update the status field on the Evaluation Request by searching with the request name.

    :param request_name: Name of the request (from the `request` field).
    :param new_status: The new status to update in the `Evaluation Request`.
    :return: Success message or error.
    """
    try:
        # Fetch the Evaluation Request document using the `request` field
        evaluation_request_dt = frappe.get_doc("Evaluation Request", {"name": request_name})

        if not evaluation_request_dt:
            frappe.throw(f"No Evaluation Request found for request: {request_name}")

 
        deed_doc = frappe.get_doc("WATHEQ Deed", evaluation_request_dt.deed)
        # Update the status field
        evaluation_request_dt.evaluation_price = int(evaluated_price) * int(deed_doc.deed_area)
        evaluation_request_dt.status = new_status

        evaluation_request_dt.save(ignore_permissions=True)  # Save with ignore permissions if necessary
        frappe.db.commit()
        return f"Status for Evaluation Request '{evaluation_request_dt.name}' updated to '{new_status}'."
    except Exception as e:
        frappe.log_error(f"Error updating status for request '{request_name}': {str(e)}", "Update Evaluation Request Status")
        frappe.throw(f"Could not update status: {str(e)}")



def fetch_value_from_evaluator_response(json_response):
    """
    Fetch the value of a specified field from a JSON response
    based on the configuration in the Evaluation Settings Doctype.

    :return: Value of the configured field if found, or an appropriate error message.
    """
    try:
        # Fetch the target field name from Evaluation Settings
        settings_doc = frappe.get_single("Evaluator Evaluation Settings")
        amount_field_name = settings_doc.amount_field_name

        if not amount_field_name:
            frappe.throw("No field name configured in Evaluation Settings.")
 

        # Search for the field in the `all_fields_from_reports` list
        for item in json_response.get("all_fields_from_reports", []):
            if item.get("name") == amount_field_name:
                return item.get("value")

        # If the field is not found, return an error message
        frappe.throw(f"Field '{amount_field_name}' not found in the response data.")

    except Exception as e:
        frappe.log_error(f"Error retrieving field value: {str(e)}", "Get Value from JSON Response")
        frappe.throw(f"An error occurred: {str(e)}")