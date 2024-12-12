

import frappe
import requests


def release_mortgage_request_api(mortgage_registration_request_id):
    """
    Sends data to an external API using information from the 
    'Mortgage Registration Request' doctype.
    """
    try:
        # Fetch the Mortgage Registration Request document
        mortgage_request = frappe.get_doc("Mortgage Registration Request", mortgage_registration_request_id)

        # Retrieve user data
        person_data = frappe.get_doc("Person Data", frappe.session.user)

        # Prepare the payload based on the document fields
        payload = {
                "deedNumber": mortgage_request.deed_id,
                "ownerNationalId": person_data.nin,
                "ownerDobHijri": person_data.birth_date, # TODO : see the hidjri date
                "ownerMobileNumber": person_data.phone_number,
                "requestId": mortgage_request.name,
                "courtCode": mortgage_request.court_code, # TODO : hwo to get this info
                "consumerNationalId": person_data.nin, # TODO : see the diff betwen user and consumer 
                "consumerDobHijri":  person_data.birth_date, 
                }

        # API configuration
        url = "https://apidev.test.com/api/v1/Request/ReleaseMortgage"  # TODO : Replace with the actual API URL
        headers = {"Content-Type": "application/json"}

        # Send the POST request
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        # Handle the response
        response_data = response.json()
        if response_data.get("isSuccess"):
            data = response_data.get("data", {})
            if data.get("isDeedUpdated"):
                # Update the status field in the Mortgage Registration Request
                mortgage_request.db_set("status", "Released", commit=True)
                return {
                    "status": "success",
                    "message": "Data sent successfully. Status updated to 'Updated'.",
                    "response": response_data,
                }
            else:
                return {
                    "status": "warning",
                    "message": "Data sent successfully, but deed is not updated.",
                    "response": response_data,
                }
        else:
            return {
                "status": "error",
                "message": "API returned an error.",
                "error_list": response_data.get("errorList", []),
                "response": response_data,
            }

    except requests.exceptions.RequestException as e:
        frappe.log_error(frappe.get_traceback(), _("External API Error"))
        return {"status": "error", "message": str(e)}
    except frappe.DoesNotExistError:
        return {"status": "error", "message": "Mortgage Registration Request not found."}
    
 
    
def create_mortgage_request_api(mortgage_registration_request_id):
    """
    Sends data to an external API using information from the 
    'Mortgage Registration Request' doctype.
    """
    try:
        # Fetch the Mortgage Registration Request document
        mortgage_request = frappe.get_doc("Mortgage Registration Request", mortgage_registration_request_id)

        # Retrieve user data
        person_data = frappe.get_doc("Person Data", frappe.session.user)

        # Prepare the payload based on the document fields
        payload = {
            "deedNumber": mortgage_request.deed_id,
            "ownerNationalId": person_data.nin,
            "ownerDobHijri": person_data.birth_date, # TODO : see the hidjri date
            "ownerMobileNumber": person_data.phone_number,
            "consumerNationalId": mortgage_request.consumer_national_id,
            "consumerDobHijri": mortgage_request.birth_date, # TODO : see the hidjri date
            "requestId": mortgage_request.name,
            "courtCode": mortgage_request.court_code, # TODO : hwo to get this info
            "mortgageeType": mortgage_request.mortgagee_type, # TODO : hwo to get this info
            "mortgageeId": mortgage_request.mortgagee_id,
            "mortgageAmount": mortgage_request.due_amount,
            "firstPaymentDate": mortgage_request.start_payment_date,
            "lastPaymentDate": mortgage_request.end_date,
            "numberOfInstallments": mortgage_request.number_months,
            "installmentAmount": mortgage_request.installement,
            "upfrontPayment": mortgage_request.upfront_payment or 0,
            "lastPayment": mortgage_request.last_payment or 0,
        }

        # API configuration
        url = "https://apidev.test.com/api/v1/Request/Mortgage"  # TODO : Replace with the actual API URL
        headers = {"Content-Type": "application/json"}

        # Send the POST request
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        # Handle the response
        response_data = response.json()

        if response_data.get("isSuccess"):
            data = response_data.get("data", {})
            if data.get("isDeedUpdated"):
                # Update the status field in the Mortgage Registration Request
                mortgage_request.db_set("status", "Registred", commit=True)
                return {
                    "status": "success",
                    "message": "Data sent successfully. Status updated to 'Updated'.",
                    "response": response_data,
                }
            else:
                return {
                    "status": "warning",
                    "message": "Data sent successfully, but deed is not updated.",
                    "response": response_data,
                }
        else:
            return {
                "status": "error",
                "message": "API returned an error.",
                "error_list": response_data.get("errorList", []),
                "response": response_data,
            }

    except requests.exceptions.RequestException as e:
        frappe.log_error(frappe.get_traceback(), _("External API Error"))
        return {"status": "error", "message": str(e)}
    except frappe.DoesNotExistError:
        return {"status": "error", "message": "Mortgage Registration Request not found."}


# TODO : We keep this code in case of Async Response
def handle_hook_response(mortgage_request_id, response):
    """
    Updates the status of the Mortgage Registration Request based on the external API response.
    """
    try:
        # Fetch the Mortgage Registration Request
        mortgage_request = frappe.get_doc("Mortgage Registration Request", mortgage_request_id)

       

        # Handle the response
        response_data = response.json()

        if response_data.get("isSuccess"):
            data = response_data.get("data", {})
            if data.get("isDeedUpdated"):
                # Update the status field in the Mortgage Registration Request
                mortgage_request.db_set("status", "Registred", commit=True)
                return {
                    "status": "success",
                    "message": "Data sent successfully. Status updated to 'Updated'.",
                    "response": response_data,
                }
            else:
                return {
                    "status": "warning",
                    "message": "Data sent successfully, but deed is not updated.",
                    "response": response_data,
                }
        else:
            return {
                "status": "error",
                "message": "API returned an error.",
                "error_list": response_data.get("errorList", []),
                "response": response_data,
            }        
        

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Hook Response Error"))
        return {"status": "error", "message": str(e)}