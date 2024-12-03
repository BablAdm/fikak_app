import frappe
from frappe.exceptions import DoesNotExistError
from fikak_app.fikak_api.integrations_evaluator_api import handle_evaluator_response_webhook

@frappe.whitelist()
def check_test_mode():
    """
    Fetch The Test mode".
    """
    try:
        # before start we should check if mode test is enabled 
        if(is_test_mode_enabled() == False):
           return {"test_mode" : 0}
        return {"test_mode" : 1}
    except DoesNotExistError:
         return {"test_mode" : 0}


@frappe.whitelist()
def set_evaluation_as_paid(split_service_request):
    """
    Fetch The Evaluation Request Doctype".
    """
    try:
        # before start we should check if mode test is enabled 
        if(is_test_mode_enabled() == False):
           return {"test_mode" : 0}
 
        # Get the evaluation request Doc and make it as paid
        evaluationRequest_dt = frappe.get_doc("Evaluation Request", {"request": split_service_request,"evaluation_source":"Split Service Request"})
        
        if not evaluationRequest_dt:
            frappe.throw(f"Evaluation Request with ID {split_service_request} not found in Eligibility Check Request {split_service_request}.")

        evaluationRequest_dt.status = "Paid"
        evaluationRequest_dt.save(ignore_permissions=True)


        split_service_dt = frappe.get_doc("Split Service Request", split_service_request)
        split_service_dt.status = "Paid"
        split_service_dt.save(ignore_permissions=True)
        frappe.db.commit()
      
        return {
            "test_mode" : 1,
            "paid": "sucess"
        }

    except DoesNotExistError as e:
        frappe.throw(f"split request with ID {split_service_request} does not exist." , e)


@frappe.whitelist()
def simulate_evaluator_webhook(split_service_request):
    # Fetch the Evaluation Request Doctype document
    evaluation_request_dt = frappe.get_doc("Evaluation Request", {"request" : split_service_request})
    return handle_evaluator_response_webhook(evaluation_request_dt.name)


@frappe.whitelist()
def get_eligibility_request_deed_data(deed_id, request_id=0):
    """
    Fetch specific deed data from the table "Eligibility Check Request Deed Item".
    """
    try:
        # before start we should check if mode test is enabled 
        if(is_test_mode_enabled() == False):
           return {"test_mode" : 0}
        if(request_id == 0):
            request_id = get_eligibility_request_id(deed_id)
            
        # Fetch the parent document
        request_doc = frappe.get_doc("Eligibility Check Request", request_id)

        # Find the deed in the child table
        deed = next((item for item in request_doc.requested_deeds if item.deed == deed_id), None)

        if not deed:
            frappe.throw(f"Deed with ID {deed_id} not found in Eligibility Check Request {request_id}.")

        # Fetch the parent document
        deed_dt = frappe.get_doc("WATHEQ Deed", deed_id)         

        return {
            "test_mode" : 1,
            "deed_name": deed.deed,
           # "current_market_deed_price": deed.current_market_deed_price,
            "total_interest_payment": deed.total_interest_payment,
            "total_principal_payment": deed.total_principal_payment,
            "deed_price": deed_dt.deed_price,
            "down_price": deed_dt.down_price,
        }

    except DoesNotExistError:
        frappe.throw(f"Eligibility Check Request with ID {request_id} does not exist.")


@frappe.whitelist()
def update_eligibility_request_deed_data( deed_id , updated_fields, request_id=0):
    """
    Update specific fields in a deed in the table "Eligibility Check Request Deed Item".
    """
    try:
        # before start we should check if mode test is enabled 
        if(is_test_mode_enabled() == False):
           return {"test_mode" : 0}
        if(request_id == 0):
            request_id = get_eligibility_request_id(deed_id)
        # Fetch the parent document
        request_doc = frappe.get_doc("Eligibility Check Request", request_id)

        # Find the deed in the child table
        el_deed_dt = next((item for item in request_doc.requested_deeds if item.deed == deed_id), None)

        if not el_deed_dt:
            frappe.throw(f"Deed with ID {deed_id} not found in Eligibility Check Request {request_id}.")

        # Update fields
        updated_fields = frappe.parse_json(updated_fields)  # Convert JSON string to dictionary
        for key, value in updated_fields.items():
            if hasattr(el_deed_dt, key):
                setattr(el_deed_dt, key, value)
        # Save the changes
        el_deed_dt.save()

        # Fetch the parent document
        deed_dt = frappe.get_doc("WATHEQ Deed", deed_id) 
        for key, value in updated_fields.items():
            if hasattr(deed_dt, key):
                setattr(deed_dt, key, value)
        # Save the changes
        deed_dt.save()

        frappe.db.commit()

        return {"test_mode" : 1,"message": f"Deed {deed_id} updated successfully in Eligibility Check Request {request_id}."}

    except DoesNotExistError as e:
        frappe.local.response.http_status_code = 404
        return {
            "data": None,
            "message": str(e),
            "status": False
        }


def get_eligibility_request_id(deed_id):
    # Find the most recent Eligibility Check Request containing the deed_id
    query = """
        SELECT 
            parent 
        FROM 
            `tabEligibility Check Request Deed Item` 
        WHERE 
            deed = %s 
        ORDER BY 
            creation DESC 
        LIMIT 1
    """
    parent_request = frappe.db.sql(query, (deed_id,), as_dict=True)
    
    if not parent_request:
        frappe.throw(f"No Eligibility Check Request found for Deed ID {deed_id}.")

    # Get the parent Eligibility Check Request
    request_name = parent_request[0]["parent"]
    return request_name



def is_test_mode_enabled():
    """
    Fetches Test Mode From DEV MOD PROPS Doctype.
    Returns:
        dict: Configuration containing base URL, access token, and enabled status.
    """
    settings = frappe.get_single("DEV MOD PROPS")
    if not settings.enable_mode_test:
        return False
    
    return True