# Copyright (c) 2024, Waseera and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
	

class Invoice(Document):
	

	def on_update(self):
		# if self.status == "Paid": create a request to the evaliation API 
		pass



