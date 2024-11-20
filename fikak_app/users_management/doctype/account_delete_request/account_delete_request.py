# Copyright (c) 2024, Waseera and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AccountDeleteRequest(Document):
	
	def validate(self):
		"""
		Validate the Account Delete Request document.
		"""
		# Check if the user has an active session
		if self.status =="Approved":
			user_doc = frappe.get_doc("User", self.user)
			user_doc.enabled = 0
			user_doc.save()
			frappe.db.commit()
