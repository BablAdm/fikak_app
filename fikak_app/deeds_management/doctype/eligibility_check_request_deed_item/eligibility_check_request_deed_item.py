# Copyright (c) 2024, Waseera and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

from fikak_app.controllers.deed_controller import update_deed_workflow
class EligibilityCheckRequestDeedItem(Document):
	pass


	def on_update(self):

		# If the item is new or the status has changed, update the Deed Doctype
		if self.get_doc_before_save() is None or self.get_doc_before_save().status != self.status:
			service = "Eligibility Check"
			status = self.status
			if(self.status == "NEW"):
				status = "Pending"
			update_deed_workflow(self.deed,service, status)