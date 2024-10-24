


import frappe
from frappe import _
import jwt
import datetime

EXPIRATION_TIME = 360000  # Token expiration time in seconds
SECRET_KEY = "FIKAK_LOGIN_SECRET_KEY"

@frappe.whitelist(allow_guest=True)
def custom_login(email, password):
    try:
        # Attempt to authenticate the user using Frappe's login manager
        login_manager = frappe.auth.LoginManager()
        login_manager.authenticate(user=email, pwd=password)

        login_manager.post_login()
        bearer_token = generate_jwt_token(email)[:130]
        store_bearer_token_in_frappe(email, bearer_token)
        # If login is successful, return a success response
        return {
            "status": "success",
            "message": _("Logged In Successfully"),
            "user": frappe.session.user,
            "token" : bearer_token,
            # "csrf_token" : frappe.sessions.get_csrf_token(),
            # "session_id": frappe.session.sid  # Return the session ID
        }
    except frappe.exceptions.AuthenticationError:
        # If authentication fails, return an error
        frappe.clear_messages()
        return {
            "status": "error",
            "message": _("Invalid email or password")
        }
    
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
