import frappe
from frappe.utils.response import build_response
import frappe.utils
import jwt

@frappe.whitelist(allow_guest=True)
def get_user_data():

    if(frappe.session.user):
        user = frappe.db.get_value("User", {"name": frappe.session.user}, "name")
    else:
        # Fetch the Authorization token from the request headers
        token = frappe.get_request_header("Authorization", "").split(" ")[-1]
        userData = decode_jwt_token(token)
        user = frappe.db.get_value("User", {"name": userData.get("email")}, "name")
    
    # Retrieve user data
    user_data = frappe.get_doc("User", user)

    # TODO : Check if not exist return false

    # Get Person Data From NAFATH Request
    if not frappe.db.exists("Person Data" , {"user" : user}):
        frappe.throw("Request not found")
    
    user_person_data = frappe.get_doc("Person Data" , {"user" : user})
    
    # Convert document to a dictionary
    person_data_dict = user_person_data.as_dict()

    # Format the response
    return {
            "name": user_data.name,
            "email": user_data.email,
            "full_name": user_data.full_name,
            # Add data from NAFATH
            "person_data" : person_data_dict,
        }


def decode_jwt_token(token):
    try:
        # Decode the JWT token without verifying the signature
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        
        # Return the decoded JSON object (payload)
        return decoded_token
    
    except jwt.InvalidTokenError as e:
        frappe.throw(f"Invalid token: {str(e)}")
