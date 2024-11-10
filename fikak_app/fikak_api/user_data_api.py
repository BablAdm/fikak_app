import frappe
from frappe.utils.response import build_response
import frappe.utils
import jwt

@frappe.whitelist(allow_guest=True)
def get_user_data():
    try:
        # Retrieve user data
        user_data = frappe.get_doc("User", frappe.session.user)

        # TODO : Check if not exist return false

        user_person_data = frappe.get_doc("Person Data" , {"user" : user_data.name})
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
    except frappe.DoesNotExistError as e:
        frappe.local.response.http_status_code = 404
        return {
            "status": False,
            "message": "User not found" + str(e)
        }


def decode_jwt_token(token):
    try:
        # Decode the JWT token without verifying the signature
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        
        # Return the decoded JSON object (payload)
        return decoded_token
    
    except jwt.InvalidTokenError as e:
        frappe.throw(f"Invalid token: {str(e)}")
