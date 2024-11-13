import frappe
import frappe.utils
import jwt
from frappe import _


@frappe.whitelist(methods="GET")
def get_user_data():
    try:
        # Retrieve user data
        user_data = frappe.get_doc("User", frappe.session.user)

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