import frappe
import requests
import json
from datetime import datetime


def get_hyperpay_settings():
    """
    Fetches HyperPay configuration from the Hyperpay Settings Doctype.
    Returns:
        dict: Configuration containing base URL, access token, and enabled status.
    """
    settings = frappe.get_doc("Hyperpay Settings", "Hyperpay Settings")
    if not settings.enabled:
        frappe.throw("HyperPay integration is disabled. Please enable it in the Hyperpay Settings.")
    
    return {
        "base_url": settings.hyperpay_base_url,
        "entity_id": settings.entity_id,
        "access_token": settings.hyperpay_access_token
    }

@frappe.whitelist(allow_guest=False)
def initiate_widget_integration_payment(deed_name, amount, currency="USD", payment_type="DB"):
    """
    Initiates a WI payment request with HyperPay and logs the request and response in Frappe.
    Args:
        request_id (str): Unique transaction ID
        amount (float): Payment amount
        currency (str): Currency code, default is 'USD'
        payment_type (str): Payment type, default is 'DB' (debit)
    Returns:
        dict: Response from HyperPay
    """
    # Fetch HyperPay settings
    settings = get_hyperpay_settings()

    endpoint = f"{settings['base_url']}/v1/checkouts"
    headers = {
        "Authorization": f"Bearer {settings['access_token']}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "entityId": settings['entity_id'],
        "amount": str(amount),
        "currency": currency,
        "paymentType": payment_type,
        "integrity": True,
    }

    try:
        # Log the request payload
        log = frappe.get_doc({
            "doctype": "Hyperpay Widget Integration Request",
            "entity_id": settings['entity_id'],
            "request_id": deed_name,
            "request_payload": json.dumps(payload),
            "request_status": "Pending",
            "date": datetime.now(),
        })
        log.insert(ignore_permissions=True)

        # Send the request to HyperPay
        response = requests.post(endpoint, data=payload, headers=headers)
        response_data = response.json()


        # Update the log with the response
        log.response_data = json.dumps(response_data)
        log.status = "Success" if response.status_code == 200 else "Failed"
        log.save(ignore_permissions=True)
        
        response_data["checkoutId"]=deed_name
        # Return the response to the client
        return {
            "status": "success" if response.status_code == 200 else "error",
            "data": response_data,
        }

    except Exception as e:
        # Log the error
        log.status = "Failed"
        log.response_data = json.dumps({"error": str(e)})
        log.save(ignore_permissions=True)
        frappe.log_error(frappe.get_traceback(), "HyperPay Payment Error")

        return {
            "status": "error",
            "message": str(e),
        }

@frappe.whitelist(allow_guest=True)
def initiate_server_to_server_payment(transaction_id, amount, currency="USD", payment_type="DB"):
    """
    Initiates a STS payment request with HyperPay and logs the request and response in Frappe.
    Args:
        transaction_id (str): Unique transaction ID
        amount (float): Payment amount
        currency (str): Currency code, default is 'USD'
        payment_type (str): Payment type, default is 'DB' (debit)
    Returns:
        dict: Response from HyperPay
    """
    # Fetch HyperPay settings
    settings = get_hyperpay_settings()

    endpoint = f"{settings['base_url']}/v1/payments"
    headers = {
        "Authorization": f"Bearer {settings['access_token']}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "entityId": settings['entity_id'], 
        "amount": str(amount),
        "currency": currency,
        "paymentType": payment_type,
        "merchantTransactionId": transaction_id,
    }

    try:
        # Log the request payload
        log = frappe.get_doc({
            "doctype": "HyperPay Log",
            "transaction_id": transaction_id,
            "request_payload": json.dumps(payload),
            "status": "Pending",
            "timestamp": datetime.now(),
        })
        log.insert(ignore_permissions=True)

        # Send the request to HyperPay
        response = requests.post(endpoint, data=payload, headers=headers)
        response_data = response.json()

        # Update the log with the response
        log.response_data = json.dumps(response_data)
        log.status = "Success" if response.status_code == 200 else "Failed"
        log.save(ignore_permissions=True)

        # Return the response to the client
        return {
            "status": "success" if response.status_code == 200 else "error",
            "data": response_data,
        }

    except Exception as e:
        # Log the error
        log.status = "Failed"
        log.response_data = json.dumps({"error": str(e)})
        log.save(ignore_permissions=True)
        frappe.log_error(frappe.get_traceback(), "HyperPay Payment Error")

        return {
            "status": "error",
            "message": str(e),
        }


@frappe.whitelist(allow_guest=True)
def get_server_to_server_payment_status(checkout_id):
    """
    Retrieves the payment status from HyperPay.
    Args:
        checkout_id (str): The checkout ID from HyperPay
    Returns:
        dict: Response from HyperPay
    """
    # Fetch HyperPay settings
    settings = get_hyperpay_settings()

    endpoint = f"{settings['base_url']}/v1/checkouts/{checkout_id}/payment"
    headers = {
        "Authorization": f"Bearer {settings['access_token']}"
    }

    try:
        response = requests.get(endpoint, headers=headers)
        response_data = response.json()

        return {
            "status": "success" if response.status_code == 200 else "error",
            "data": response_data,
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "HyperPay Payment Status Error")
        return {
            "status": "error",
            "message": str(e),
        }
