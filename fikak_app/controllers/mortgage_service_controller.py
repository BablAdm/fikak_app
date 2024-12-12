

import frappe
from fikak_app.external_requests.mortgage_service_requests import release_mortgage_request_api,create_new_mortgage_request_api
from frappe import _


def create_mortgage_registration_request( split_bank_request_id):
    """
    Create a new Mortgage Registration Request with details from related doctypes.
    """
    try:
        # Fetch the Split Bank Request document
        split_bank_request = frappe.get_doc("Split Bank Request", split_bank_request_id)

        # Fetch the accepted response item from the child table
        accepted_response = next(
            (item for item in split_bank_request.responses if item.status == "Accepted"),
            None
        )
        if not accepted_response:
            frappe.throw(_("No accepted response found in Split Bank Request Response Item."))

        # Create the new Mortgage Registration Request
        mortgage_request = frappe.new_doc("Mortgage Registration Request")
        mortgage_request.split_service_request = split_bank_request.split_service_request
        mortgage_request.split_bank_request = split_bank_request_id
        mortgage_request.requester = frappe.session.user
        mortgage_request.deed_id = split_bank_request.deed_id
        mortgage_request.submission_date = frappe.utils.now()
        mortgage_request.status = "Pending"

        # Populate fields from Split Bank Request
        mortgage_request.mortgage_id = split_bank_request.mortgage_id
        mortgage_request.bank_holder = split_bank_request.bank_holder

        # Populate fields from the accepted response
        mortgage_request.due_amount = accepted_response.negociated_due_amount
        mortgage_request.end_date = accepted_response.new_mortgage_end_date
        mortgage_request.start_payment_date = accepted_response.mortgage_start_payment_date
        mortgage_request.installement = accepted_response.mortgage_installement
        mortgage_request.type = accepted_response.type
        mortgage_request.number_months = accepted_response.mortgage_number_months
        mortgage_request.duration = accepted_response.mortgage_duration
        mortgage_request.smr_id = accepted_response.smr_id
        mortgage_request.smr_bank_id = accepted_response.smr_bank_id
        mortgage_request.offer_date = accepted_response.offer_date

        # Insert the new document
        mortgage_request.insert()
        frappe.db.commit()

        # Call to Release Mortgage  && create new Mortgage API
        # TODO : See the deed_info  + organisation_info  data
        deed_info = {"deed_id": deed_id}
        organization_info = {"org_name": "Waseera"}
        release_mortgage_request_api(deed_info, organization_info)
        
        # TODO : See the mortgage info data 
        mortgage_info = {"mortgage_id": split_bank_request.mortgage_id}
        create_new_mortgage_request_api(deed_info, organization_info, mortgage_info)
        
        return {"status": "success", "message": "Mortgage Registration Request created successfully.", "docname": mortgage_request.name}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Mortgage Registration Request Error"))
        return {"status": "error", "message": str(e)}

