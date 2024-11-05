

import frappe
import requests
from frappe import _


def generate_access_token(endpoint, client_id, client_secret, customer_id):
    """
    Generate the access token.

    This function retrieves the client ID and client secret from the Integration setup and sends a POST request to the GO1 OAuth token endpoint to obtain an access token. The access token is then returned.

    Returns:
        str: The access token if the POST request is successful, None otherwise.

    Raises:
        Exception: If an error occurs during the POST request.
    """

    data = {
        'clientId': client_id,
        'clientSecret': client_secret,
        'grantType': "client_credentials"
    }
    headers = {
        'Content-Type': 'application/json',
        'X-TG-CustomerUserId' : customer_id
    }

    try:
        response = requests.post(f"{endpoint}", json=data , headers=headers)
        if response.status_code == 200:
            access_token = response.json().get('accessToken')
            return access_token
        else:
            frappe.logger().error(f"An error occurred on generate access token: {response.text}")
            return None

    except Exception as e:
        frappe.logger().error(f"An error occurred on generate access token: {response.text}")
        return None
    
@frappe.whitelist()
def create_intent():
    """
    Create an intent.

    This function creates an intent in the GO1 platform. The intent is used to track the user's interaction with the platform.

    Returns:
        dict: The response from the GO1 platform.

    Raises:
        Exception: If an error occurs during the POST request.
    """

    # Get the client ID and client secret from the Integration setup
    tarabut_settings = frappe.get_single('TARABUT Settings')
    endpoint = tarabut_settings.api_url
    api_token = tarabut_settings.api_token
    client_id = tarabut_settings.get_password('client_id')
    client_secret = tarabut_settings.get_password('client_secret')
    redirect_url = tarabut_settings.get_password('redirect_url')
    
    user_doc = frappe.get_doc('User', frappe.session.user)

    access_token = generate_access_token(api_token, client_id, client_secret , tarabut_settings.customer_user_id)

    if access_token:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        data ={ 
            'user' : {
                'customerUserId': tarabut_settings.customer_user_id,
                'firstName': user_doc.get("first_name"),
                "lastName": user_doc.get("last_name"),
                "email": user_doc.get("email")
            },
            "redirectUrl" : redirect_url,
        }
        try:
            response = requests.post(f"{endpoint}/accountInformation/v1/intent", headers=headers, json=data)
            if response.status_code in (201 , 200):
                result = response.json()
                insert_intent_request(result.get("intentId") , result.get("connectUrl") , result.get("expiry"))
                return {
                    "message": "Intent created successfully",
                    "data": result,
                    "status": True
                }
            else:
                frappe.local.response["http_status_code"] = response.status_code
                frappe.log_error(frappe.get_traceback(),"An error occurred on create intent : " + response.text)
                return {
                    "message": response.text,
                    "status": False
                }

        except Exception as e:
            frappe.log_error(frappe.get_traceback(),"An error occurred on create intent : " + str(e))
            return str(e)
    else:
        frappe.local.response["http_status_code"] = 500
        return {
            "message": "Access token not generated",
            "status": False
        }


def insert_intent_request(intent_id , connect_url , Expiry):
    """
    Insert the intent request in the database.

    This function inserts the intent request in the database.

    Args:
        user (str): The user who created the intent.
        intent_id (str): The intent ID.
        connect_url (str): The connect URL.
        Expiry (str): The expiry date of the intent.
    """

    doc = frappe.get_doc({
        "doctype": "TARABUT Intent Request",
        "user": frappe.session.user,
        "intent_id": intent_id,
        "connect_url": connect_url,
        "expiry": Expiry
    })

    doc.insert(ignore_permissions=True)
    frappe.db.commit()

def update_intent_request(intent_id , tarabut_callback, status):
    """
    Update the intent request in the database.

    This function updates the intent request in the database.

    Args:
        intent_id (str): The intent ID.
        status (str): The status of the intent.
    """

    doc = frappe.get_doc("TARABUT Intent Request", {"intent_id": intent_id})
    doc.status = status
    doc.tarabut_callback = tarabut_callback
    doc.save(ignore_permissions=True)
    frappe.db.commit()

@frappe.whitelist(allow_guest=True)
def handle_tarabut_webhook(intentId, status):
    """
    Endpoint to handle the TARABUT webhook by capturing intentId and status, and
    saving them in the TARABUT Callback Doctype.

    Args:
        intentId (str): The unique intent identifier from the webhook URL.
        status (str): The status of the intent, such as "SUCCESSFUL" or other values.
    """
    try:
        # Insert a new document in TARABUT Callback
        doc = frappe.get_doc({
            "doctype": "TARABUT Callback",
            "intent_id": intentId,
            "status": status
        })
        
        doc.insert(ignore_permissions=True)  # Ignore permissions if necessary
        update_intent_request(intentId, doc.name, status)  # Update the intent request
        frappe.db.commit()  # Commit the transaction

        return {"message": _("Data inserted successfully in TARABUT Callback"), "status": True}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Error in TARABUT Webhook"))
        return {"message": _("Failed to insert data"), "error": str(e), "status": False}