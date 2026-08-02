


import logging

import frappe
from frappe import _
import jwt
import datetime
from frappe.utils import now_datetime

_logger = logging.getLogger(__name__)

EXPIRATION_TIME = 360000  # Token expiration time in seconds

def get_jwt_secret():
    """
    Read the JWT signing secret from site_config.json (set via
    `bench --site <site> set-config fikak_jwt_secret <random-value>`).
    Falls back to frappe's own secret_key so a fresh install still works,
    but you should set fikak_jwt_secret explicitly before production use.
    """
    return frappe.conf.get("fikak_jwt_secret") or frappe.conf.get("encryption_key")

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
    except frappe.exceptions.AuthenticationError as auth_err:
        _logger.debug("Login failed for %s: %s", email, auth_err)
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
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=EXPIRATION_TIME)
    }

    # Encode the payload with the secret key
    token = jwt.encode(payload, get_jwt_secret(), algorithm="HS256")

    return token

def store_bearer_token_in_frappe(user, token):
    """
    Store the generated JWT token in the OAuth Bearer Token DocType in Frappe.
    """
    # Get the current timestamp for token creation
    issued_at = frappe.utils.now()

    # Calculate token expiry (based on your token's expiration time)
    expiry = frappe.utils.add_to_date(issued_at, seconds=EXPIRATION_TIME)
    if not frappe.db.exists("User", user):
        user = frappe.db.exists("User", {"username": user})
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


@frappe.whitelist(allow_guest=True)
def get_timezones():
    import pytz
    return list(pytz.all_timezones)


def _has_accepted_current_terms(user):
    """
    True if the user has an acceptance record for whichever Terms And
    Conditions is currently enabled. If no Terms And Conditions is
    configured at all, there is nothing to accept, so this returns True
    (matches the previous hardcoded-True behavior for installs that
    haven't set up a terms document yet, instead of permanently blocking
    every user with an impossible-to-satisfy requirement).
    """
    active_terms = frappe.get_all("Terms And Conditions", filters={"enabled": 1}, fields=["name"], limit=1)
    if not active_terms:
        return True
    return bool(frappe.db.exists("Terms Acceptance", {
        "user": user,
        "terms_and_conditions": active_terms[0].name,
    }))


@frappe.whitelist()
def get_user_info():
    """
    Returns basic info about the logged-in user for the dashboard header.

    `terms_submitted` is a real check against the Terms Acceptance doctype
    (see fikak_api.conditions_api) - no longer hardcoded.
    """
    user = frappe.session.user
    user_doc = frappe.get_doc("User", user)
    return {
        "data": {
            "full_name": user_doc.full_name,
            "email": user_doc.email,
            "user_image": user_doc.user_image,
            "first_name": user_doc.first_name,
            "last_name": user_doc.last_name,
            "terms_submitted": _has_accepted_current_terms(user),
        }
    }


