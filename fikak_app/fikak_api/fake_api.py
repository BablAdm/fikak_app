
import frappe
from frappe import _
import json

def get_deed_data():
    try:
        # Construct the file path
        file_path = frappe.get_app_path('fikak_app', 'data', 'wathiq_deed.json')
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data
    except Exception as e:
        frappe.throw(_("Unable to retrieve deed data."))



@frappe.whitelist()
def delete_deed_eligibility_data(deed_id):
    deeds = frappe.get_all("Eligibility Check Request" , filters = {"deed": deed_id  } , fields = ["parent" , "name"])
    for deed in deeds:
        # frappe.delete_doc("Eligibility Check Request", deed.get("name"))
        deed_doc = frappe.get_doc("Eligibility Check Request Deed Item" , deed.get("name"))
        deed_doc.save(ignore_permissions = True)
    


@frappe.whitelist()
def delete_loan_data(deed_id):
    try:
        

        #split

        evaluations = frappe.get_all("Evaluation Request" , filters = {"deed": deed_id } , fields = ["name"])
        
        for evaluation in evaluations:
            evaluation_evaluator_requests = frappe.get_all("Evaluator Evaluation Request" , filters = {"request_id": evaluation.get("name") } , fields = ["name"])
            for evaluation_evaluator_request in evaluation_evaluator_requests:
                frappe.delete_doc("Evaluator Evaluation Request", evaluation_evaluator_request.get("name"))
            evaluation_hook_responses = frappe.get_all("Evaluator Evaluation Hook Response" , filters = {"request_id": evaluation.get("name") } , fields = ["name"])
            for evaluation_hook_response in evaluation_hook_responses:
                frappe.delete_doc("Evaluator Evaluation Hook Response", evaluation_hook_response.get("name"))

        for evaluation in evaluations:
            frappe.delete_doc("Evaluation Request", evaluation.get("name"))
            

        mortgage_registers = frappe.get_all("Mortgage Registration Request" , filters = {"deed_id": deed_id } , fields = ["name"])
        for mortgage_register in mortgage_registers:
            frappe.delete_doc("Mortgage Registration Request", mortgage_register.get("name"))
        
        bank_splits = frappe.get_all("Split Bank Request" , filters = {"deed_id": deed_id } , fields = ["name"])
        for bank_split in bank_splits:
            frappe.delete_doc("Split Bank Request", bank_split.get("name"))
        
        

        bank_loans = frappe.get_all("Bank Loan Request" , filters = {"deed_id": deed_id } , fields = ["name"])
        for bank_loan in bank_loans:
            frappe.delete_doc("Bank Loan Request", bank_loan.get("name"))



        loans = frappe.get_all("Loan Service Request" , filters = {"deed": deed_id } , fields = ["name"])
        for loan in loans:
            hyper_pays = frappe.get_all("Hyperpay Request" , filters = {"source": "Loan Service Request" , "reference" : loan.get("name")  } , fields = ["name"])
            for hyper_pay in hyper_pays:
                frappe.delete_doc("Hyperpay Request", hyper_pay.get("name"))
            
            frappe.delete_doc("Loan Service Request", loan.get("name"))

        terms_and_donditions = frappe.get_all("Terms And Conditions Submission" , filters = {"deed_id": deed_id } , fields = ["name"])
        for term_and_dondition in terms_and_donditions:
            frappe.delete_doc("Terms And Conditions Submission", term_and_dondition.get("name"))

            

        splits = frappe.get_all("Split Service Request" , filters = {"deed": deed_id } , fields = ["name"])
        for split in splits:
            hyper_pays = frappe.get_all("Hyperpay Request" , filters = {"source": "Split Service Request" , "reference" : split.get("name")  } , fields = ["name"])
            for hyper_pay in hyper_pays:
                frappe.delete_doc("Hyperpay Request", hyper_pay.get("name"))
            frappe.delete_doc("Split Service Request", split.get("name"))

        
        
        
        return "Deleted Successfully"
    except Exception as e:
        return "Error in deletion" + str(e)
    
