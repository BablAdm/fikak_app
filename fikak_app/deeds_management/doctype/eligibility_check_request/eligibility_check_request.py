# Copyright (c) 2024, Waseera and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now
from frappe.model.document import Document


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
	


def update_deed_workflow(deed_name ,service, status):
    """
    Update the 'Deed' Doctype based on changes in 'Eligibility Check Request Deed Item'
    """	
	## 1. get deed doctype
    deed_dt = frappe.get_doc("WATHEQ Deed", deed_name)

    if not deed_dt:
        frappe.throw(f"Deed with name '{deed_name}' not found.")

    # 2.Update the Deed status and services
    deed_dt.service_status = status
    deed_dt.service = service

    # 3. Add a new entry to the Watheq Deed Status Item table
    deed_dt.append("statuses", {
        "submission_date": now(),
        "service": service,
        "status": status
    })

    # Save the changes to the Deed Doctype
    deed_dt.save(ignore_permissions=True)




 