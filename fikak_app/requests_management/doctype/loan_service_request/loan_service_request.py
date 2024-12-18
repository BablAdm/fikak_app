# Copyright (c) 2024, Waseera and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class LoanServiceRequest(Document):
	

	def on_update(self):

		# handle result after evaluation hook response
		if self._doc_before_save and self._doc_before_save.status != "Evaluated" and self.status == "Evaluated":
			if self.source == "Free Deed":
				self.bank_equity = 0
				self.customer_equity = 1
				self.max_new_loan = get_prices(self.current_market_deed_price)
			self.status = "Eligible For Loan"
			self.save()


def get_prices(current_market_price):
	fikak_settings = frappe.get_single("Fikak Settings")
	max_new_loan = fikak_settings.max_new_loan
	waseera_fees = fikak_settings.waseera_fees
		
	loan_bba = (current_market_price  )* \
	(max_new_loan /100) * (1 - (waseera_fees / 100))
	
	
	return loan_bba
