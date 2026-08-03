import frappe
from frappe.model.document import Document

class PaymentTransaction(Document):
    def before_insert(self):
        if not self.gateway_reference:
            self.gateway_reference = "TXN-" + frappe.generate_hash(length=8).upper()
