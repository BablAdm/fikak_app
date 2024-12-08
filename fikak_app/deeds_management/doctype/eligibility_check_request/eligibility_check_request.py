# Copyright (c) 2024, Waseera and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from fikak_app.controllers.deed_controller import update_deed_workflow

class EligibilityCheckRequest(Document):
    
	def validate(self):
		#TODO : Check if the user is the owner of the deed
		#TODO : Check if the deed is not already in the request
		pass

	def on_update(self):

		# Iterate over child table items and detect status changes
		for item in self.get("requested_deeds"):

			# Fetch the previous state of the document before the current save
			previous_doc = self.get_doc_before_save()

			# Iterate over child table items to compare statuses
			for item in self.get("requested_deeds"):
				# Find the corresponding item in the previous state
				previous_item = (
					next((prev for prev in previous_doc.get("requested_deeds") if prev.name == item.name), None)
					if previous_doc else None
				)
			# If the item is new or the status has changed, update the Deed Doctype
			if previous_item is None or previous_item.status != item.status:
				service = "Eligibility Check"
				status = item.get("status")
				if(status == "NEW"):
					status = "Pending"
				update_deed_workflow(item.deed,service, status)

			# # Get the old status from the cached statuses
			# old_status = self._cached_statuses.get(item.name)

			# # Check if the status has changed
			# if old_status != item.status:
			# 	service = "Eligibility Check"
			# 	status = item.get("status")
			# 	if(status == "NEW"):
			# 		status = "Pending"
			# 	update_deed_workflow(item.deed,service, status)
	





 