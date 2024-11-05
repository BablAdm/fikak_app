

import frappe
import requests

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
                return {
                    "message": "Intent created successfully",
                    "data": response.json(),
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
