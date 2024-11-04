# custom_app/api.py

import frappe
from frappe.utils.file_manager import save_file
from frappe import _

@frappe.whitelist(methods=['POST'])
def update_user_photo():
    """
    Update a user's profile photo using binary file data.

        Returns:
        dict: Success message with file URL.
    """
    # Check if user exists
    
    user = frappe.get_doc('User', frappe.session.user)
    if not user:
        frappe.throw("User not found")

    # Get binary file from request
    file = frappe.request.files.get('user_photo')
    
    if not file:
        frappe.throw("No file uploaded")
    
    # Save the file
    file_doc = save_file(
        fname=file.filename,
        content=file.read(),
        dt='User',
        dn=user.name,
        decode=False,
        is_private=0
    )

    # Update user's profile picture
    user.user_image = file_doc.file_url
    user.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "message": "User photo updated successfully",
        "file_url": file_doc.file_url
    }

@frappe.whitelist(methods=['GET'])
def get_user_profile_data():
    """
    Get user profile data.

        Returns:
        dict: User profile data.
    """
    user = frappe.get_doc('User', frappe.session.user)
    if not user:
        frappe.throw("User not found")

    try:
        person_data = frappe.get_doc('Person Data', {'user': user.name})
    except frappe.DoesNotExistError:
        person_data = None
    data = {
        "user_id": user.name,
        "user_image": user.user_image,
        "first_name": user.first_name,
        "time_zone" : user.time_zone,
        "last_name": user.last_name,
        "full_name": user.full_name,
        "email": user.email,
        "user_image": user.user_image,
        "father_name": person_data.father_name if person_data else None,
        "grand_father_name" : person_data.grand_father_name if person_data else None,
        "english_third_name" : person_data.english_third_name if person_data else None,
        "birth_date" : person_data.birth_date if person_data else None,
        "gender" : person_data.gender if person_data else None,
        "nationality" : person_data.nationality if person_data else None,
        "phone_number" : person_data.phone_number if person_data else None,
        "street" : person_data.street if person_data else None,
        "building_number" : person_data.building_number if person_data else None,
        "city" : person_data.city if person_data else None,
        "post_code" : person_data.post_code if person_data else None,
        "region_name" : person_data.region_name if person_data else None,
        "district" : person_data.district if person_data else None,
        "country" : person_data.country if person_data else None,
        "additional_number" : person_data.additional_number if person_data else None,
        "marital_status" : person_data.marital_status if person_data else None

    }


    return {
        "status" : True,
        "data" : data,
        "message" : "User profile data retrieved successfully"
    }

@frappe.whitelist(methods=['POST'])
def update_user_profile_data(user_data):
    """
    Update user profile data.

        Args:
        user_data (dict): User profile data.

        Returns:
        dict: Success message.
    """
    user = frappe.get_doc('User', frappe.session.user)
    if not user:
        frappe.throw("User not found")
    if user.email != user_data.get("email"): user.email = user_data.get("email")
    if user.time_zone != user_data.get("time_zone"): user.time_zone = user_data.get("time_zone")

    user.save(ignore_permissions=True)
    try:
        person_data = frappe.get_doc('Person Data', {'user': user.name})
        if person_data.country != user_data.get("country") and user_data.get("country"): person_data.country = user_data.get("country")
        if person_data.gender != user_data.get("gender") and user_data.get("gender"): person_data.gender = user_data.get("gender")
        if person_data.marital_status != user_data.get("marital_status") and user_data.get("marital_status"): person_data.marital_status = user_data.get("marital_status")
        if person_data.phone_number != user_data.get("phone_number") and user_data.get("phone_number"): person_data.phone_number = user_data.get("phone_number")
        if person_data.street != user_data.get("street") and user_data.get("street"): person_data.street = user_data.get("street")
        if person_data.building_number != user_data.get("building_number") and user_data.get("building_number"): person_data.building_number = user_data.get("building_number")
        # if person_data.city != user_data.get("city"): person_data.city = user_data.get("city")
        if person_data.post_code != user_data.get("post_code") and user_data.get("post_code"): person_data.post_code = user_data.get("post_code")
        if person_data.region_name != user_data.get("region_name") and user_data.get("region_name"): person_data.region_name = user_data.get("region_name")
        if person_data.district != user_data.get("district") and user_data.get("district"): person_data.district = user_data.get("district")
        if person_data.nationality != user_data.get("nationality") and user_data.get("nationality"): person_data.nationality = user_data.get("nationality")
        if person_data.additional_number != user_data.get("additional_number") and user_data.get("additional_number"): person_data.additional_number = user_data.get("additional_number")

        person_data.save(ignore_permissions=True)

    except frappe.DoesNotExistError:
        pass
    
    return {
        "status": True,
        "message": "User profile data updated successfully"
   }

@frappe.whitelist(allow_guest=False)
def update_user_password(old_password, new_password , email = None):
    """
    Updates the current user's password.

    Args:
        old_password (str): The user's current password.
        new_password (str): The new password to set.

    Returns:
        dict: Success or failure message.
    """
    if email:
        user = frappe.db.exists("User", {"email": email})
        if not user:
            frappe.local.response["http_status_code"] = 404
            return {
                "message": _("User not found"),
                "status": False
            }
            
    if not email:
        user = frappe.session.user  # Get the current logged-in user
    
    # Verify the old password
    try:
        frappe.auth.check_password(user, old_password)
    except Exception as e:    
        frappe.local.response["http_status_code"] = 401
        return {
            "message": _("Incorrect old password"),
            "status": False
        }
    # Update to the new password
    try:
        frappe.utils.password.update_password(user, new_password)
        frappe.db.commit()
        return {
            "status": True,
            "message": _("Password updated successfully")
        }
    except frappe.exceptions.ValidationError as e:
        frappe.local.response["http_status_code"] = 400
        return {
            "status": False,
            "message": _("Failed to update password: {0}").format(e)
        }
    except Exception as e:
        frappe.local.response["http_status_code"] = 500
        return {
            "status": False,
            "message": _("An error occurred: {0}").format(e)
        }


@frappe.whitelist()
def deactivate_user_account(methods=['POST']):
    """
    Deactivates a user account by disabling the user.

    Returns:
        dict: Success message indicating the user was deactivated.
    """
    try:
        delete_account_request = frappe.new_doc("Account Delete Request")
        delete_account_request.user = frappe.session.user
        delete_account_request.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {"status":True,  "message": _("User account deactivated request created successfully")}
    
    except Exception as e:
        frappe.throw(str(e))
        frappe.local.response["http_status_code"] = 500
        return {"message":_("An error occurred while deactivating the account: {0}").format(str(e)) , "status" : False}
