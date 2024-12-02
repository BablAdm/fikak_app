import frappe
from frappe.exceptions import DoesNotExistError


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
def set_evaluation_as_paid(deed_id):
    """
    Fetch The Evaluation Request Doctype".
    """
    try:
        # before start we should check if mode test is enabled 
        if(is_test_mode_enabled() == False):
           return {"test_mode" : 0}
 
        # Get the evaluation request Doc and make it as paid
        evaluationRequest_dt = frappe.get_doc("Evaluation Request", {"deed": deed_id, "status": "Pending"})
        
        if not evaluationRequest_dt:
            frappe.throw(f"Deed with ID {deed_id} not found in Eligibility Check Request {request_id}.")

        evaluationRequest_dt.status = "Paid"
        evaluationRequest_dt.save(ignore_permissions=True)
        frappe.db.commit()

      
        return {
            "test_mode" : 1,
            "paid": "sucess"
        }

    except DoesNotExistError:
        frappe.throw(f"Deed with ID {deed_id} does not exist.")


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

        return {
            "test_mode" : 1,
            "deed_name": deed.deed,
            "current_market_deed_price": deed.current_market_deed_price,
            "total_interest_payment": deed.total_interest_payment,
            "total_principal_payment": deed.total_principal_payment
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
        deed = next((item for item in request_doc.requested_deeds if item.deed == deed_id), None)

        if not deed:
            frappe.throw(f"Deed with ID {deed_id} not found in Eligibility Check Request {request_id}.")

        # Update fields
        updated_fields = frappe.parse_json(updated_fields)  # Convert JSON string to dictionary
        for key, value in updated_fields.items():
            if hasattr(deed, key):
                setattr(deed, key, value)
            else:
                frappe.throw(f"Field {key} does not exist in Eligibility Check Request Deed Item.")

        # Save the changes
        request_doc.save()
        frappe.db.commit()

        return {"test_mode" : 1,"message": f"Deed {deed_id} updated successfully in Eligibility Check Request {request_id}."}

    except DoesNotExistError:
        frappe.throw(f"Eligibility Check Request with ID {request_id} does not exist.")


def get_eligibility_request_id(deed_id):
    # Find the most recent Eligibility Check Request containing the deed_id
    query = """
        SELECT 
            parent 
        FROM 
            `tabEligibility Check Request Deed Item` 
        WHERE 
            name = %s 
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