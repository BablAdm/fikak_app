

import frappe
import requests
from frappe import _
import math


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
        #Get  intent request
        intent_request = frappe.get_doc("TARABUT Intent Request", {"intent_id": intentId})
        # Insert a new document in TARABUT Callback
        doc = frappe.get_doc({
            "doctype": "TARABUT Callback",
            "intent_id": intentId,
            "status": status
        })
        doc.insert(ignore_permissions=True)  # Ignore permissions if necessary
        update_intent_request(intentId, doc.name, status)  # Update the intent request
        get_user_bank_accounts_from_tarabut(intentId , intent_request.user)
        update_deed_workflow_step(3)
        frappe.db.commit()  # Commit the transaction
        return {"message": _("Data inserted successfully in TARABUT Callback"), "status": True}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Error in TARABUT Webhook"))
        frappe.local.response["http_status_code"] = 500
        return {"message": _("Failed to insert data error" + str(e) ), "status": False}


def update_deed_workflow_step(step):
    """
    Update the deed workflow status.

    This function updates the deed workflow status in the database.

    Args:
        deed_id (str): The deed ID.
        status (str): The status of the deed.
    """
    try:
        doc = frappe.get_doc("WATHEQ Deed", {"workflow_state": "NEW" , "deed_owner" : frappe.session.user})
        doc.wizard_step = step
        doc.save(ignore_permissions=True)
    except Exception as e:
        return None
    
def get_user_bank_accounts_from_tarabut(intent_id , user):
    """
    Get the user's bank accounts from the GO1 platform.

    This function retrieves the user's bank accounts from the GO1 platform.

    Returns:
        dict: The response from the GO1 platform.

    Raises:
        Exception: If an error occurs during the GET request.
    """

    # Get the client ID and client secret from the Integration setup
    tarabut_settings = frappe.get_single('TARABUT Settings')
    endpoint = tarabut_settings.api_url
    api_token = tarabut_settings.api_token
    client_id = tarabut_settings.get_password('client_id')
    client_secret = tarabut_settings.get_password('client_secret')
    customer_user_id = tarabut_settings.customer_user_id

    access_token = generate_access_token(api_token, client_id, client_secret , customer_user_id)

    if access_token:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.get(f"{endpoint}/accountInformation/v2/accounts", headers=headers)
            if response.status_code == 200:
                intent =  get_consent_by_intent_id(endpoint , access_token , intent_id)
                bank_accounts = get_bank_accounts_by_intent(intent.get("consentId") , response.json().get("accounts"))
                frappe.enqueue(insert_bank_accounts , bank_accounts = bank_accounts , user = user ,queue="long")
                return {
                    "message": "User bank accounts retrieved successfully",
                    "data": bank_accounts
                }
            else:
                frappe.logger().error(f"An error occurred on get user bank accounts from tarabut: {response.text}")
                frappe.local.response["http_status_code"] = response.status_code
                return {
                    "message": response.text,
                    "status": False
                }

        except Exception as e:
            frappe.logger().error(f"An error occurred on get user bank accounts from tarabut: {response.text}")
            frappe.local.response["http_status_code"] = 500
            return {
                "message": str(e),
                "status": False
            }
    else:
        frappe.logger().error(f"An error occurred on get user bank accounts from tarabut: Access token not generated")
        frappe.local.response["http_status_code"] = 404
        return {
            "message": "Access token not generated",
            "status": False
        }

def get_consent_by_intent_id(endpoint , access_token , intent_id):
    """
    Get the consent by intent ID.

    This function retrieves the consent by intent ID.

    Args:
        access_token (str): The access token.
        intent_id (str): The intent ID.

    Returns:
        dict: The consent by intent ID.
    """

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(f"{endpoint}/accountInformation/v1/intent/{intent_id}", headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            frappe.logger().error(f"An error occurred on get user bank accounts from tarabut: {response.text}")
            frappe.local.response["http_status_code"] = response.status_code
            return {
                "message": response.text,
                "status": False
            }

    except Exception as e:
        frappe.logger().error(f"An error occurred on get user bank accounts from tarabut: {response.text}")
        frappe.local.response["http_status_code"] = 500
        return {
            "message": str(e),
            "status": False
        }


def get_bank_accounts_by_intent(consent_id , bank_accounts):
    """
    Get the bank accounts by intent.

    This function retrieves the bank accounts by intent.

    Args:
        intent_id (str): The intent ID.
        bank_accounts (list): The bank accounts list.

    Returns:
        list: The bank accounts by intent.
    """
    filtered_accounts = [
            account for account in bank_accounts
            if any((consent.get("id") == consent_id and consent.get("status") == "ACTIVE") for consent in account.get("consents", []))
        ]

    return filtered_accounts

def insert_bank_accounts(bank_accounts , user):
    """
    Insert the bank accounts.

    This function inserts the bank accounts in the database.

    Args:
        intent_id (str): The intent ID.
    """
    
    for account in bank_accounts:
        if frappe.db.exists("Bank Account Details", {"account_id": account.get("accountId") , "user": frappe.session.user}):
            continue
        bank_provider = frappe.db.exists("Bank Provider", {"bank_code": account.get("providerId")})
        if not bank_provider:
            bank_provider_doc = frappe.get_doc({
                "doctype": "Bank Provider",
                "bank_name": account.get("providerId"),
                "bank_code": account.get("providerId"),
            })
            bank_provider_doc.insert(ignore_permissions=True)
            bank_provider = bank_provider_doc.name
            frappe.db.commit()
        doc = frappe.get_doc({
            "doctype": "Bank Account Details",
            "user": user,
            "account_id": account.get("accountId"),
            "account_holder_name": account.get("accountHolderName"),
            "account_product_type": account.get("accountProductType"),
            "account_description": account.get("accountDescription"),
            "bank_provider": bank_provider,
            "identifiers" : [{"type": identifier.get("type"), "value": identifier.get("value")} for identifier in account.get("identifiers")],
            "balances" : [{"type": balance.get("type"), "amount": balance.get("amount").get("value"), "currency": balance.get("amount").get("currency")} for balance in account.get("balances")],
            "links" : [{"rel": link.get("rel"), "link": link.get("href")} for link in account.get("links")],
            "consents" : [{"consent_id": consent.get("id"), "expiry_date": consent.get("expiryDate"), "status": consent.get("status")} for consent in account.get("consents")],
            "last_updated_date_time": account.get("lastUpdatedDateTime"),
            "last_balances_update_datetime" : account.get("meta").get("lastBalancesUpdateDatetime"),
            "last_account_update_date_time" : account.get("meta").get("lastAccountUpdateDatetime")
            
        })
        doc.insert(ignore_permissions=True)
        
        # frappe.enqueue(get_tarabut_account_transactions , bank_account_id = account.get("accountId") , user = user ,queue="long")
        frappe.db.commit()


@frappe.whitelist(allow_guest=True)
def get_my_bank_accounts():
    """
    Get the user's bank accounts.

    This function retrieves the user's bank accounts from the GO1 platform.

    Returns:
        dict: The response from the GO1 platform.

    Raises:
        Exception: If an error occurs during the GET request.
    """

    # Get the client ID and client secret from the Integration setup
    accounts = get_accounts(frappe.session.user)
    return accounts

def get_accounts(user):
    bank_accounts_details_dt = frappe.qb.DocType("Bank Account Details")
    bank_provider_dt = frappe.qb.DocType("Bank Provider")
    bank_balances = frappe.qb.DocType("Bank Account Details Balance Item")

    bank_accounts_query = (
        frappe.qb.from_(bank_accounts_details_dt)
        .inner_join(bank_provider_dt)
        .on(bank_accounts_details_dt.bank_provider == bank_provider_dt.name)
        .inner_join(bank_balances)
        .on(bank_accounts_details_dt.name == bank_balances.parent)
        .select(
            bank_accounts_details_dt.name.as_("bank_account_details_id"),
            bank_accounts_details_dt.account_id,
            bank_accounts_details_dt.account_holder_name,
            bank_accounts_details_dt.account_product_type,
            bank_accounts_details_dt.account_description,
            bank_provider_dt.name.as_("bank_provider_id"),
            bank_provider_dt.bank_name,
            bank_provider_dt.bank_code,
            bank_provider_dt.logo,
            bank_balances.type,
            bank_balances.amount,
            bank_balances.currency
        )
        .where(bank_accounts_details_dt.user == user)
    )
    
    bank_accounts = bank_accounts_query.run(as_dict=True)
    return {
        "data": bank_accounts,
        "status": True,
        "message": _("Bank accounts retrieved successfully")
    }

@frappe.whitelist(methods="GET")
def get_intent_status(intent_id):
    try:
        intent_request = frappe.get_doc("TARABUT Intent Request", {"intent_id": intent_id , "user" : frappe.session.user})
        return {
            "message" : "Intent status retrieved successfully",
            "data" : {
                "status" : intent_request.status
            },
            "status": True
        }
    except frappe.DoesNotExistError:
        frappe.local.response["http_status_code"] = 404
        return {
            "message": _("Intent not found"),
            "status": False
        }
    
@frappe.whitelist(methods="GET")
def get_tarabut_account_transactions(bank_account_id , user):
    """
    Get the user's account transactions.

    This function retrieves the user's account transactions from the GO1 platform.

    Args:
        bank_account_id (str): The bank account ID.

    Returns:
        dict: The response from the GO1 platform.

    Raises:
        Exception: If an error occurs during the GET request.
    """

    # Get the client ID and client secret from the Integration setup
    tarabut_settings = frappe.get_single('TARABUT Settings')
    endpoint = tarabut_settings.api_url
    api_token = tarabut_settings.api_token
    client_id = tarabut_settings.get_password('client_id')
    client_secret = tarabut_settings.get_password('client_secret')
    customer_user_id = tarabut_settings.customer_user_id

    access_token = generate_access_token(api_token, client_id, client_secret , customer_user_id)

    if access_token:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.get(f"{endpoint}/accountInformation/v2/accounts/{bank_account_id}/transactions", headers=headers)
            if response.status_code == 200:
                frappe.enqueue(insert_bank_account_transactions , bank_account = bank_account_id \
                             , transactions = response.json().get("transactions") , user = user ,queue="long")
                return {
                    "message": "User account transactions retrieved successfully",
                    "data": response.json()
                }
            else:
                frappe.logger().error(f"An error occurred on get user account transactions: {response.text}")
                frappe.local.response["http_status_code"] = response.status_code
                return {
                    "message": response.text,
                    "status": False
                }

        except Exception as e:
            frappe.logger().error(f"An error occurred on get user account transactions: {response.text}")
            frappe.local.response["http_status_code"] = 500
            return {
                "message": str(e),
                "status": False
            }
    else:
        frappe.logger().error(f"An error occurred on get user account transactions: Access token not generated")
        frappe.local.response["http_status_code"] = 404
        return {
            "message": "Access token not generated",
            "status": False
        }


def insert_bank_account_transactions(bank_account , transactions, user):
    """
    Insert the bank account transactions.

    This function inserts the bank account transactions in the database.

    Args:
        bank_account (str): The bank account.
        transactions (list): The bank account transactions list.
    """

    for transaction in transactions:
        bank_account_id = frappe.get_doc("Bank Account Details", {"account_id" : bank_account}).name
        if frappe.db.exists("Account Transaction", {"transaction_id": transaction.get("transactionId") , "account_id": bank_account_id}):
            continue

        bank_provider = frappe.db.exists("Bank Provider", {"bank_code": transaction.get("providerId")})
        if not bank_provider:
            bank_provider_doc = frappe.get_doc({
                "doctype": "Bank Provider",
                "bank_name": transaction.get("providerId"),
                "bank_code": transaction.get("providerId"),
            })
            bank_provider_doc.insert(ignore_permissions=True)
            bank_provider = bank_provider_doc.name
        category = frappe.db.exists("Transaction Category", {"category_name": transaction.get("category").get("name")})
        if not category:
            category_doc = frappe.get_doc({
                "doctype": "Transaction Category",
                "category_name": transaction.get("category").get("name"),
                "category_group": transaction.get("category").get("group"),
                "icon": transaction.get("category").get("icon")
            })
            category_doc.insert(ignore_permissions=True)
            category = category_doc.name
        merchant = frappe.db.exists("Transaction Merchant", {"merchant_category_code": transaction.get("merchant").get("merchantCategoryCode")})
        if not merchant:
            merchant_doc = frappe.get_doc({
                "doctype": "Transaction Merchant",
                "merchant_name": transaction.get("merchant").get("name"),
                "merchant_category_code": transaction.get("merchant").get("merchantCategoryCode"),
                "logo": transaction.get("merchant").get("logo")
            })
            merchant_doc.insert(ignore_permissions=True)
            merchant = merchant_doc.name
        doc = frappe.get_doc({
            "doctype": "Account Transaction",
            "account_id": bank_account_id,
            "user" : user,
            "transaction_id": transaction.get("transactionId"),
            "account_product_type": transaction.get("accountProductType"),
            "bank_provider": bank_provider,
            "transaction_description": transaction.get("transactionDescription"),
            "transaction_category": category,
            "merchant": merchant,
            "credit_debit_indicator": transaction.get("creditDebitIndicator"),
            "amount": transaction.get("amount"),
            "currency": transaction.get("amount").get("currency"),
            "booking_date_time": transaction.get("bookingDateTime")
        })
        doc.insert(ignore_permissions=True)
    frappe.db.commit()

@frappe.whitelist(methods="GET")
def check_elgibility_status(request_id , offset = 0 , page_size = 10 , order_direction = -1 , order_by = "creation"):
    try:
        if isinstance(offset, str):
            offset = int(offset)
    
        if isinstance(page_size, str):
            page_size = int(page_size)
        request = frappe.get_doc("Eligibility Check Request" , request_id)
        if request.user != frappe.session.user:
            frappe.local.response["http_status_code"] = 403
            return {
                "message": _("You are not allowed to access this request"),
                "status": False
            }
        requested_deeds = frappe.get_all("Eligibility Check Request Deed Item" , 
                                         filters = {"parent" : request_id} , 
                                         fields = ["name as deed_request_id" , "deed_source" , "deed" , "total_interest_payment"
                                                    , "current_market_deed_price" , "total_principal_payment"
                                                    , "new_loan" , "loan_eligibility" , "split_eligibility" , "status" , "customer_equity"
                                                    ] 
                                         ,  start = offset , limit = page_size , order_by = "idx asc" )
        eligibility_results = []
        for requested_deed in requested_deeds:
            deed_object = frappe.get_doc(requested_deed.deed_source, requested_deed.deed)
            if requested_deed.status == "NEW":
                fikak_settings = frappe.get_single("Fikak Settings")
                eligibity_check = fikak_settings.eligibity_check
                max_new_loan = fikak_settings.max_new_loan
                waseera_fees = fikak_settings.waseera_fees
                #Compute customer total paid amount
                customer_total_deed_payment = deed_object.get("down_price") + requested_deed.get("total_principal_payment")
                
                loan_eligibility = split_eligibility = loan_bba = None

                if requested_deed.get("current_market_deed_price") and deed_object.get("deed_price"):
                    loan_eligibility = split_eligibility = False
                    #Compute total amount due to bank
                    total_due_to_bank = deed_object.get("deed_price") + deed_object.get("interest_amount") - deed_object.get("down_price")\
                                            - (requested_deed.get("total_interest_payment") + requested_deed.get("total_principal_payment"))
                    #Compute bank equity from new market price
                    bank_equity_from_new_price = total_due_to_bank / requested_deed.get("current_market_deed_price") if requested_deed.get("current_market_deed_price") > 0 else 0
                    
                    #Compute customer equity from new market price
                    customer_equity_new_price = 1 - bank_equity_from_new_price
                    
                    
                    split_eligibility = True if customer_equity_new_price > eligibity_check / 100 else False
                    if total_due_to_bank == 0 :
                        loan_eligibility = True
                        split_eligibility = False
                    if split_eligibility or loan_eligibility:
                        loan_bba = (requested_deed.get("current_market_deed_price") * customer_equity_new_price )* \
                        (max_new_loan /100) * (1 - (waseera_fees / 100))
                request_deed_item_doc = frappe.get_doc("Eligibility Check Request Deed Item" , requested_deed.deed_request_id)
                status = "Not Eligible"
                if loan_eligibility: status = "Eligible For Loan"
                if split_eligibility: status = "Eligible For Split"
                
                request_deed_item_doc.status = status
                if loan_eligibility: request_deed_item_doc.loan_eligibility = loan_eligibility
                if split_eligibility: request_deed_item_doc.split_eligibility = split_eligibility
                if loan_bba: request_deed_item_doc.new_loan = loan_bba
                if customer_equity_new_price: request_deed_item_doc.customer_equity = customer_equity_new_price
                if bank_equity_from_new_price: request_deed_item_doc.bank_equity = bank_equity_from_new_price
                
                request_deed_item_doc.save(ignore_permissions=True)
            else:
                loan_eligibility = requested_deed.get("loan_eligibility")
                split_eligibility = requested_deed.get("split_eligibility")
                loan_bba = requested_deed.get("new_loan")
                    
            eligibility_results.append({
                "deed_number" : deed_object.deed_number,
                "deed_serial" : deed_object.deed_serial,
                "deed_city" : deed_object.real_estate_details[0].city_name,
                "deed_area" : deed_object.deed_area,
                "deed_status" : deed_object.deed_status,
                "last_price_registred" : deed_object.deed_price,
                "bursa_price" : requested_deed.get("current_market_deed_price"),
                "equity_percent" : requested_deed.get("customer_equity") if requested_deed.status != "NEW" else customer_equity_new_price * 100,
                "loan_bba" : loan_bba,
                "loan_eligibility" : loan_eligibility,
                "split_eligibility" : split_eligibility,
            })
            
        frappe.db.commit()

    except Exception as e:
        frappe.local.response["http_status_code"] = 404
        return{
            "status:" : False,
            "message" : str(e),
        }

    return {
        "message" : "Success",
        "status:" : True,
        "data" : eligibility_results,
        "meta": {
            "current_page": int((offset/page_size)+1),
            "total_items": len(request.requested_deeds),
            "items_per_page": page_size,
            "total_pages": math.ceil(len(request.requested_deeds) / page_size)
        },
        
    }