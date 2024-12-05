# Copyright (c) 2024, Waseera and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class EligibilityCheckRequest(Document):
    
	def validate(self):
		#TODO : Check if the user is the owner of the deed
		#TODO : Check if the deed is not already in the request
		pass

	def on_update(self):
		
		if not self._doc_before_save:
			#TODO : Update all new deeds
			for deed in self.requested_deeds:
				update_deed_status(deed.deed , "NEW")
			pass
		else:
			#TODO : Update only the new deeds
			#TODO : Update deeds that are not in the old request and the status has been changed
		print("fsssssssssssssssssss")
		pass


def update_deed_status(deed_id , status):
	pass