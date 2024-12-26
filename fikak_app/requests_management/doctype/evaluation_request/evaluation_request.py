# Copyright (c) 2024, Waseera and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from fikak_app.controllers.split_service_controller import update_split_service_request_status , approve_auto_stpes
from fikak_app.external_requests.evaluation_requests import create_evaluation_request
from fikak_app.controllers.lba_controller import approve_lba_auto_stpes
import frappe

class EvaluationRequest(Document):
    def on_update(self):
        # Check for status change to "Done" and update the related request status
        if (
            self._doc_before_save
            and self._doc_before_save.status != "Done"
            and self.status == "Done"
        ):
            update_split_service_request_status(self.request, "Evaluated", self.evaluation_price , self.evaluation_source)
            if self.evaluation_source == "Split Service Request":
                approve_auto_stpes(self.request , self.deed)
            if self.evaluation_source == "Loan Service Request":
                approve_lba_auto_stpes(self.request, self.deed)

        # Handle status change to "Paid"
        if self.status == "Paid" and (
            self._doc_before_save and self._doc_before_save.status != "Paid"
        ):
            update_split_service_request_status(self.request, "Paid", self.evaluation_price , self.evaluation_source)
            self.process_evaluation_request()
    
    def after_insert(self):
        # Handle status change to "Paid"
        if self.status == "Pay Later":
            self.process_evaluation_request()
            if self.evaluation_source == "Loan Service Request":
                update_split_service_request_status(self.request, "Pay Later", self.evaluation_price , self.evaluation_source)
        else:
            update_split_service_request_status(self.request, "Waiting For Payment", self.evaluation_price , self.evaluation_source)

    def process_evaluation_request(self):
        """Processes the evaluation request by preparing the request parameters
        and triggering the evaluation API."""
        try:
            # Ensure the deed is linked
            if not self.deed:
                frappe.throw("Deed is not linked to the Evaluation Request.")

            # Trigger the API
            response = create_evaluation_request(self.deed , self.requester , self.name)
            
            # Log success message
            frappe.msgprint(f"Evaluation API Triggered: {response.get('message', 'Success')}")
        
        except frappe.ValidationError as e:
            # Handle validation-specific errors
            frappe.throw(str(e))
        except Exception as e:
            # Log and rethrow other errors
            frappe.log_error(message=str(e), title="EvaluationRequest API Error")
            frappe.throw(f"Error processing evaluation: {e}")

    
