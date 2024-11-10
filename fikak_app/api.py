
import frappe
from frappe import _
import jwt
import datetime
from frappe.utils import now_datetime

EXPIRATION_TIME = 360000  # Token expiration time in seconds
SECRET_KEY = "FIKAK_LOGIN_SECRET_KEY"

@frappe.whitelist(methods=['GET'])
def get_user_info():
    try:
        user = frappe.get_doc("User", frappe.session.user)
        data = {
            "email": user.email,
            "full_name": user.full_name,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "user_image": user.user_image,
            "terms_submitted" : check_user_terms_and_conditions(frappe.session.user),
            "kyc_submitted" : check_kyc_submitted(frappe.session.user)
        }
        

        return {
            "status": True,
            "data": data,
            "message": _("User profile data retrieved successfully")
        }
    except frappe.DoesNotExistError:
        return {
            "status": False,
            "message": _("User not found")
        }

def check_kyc_submitted(user):
    enabled_kyc = frappe.db.exists("KYC", {"enabled": 1})
    if not enabled_kyc:
        return True
    return frappe.db.exists("KYC Submission", {"user": user, "kyc": enabled_kyc}) != None



def check_user_terms_and_conditions(user):
    """
    Check if the user has accepted the terms and conditions.

    Args:
    user (str): The name of the user.

    Returns:
    bool: True if the user has accepted the terms and conditions, False otherwise.
    """
    # Check if the user has accepted the terms and conditions
    enabled_terms_and_conditions = frappe.db.exists("Terms And Conditions", {"enabled": 1 , "type" : "General"})
    if not enabled_terms_and_conditions:
        return True
    
    return frappe.db.exists("Terms And Conditions Submission", {"user": user , "terms_and_conditions" : enabled_terms_and_conditions}) != None

@frappe.whitelist(allow_guest=True)
def custom_login(email, password):
    try:
        # Attempt to authenticate the user using Frappe's login manager
        login_manager = frappe.auth.LoginManager()
        login_manager.authenticate(user=email, pwd=password)

        login_manager.post_login()
        bearer_token = get_or_create_token(email)
        
        # If login is successful, return a success response
        return {
            "status": "success",
            "message": _("Logged In Successfully"),
            "user": frappe.session.user,
            "token" : bearer_token,
            "csrf_token" : frappe.sessions.get_csrf_token(),
            "session_id": frappe.session.sid  # Return the session ID
        }
    except frappe.exceptions.AuthenticationError:
        # If authentication fails, return an error
        frappe.clear_messages()
        frappe.local.response["http_status_code"] = 401
        return {
            "status": "error",
            "message": _("Invalid email or password")
        }
def get_or_create_token(user):
    # Query the OAuth Bearer Token DocType for an existing token
    existing_token = frappe.db.get_value(
        "OAuth Bearer Token",
        filters={
            "user": user
        },
        fieldname=["access_token", "expiration_time"]
    )

    # Check if a valid token exists and is not expired
    if existing_token:
        access_token, expiration_time = existing_token
        if expiration_time and expiration_time > now_datetime():
            return access_token  # Return existing valid token

    # If no valid token is found, generate a new one
    new_token = generate_jwt_token(user)[:130]
    store_bearer_token_in_frappe(user, new_token)
    return new_token

def generate_jwt_token(email):
    """
    Generate a JWT token containing the user's email and expiration time.
    """
    payload = {
        "email": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=EXPIRATION_TIME)
    }

    # Encode the payload with the secret key
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    return token

def store_bearer_token_in_frappe(user, token):
    """
    Store the generated JWT token in the OAuth Bearer Token DocType in Frappe.
    """
    # Get the current timestamp for token creation
    issued_at = frappe.utils.now()

    # Calculate token expiry (based on your token's expiration time)
    expiry = frappe.utils.add_to_date(issued_at, seconds=EXPIRATION_TIME)
    if not frappe.db.exists("User" , user):
        user = frappe.db.exists("User" , {"username" , user})
    # Insert a new Bearer Token entry in the OAuth Bearer Token DocType
    bearer_token = frappe.get_doc({
        "doctype": "OAuth Bearer Token",
        "access_token": token,  # The generated JWT token
        "user": user,  # The user for whom the token was generated
        "expires_in": EXPIRATION_TIME,  # Expiration time in seconds
        "issued_at": issued_at,  # When the token was created
        "scopes" : "all openid",
        "expiration_time": expiry,  # When the token will expire
    })

    # Save the new token
    bearer_token.insert(ignore_permissions=True)

    frappe.db.commit()  # Ensure the token is saved to the database
    return bearer_token.name


@frappe.whitelist(allow_guest=True)
def get_country_list():
    return frappe.get_all("Country" , fields=["name" , "country_name"])


@frappe.whitelist()
def get_timezones():
	import pytz

	return {"timezones": pytz.all_timezones}