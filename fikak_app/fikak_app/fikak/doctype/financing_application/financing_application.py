import frappe
from frappe import _
from frappe.model.document import Document

MIN_AMOUNT = 50000
MAX_AMOUNT = 5000000

class FinancingApplication(Document):
    def validate(self):
        if self.amount and not (MIN_AMOUNT <= self.amount <= MAX_AMOUNT):
            frappe.throw(_("Amount must be between {0} and {1} SAR").format(MIN_AMOUNT, MAX_AMOUNT))

    def before_save(self):
        if self.status == "Approved" and not self.approval_date:
            self.approval_date = frappe.utils.now()
        if self.status == "Disbursed":
            if not self.approval_date:
                frappe.throw(_("Application must be approved before disbursement"))
            if not self.disbursement_date:
                self.disbursement_date = frappe.utils.now()
