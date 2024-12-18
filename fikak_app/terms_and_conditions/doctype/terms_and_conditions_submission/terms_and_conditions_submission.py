# Copyright (c) 2024, Waseera and contributors
# For license information, please see license.txt

# import frappe
from fikak_app.controllers.lba_controller import insert_new_lba_request

from frappe.model.document import Document


class TermsAndConditionsSubmission(Document):
	

	def after_insert(self):
		# Update the status of the Split Bank Request
		if self.terms_type == "Asset-Backed Loan":
			insert_new_lba_request(self.deed_id)

