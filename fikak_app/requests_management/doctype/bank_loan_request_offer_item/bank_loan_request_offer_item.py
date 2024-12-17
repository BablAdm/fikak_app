# Copyright (c) 2024, Waseera and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BankLoanRequestOfferItem(Document):
	

	def on_update(self):
		# Update the status of the Split Bank Request
		if self._doc_before_save:
			if self.status != self._doc_before_save.status:
				bank_split_request = frappe.get_doc("Bank Loan Request", self.parent)
				bank_split_request.status = self.status
				
				if self.status == "Negociation":
					bank_split_request.append("bank_offers", {
						"status": "Pending"
					})
				
				bank_split_request.save(ignore_permissions=True)

