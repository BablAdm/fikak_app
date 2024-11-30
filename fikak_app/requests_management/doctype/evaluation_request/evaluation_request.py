# Copyright (c) 2024, Waseera and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from fikak_app.fikak_api.integrations_evaluator_api import create_evaluate_request
import frappe
from convertdate import islamic
from datetime import datetime
import re


class EvaluationRequest(Document):
	pass


	def on_update(self):
		if self._doc_before_save and self._doc_before_save.status != "Done" and self.status == "Done":
			update_split_service_request_status(self.request, "Evaluated" , self.evaluation_price)

		if self.status == "Paid" and ( self._doc_before_save and self._doc_before_save.status != "Paid" ) : 
			try:
				

				# Fetch related Deed details
				if not self.deed:
					frappe.throw("Deed is not linked to the Evaluation Request.")

				deed_dt = frappe.get_doc("WATHEQ Deed", self.deed)
				# Retrieve user data
				user_data = frappe.get_doc("User", self.requester)
				user_person_data = frappe.get_doc("Person Data" , {"user" : user_data.name})
				deed_date_gregorian = convert_hijri_to_gregorian(deed_dt.deed_date)
				# Prepare the request parameters from the document
				request_params = {
					"request_id": self.name,
					"deed_date": deed_date_gregorian , #"2024-10-01T00:00:00Z" , #self.deed,
					"deed_no": deed_dt.deed_number ,#self.deed_no,
					"request_type_id": "1", # TODO : should get a request_type_id deed_dt.real_estate_details[0].real_estate_type_name
					"sector_no": deed_dt.real_estate_details[0].plan_number, # TODO : we should check if is the same with sector_no
					"land_no": deed_dt.real_estate_details[0].land_number,#self.land_no,
					"land_area": deed_dt.deed_area,#"0.0",#self.land_area,
					"city_id": "000001", # TODO : should get a real city_id
					"area_id": "000001", # TODO : should get a real area_id
					"client_name": user_data.full_name,#self.client_name,
					"phone": user_person_data.phone_number,#self.phone,
				}
				
				# Fetch the deed document file
				# deed_document = frappe.get_doc("File", {"attached_to_name": doc.name, "attached_to_doctype": "EvaluationRequest"}).file_url
				deed_document = None
				# Trigger the API
				response = create_evaluate_request(request_params)
				
				# Log the response or handle further processing
				frappe.msgprint(f"Evaluation API Triggered: {response['message']}")
			except Exception as e:
				frappe.log_error(message=str(e), title="EvaluationRequest API Error")
				frappe.throw(f"Error processing evaluation: {e}")




def convert_hijri_to_gregorian(hijri_date_str):
    """
    Convert a Hijri date string to Gregorian and format it as an ISO 8601 date string.

    :param hijri_date_str: Hijri date as a string in the format 'YYYY-M-Dxxx'
                           (e.g., '1446-4-702')
    :return: Gregorian date formatted as 'YYYY-MM-DDT00:00:00Z'
    """
    # Extract the Hijri year, month, and day using regex
    match = re.match(r"(\d+)-(\d+)-(\d+)", hijri_date_str)
    if not match:
        raise ValueError("Invalid Hijri date format. Expected format: 'YYYY-M-Dxxx'.")

    hijri_year, hijri_month, hijri_day = map(int, match.groups())

    # Convert Hijri to Gregorian
    gregorian_year, gregorian_month, gregorian_day = islamic.to_gregorian(hijri_year, hijri_month, hijri_day)

    # Format as ISO 8601
    gregorian_date = datetime(gregorian_year, gregorian_month, gregorian_day)
    return gregorian_date.strftime("%Y-%m-%dT00:00:00Z")

# Example usage
#hijri_date_str = "1446-4-702"
#result = convert_hijri_to_gregorian(hijri_date_str)
#print(f"Gregorian Date: {result}")

def update_split_service_request_status(request_id , status , evaluation_price):
	split_service_request = frappe.get_doc("Split Service Request", request_id)
	split_service_request.status = status
	split_service_request.current_market_deed_price = evaluation_price
	split_service_request.save(ignore_permissions=True)
	frappe.db.commit()
	return split_service_request