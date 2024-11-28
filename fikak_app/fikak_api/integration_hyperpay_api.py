import frappe
import requests
import json
from datetime import datetime , timedelta
from fikak_app.fikak_api.split_service_api import get_deed_active_split_service_request

@frappe.whitelist(methods=['GET'])
def get_payment_status(deed_id , checkout_id):
    try:
        deed_doc = frappe.get_doc("WATHEQ Deed", deed_id)
        if not deed_doc.deed_owner == frappe.session.user:
            frappe.local.response.http_status_code = 404
            return {
                "status": False,
                "message": "You are not authorized to view this deed"
            }
        hyperpay_request = frappe.get_doc("Hyperpay Request", {"checkout_id" : checkout_id , "requester" : frappe.session.user})
        evaluation_request = frappe.get_doc("Evaluation Request", {"request" : hyperpay_request.reference})


        if evaluation_request.status in ["Paid", "Not paid" ,"Done"]:
            status = "Paid" if evaluation_request.status in ["Paid", "Done"] else "Not paid"
            return {
                "status": True,
                "data": {
                    "status" : status
                }
            }
           
        # Fetch HyperPay settings
        settings = get_hyperpay_settings()
        endpoint = f"{settings['base_url']}/v1/checkouts/{checkout_id}/payment"
        headers = {
            "Authorization": f"Bearer {settings['access_token']}"
        }
        params  = {
            "entityId": settings['entity_id'],
        }

        response = requests.get(endpoint, headers=headers, params =params )
        response_data = response.json()
        status = 'Error'

        if response_data.get("result", {}).get("code") == "000.100.110":
            status = "Paid"
        elif response_data.get("result", {}).get("code") == "000.200.000":
            status = "Pending"
        
        if status != "Pending":
            update_evaluation_request_status(evaluation_request , status)
            update_hyperpay_request_status(hyperpay_request , status , response_data)
            if status == "Paid":
                update_split_service_status(hyperpay_request.reference , status)
        
        
        return {
            "status": True,
            "data": {
                "status" : status
            }
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "status": False,
            "message": str(e),
        }

def update_split_service_status(split_service_d , status):
    try:
        split_service = frappe.get_doc("Split Service Request", split_service_d)
        split_service.status = status
        split_service.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        print(str(e))

    
def update_hyperpay_request_status(hyperpay_request , status , response_data):
    try:
        if status == "Error" : status = "Rejected" 
        hyperpay_request.status = status
        hyperpay_request.json_response = json.dumps(response_data)
        hyperpay_request.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        print(str(e))

def update_evaluation_request_status(evaluation_request , status):
    try:
        if status == "Error" : status = "Not paid" 

        evaluation_request.status = status
        
        evaluation_request.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        print(str(e))


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
        "access_token": settings.hyperpay_access_token,
        "callback_url" : settings.callback_url
    }

@frappe.whitelist(methods=['GET'])
def get_payment_methods():
    return {
        "status": True,
        "data" : frappe.get_all("Payment Method",
                                 fields=["name as method_id", "method_name", "method_code", "image"] 
                                 , filters={"is_enabled": 1} , order_by="method_order asc"),
        "description": "Payment methods retrieved successfully"
    }


@frappe.whitelist(methods=['POST'])
def initiate_widget_integration_payment(deed_id, split_service_request ,  currency="USD", payment_type="DB"):
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
    payment_history = get_payment_params_by_split_request(split_service_request)
    if payment_history:
        return {
            "status": "success",
            "data": {
                "id": payment_history.checkout_id,
                "integrity": payment_history.integrity,
                "callbackUrl": payment_history.callback_url
            },
        }

    # Fetch HyperPay settings
    settings = get_hyperpay_settings()
    amount = frappe.db.get_single_value("Fikak Settings", "evaluation_amount")
    amount = amount if amount else 1000
    endpoint = f"{settings['base_url']}/v1/checkouts"
    headers = {
        "Authorization": f"Bearer {settings['access_token']}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "entityId": settings['entity_id'],
        "amount": int(amount),
        "currency": currency,
        "paymentType": payment_type,
        "integrity": True,
    }

    try:
        # Send the request to HyperPay
        response = requests.post(endpoint, data=payload, headers=headers)
        response_data = response.json()
        response_data["callbackUrl"] = settings['callback_url'] + "?deed_id=" + deed_id
        if response.status_code != 200:
            frappe.local.response.http_status_code = 500
        
        split_service_request_id = get_deed_active_split_service_request(deed_id)
        insert_payment_history(split_service_request_id[0] , response_data['id'],
                               response_data['integrity'], settings['entity_id'] , "Split Service Request"
                                 , response_data["callbackUrl"])

        return {
            "status": "success" if response.status_code == 200 else "error",
            "data": response_data,
        }

    except Exception as e:
        # Log the error
        frappe.log_error(frappe.get_traceback(), "HyperPay Payment Error")
        frappe.local.response.http_status_code = 500
        return {
            "status": "error",
            "message": str(e),
        }
    
def get_payment_params_by_split_request(request_id , filter_by_date = True):
    
    # Calculate the timestamp for 10 minutes ago
    current_time = datetime.strptime(frappe.utils.now(), "%Y-%m-%d %H:%M:%S.%f")
    ten_minutes_ago = current_time - timedelta(minutes=10)
    filters = {
        "reference": request_id,
        "requester" : frappe.session.user,
        "source": "Split Service Request"
    }
    if filter_by_date:
        filters["creation"] = [">=", ten_minutes_ago.strftime('%Y-%m-%d %H:%M:%S')]
    try:
        doc = frappe.get_doc(
            "Hyperpay Request",
            filters
        )
        return doc
    except Exception as e:
        return None
    

def insert_payment_history(reference ,checkout_id, entity ,integrity , source , callback_url):
    try:
        frappe.get_doc({
            "doctype": "Hyperpay Request",
            "requester" : frappe.session.user,
            "callback_url" : callback_url,
            "integrity" : integrity,
            "entity_id" : entity,
            "source" : source,
            "checkout_id" : checkout_id,
            "date" : datetime.now(), 
            "reference" : reference,

        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        print(str(e))


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
