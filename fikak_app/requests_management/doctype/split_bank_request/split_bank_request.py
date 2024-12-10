# Copyright (c) 2024, Waseera and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

from fikak_app.controllers.split_service_controller import update_split_service_request_status

class SplitBankRequest(Document):
	

	def after_insert(self):
		update_split_service_request_status(self.split_service_request , 'Offer')


	def on_update(self):
		if self._doc_before_save and self.status in ( "Accepted" , "Rejected") and self._doc_before_save.status != self.status:
			update_split_service_request_status(self.split_service_request , self.status)