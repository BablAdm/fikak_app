# Copyright (c) 2024, Waseera and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SplitServiceRequest(Document):

	def on_update(self):
		if self._doc_before_save and self._doc_before_save.status != "Evaluated" and self.status == "Evaluated":
			requested_deed = {
				"total_interest_payment" : self.total_interest_payment,
				"total_principal_payment" : self.total_principal_payment
			}
			max_new_loan , split_eligibility , customer_equity_new_price , bank_equity_from_new_price = get_prices(self.deed , requested_deed , self.current_market_deed_price)
			self.split_eligibility = split_eligibility
			self.customer_equity = customer_equity_new_price
			self.new_loan = max_new_loan
			self.bank_equity = bank_equity_from_new_price
			print(max_new_loan , split_eligibility , customer_equity_new_price , bank_equity_from_new_price)
			self.save()


	def after_insert(self):
		deed_pricing = get_eligibility_check_details(self.eligibility_check_request , self.deed)
		self.total_interest_payment = deed_pricing.get("total_interest_payment")
		self.total_principal_payment = deed_pricing.get("total_principal_payment")
		self.save()



def get_eligibility_check_details(eligibility_check_request , deed_id):
	eligibility_check_request_doc = frappe.get_doc("Eligibility Check Request Deed Item",{"parent" : eligibility_check_request , "deed" : deed_id})
	return eligibility_check_request_doc.as_dict()


def get_prices(deed , requested_deed , current_market_price):
	fikak_settings = frappe.get_single("Fikak Settings")
	eligibity_check = fikak_settings.eligibity_check
	max_new_loan = fikak_settings.max_new_loan
	waseera_fees = fikak_settings.waseera_fees

	deed_object = frappe.get_doc("WATHEQ Deed", deed)
	total_due_to_bank = deed_object.get("deed_price") + deed_object.get("interest_amount") - deed_object.get("down_price")\
                                        - (requested_deed.get("total_interest_payment") + requested_deed.get("total_principal_payment"))
	#Compute bank equity from new market price
	bank_equity_from_new_price = total_due_to_bank / current_market_price if current_market_price > 0 else 0
	
	#Compute customer equity from new market price
	customer_equity_new_price = 1 - bank_equity_from_new_price
	
	
	
	split_eligibility = True if customer_equity_new_price > eligibity_check / 100 else False
	loan_bba = 0
	if split_eligibility:
		loan_bba = (current_market_price * customer_equity_new_price )* \
		(max_new_loan /100) * (1 - (waseera_fees / 100))
	
	
	return loan_bba , split_eligibility , customer_equity_new_price , bank_equity_from_new_price
