import frappe
from frappe.exceptions import DoesNotExistError
from fikak_app.fikak_api.integrations_evaluator_api import handle_evaluator_response_webhook
from frappe import _
import frappe.utils

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
def set_evaluation_as_paid(request_id ,  source = "Split Service Request"):
    """
    Fetch The Evaluation Request Doctype".
    """
    try:
        # before start we should check if mode test is enabled 
        if(is_test_mode_enabled() == False):
           return {"test_mode" : 0}
        
        # Get the evaluation request Doc and make it as paid
        evaluation_request_dt = frappe.get_doc("Evaluation Request", {"request": request_id,"evaluation_source":source})
        
        evaluation_request_dt.status = "Paid"
        evaluation_request_dt.save(ignore_permissions=True)
        doctype = "Split Service Request" if source == "Split Service Request" else "Loan Service Request"
        split_service_dt = frappe.get_doc(doctype, request_id)
        split_service_dt.status = "Paid"
        split_service_dt.save(ignore_permissions=True)
        frappe.db.commit()
      
        return {
            "status" : True,
            "test_mode" : 1,
            "paid": "sucess"
        }

    except Exception as e:
        frappe.local.response.http_status_code = 404
        return {
            "status": False,
            "message": str(e)
        }


@frappe.whitelist()
def simulate_evaluator_webhook(split_service_request,evaluationPriceTest=0):
    # Fetch the Evaluation Request Doctype document
    evaluation_request_dt = frappe.get_doc("Evaluation Request", {"request" : split_service_request})
    return handle_evaluator_response_webhook(evaluation_request_dt.name,"",evaluationPriceTest)


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
            "deed_price": deed_dt.deed_price,
            "interest_amount": deed_dt.interest_amount,
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
        #el_deed_dt.save()
        request_doc.save()
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

@frappe.whitelist()
def insert_split_bank_request_item( deed_id, data):
    """
    Inserts a new child item into 'Split Bank Request Response Item' linked to a 'Split Service Request'.

    :param deed_id: ID of the deed linked to the 'Split Service Request'
    :param data: Dictionary containing the fields for the child doctype
    :return: Response with success or error message
    """
    try:
        # before start we should check if mode test is enabled 
        if(is_test_mode_enabled() == False):
           return {"test_mode" : 0}
        
        # Fetch the most recent Split Service Request linked to the deed_id using Frappe ORM
        split_request = frappe.get_all(
            "Split Bank Request",
            filters={"deed_id": deed_id},
            fields=["name", "submission_date"],
            order_by="submission_date desc",
            limit=1
        )

        if not split_request:
            return {
                "status": False,
                "message": "No Split Service Request found for the provided Deed ID"
            }

        split_request_id = split_request[0]["name"]

        # Fetch the parent Split Service Request document
        split_request_response_item = frappe.get_doc("Split Bank Request Response Item",{"parent" : split_request_id , "status" : "Pending" } )


        # Validate input data
        required_fields = [
            "negociated_due_amount", "new_mortgage_end_date",
            "mortgage_start_payment_date"
        ]

        for field in required_fields:
            if field not in data:
                    frappe.local.response.http_status_code = 404
                    return {
                        "status": False,
                        "message": "Missing required field: {field}"
                    }
        print("ssssssssssss  ,  " , data["new_mortgage_end_date"])
        split_request_response_item.status = "Waiting For Customer Validation"
        split_request_response_item.negociated_due_amount = int(data["negociated_due_amount"]) 
        split_request_response_item.new_mortgage_end_date = data["new_mortgage_end_date"]
        split_request_response_item.mortgage_start_payment_date = data["mortgage_start_payment_date"]
        split_request_response_item.type = "Update"
        split_request_response_item.mortgage_installement = (int(data["negociated_due_amount"]) / 10) / 12
        split_request_response_item.mortgage_number_months = data["mortgage_number_months"]
        split_request_response_item.mortgage_duration = 10
        split_request_response_item.offer_date = frappe.utils.now_datetime()
        split_request_response_item.save(ignore_permissions=True)

        # Create a new child item
        # child_item = {
        #     "negociated_due_amount": data["negociated_due_amount"],
        #     "new_mortgage_end_date": data["new_mortgage_end_date"],
        #     "mortgage_start_payment_date": data["mortgage_start_payment_date"],
        #     # "mortgage_installement": data["mortgage_installement"],
        #      "type":"Update",
        #     "status": "Waiting For Customer Validation",
        #     "mortgage_number_months": 10,
        #     "mortgage_duration": 10,
        #     # "smr_id": data["smr_id"],
        #     # "smr_bank_id": data["smr_bank_id"],
        #     "offer_date": frappe.utils.now_datetime()
        # }

        frappe.db.commit()

        return {
            "status": "success",
            "message": _("Child item inserted successfully"),
            "split_request_id": split_request_id
        }

    except Exception as e:
        frappe.local.response.http_status_code = 404
        return {
            "status": False,
            "message": str(e)
        }



@frappe.whitelist()
def insert_loan_bank_request_item( deed_id, data):
    """
    Inserts a new child item into 'Bank Loan Request Response Item' linked to a 'Bank Loan Request'.

    :param deed_id: ID of the deed linked to the 'Loan Service Request'
    :param data: Dictionary containing the fields for the child doctype
    :return: Response with success or error message
    """
    try:
        # before start we should check if mode test is enabled 
        if(is_test_mode_enabled() == False):
           return {"test_mode" : 0}
        
        # Fetch the most recent Loan Service Request linked to the deed_id using Frappe ORM
        loan_request = frappe.get_all(
            "Bank Loan Request",
            filters={"deed_id": deed_id},
            fields=["name", "submission_date"],
            order_by="submission_date desc",
            limit=1
        )

        if not loan_request:
            return {
                "status": False,
                "message": "No Bank Loan Request found for the provided Deed ID"
            }

        loan_request_id = loan_request[0]["name"]

        # Fetch the parent Loan Service Request document
        loan_request_response_item = frappe.get_doc("Bank Loan Request Offer Item",{"parent" : loan_request_id , "status" : "Pending" } )


        # Validate input data
        required_fields = [
            "negociated_due_amount", "new_mortgage_end_date","bank_equity_percent",
            "mortgage_start_payment_date"
        ]

        for field in required_fields:
            if field not in data:
                    frappe.local.response.http_status_code = 404
                    return {
                        "status": False,
                        "message": "Missing required field: {field}"
                    }
        loan_request_response_item.status = "Waiting For Customer Validation"
        loan_request_response_item.negociated_loan_amount = int(data["negociated_due_amount"]) 
        loan_request_response_item.offered_equity = int(data["bank_equity_percent"]) 
        loan_request_response_item.new_mortgage_end_date = data["new_mortgage_end_date"]
        loan_request_response_item.mortgage_start_payment_date = data["mortgage_start_payment_date"]
        loan_request_response_item.mortgage_installement = (int(data["negociated_due_amount"]) / 10) / 12
        loan_request_response_item.mortgage_number_months = data["mortgage_number_months"]
        loan_request_response_item.mortgage_duration = 10
        loan_request_response_item.offer_date = frappe.utils.now_datetime()
        # TODO : loan_request_response_item.lba_bank_id = data["lba_bank_id"],
        loan_request_response_item.save(ignore_permissions=True)

        # Create a new child item
        # child_item = {
        #     "negociated_due_amount": data["negociated_due_amount"],
        #     "new_mortgage_end_date": data["new_mortgage_end_date"],
        #     "mortgage_start_payment_date": data["mortgage_start_payment_date"],
        #     # "mortgage_installement": data["mortgage_installement"],
        #      "type":"Update",
        #     "status": "Waiting For Customer Validation",
        #     "mortgage_number_months": 10,
        #     "mortgage_duration": 10,
        #     # "smr_id": data["smr_id"],
        #     # "smr_bank_id": data["smr_bank_id"],
        #     "offer_date": frappe.utils.now_datetime()
        # }
        # update status parent doctype
        loan_request_response_dt = frappe.get_doc("Bank Loan Request", loan_request_id)
        loan_request_response_dt.status="Waiting For Customer Validation"
        loan_request_response_dt.save(ignore_permissions=True) 
        
        frappe.db.commit()

        return {
            "status": "success",
            "message": _("Child item inserted successfully"),
            "loan_request_id": loan_request_id
        }

    except Exception as e:
        frappe.local.response.http_status_code = 404
        return {
            "status": False,
            "message": str(e)
        }


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