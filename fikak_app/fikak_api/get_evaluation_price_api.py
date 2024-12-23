import frappe
from frappe.utils.safe_exec import safe_exec
from datetime import date

@frappe.whitelist()
def get_evaluation_price():
    """
    Evaluates a formula stored in the 'formula_code' field of "Fikak Settings" Doctype
    using fields from the related Doctype's document.

    :return: Evaluated result of the formula
    """
    # Fetch the document with the formula
    formula_doc = frappe.get_doc("Fikak Settings", "Fikak Settings")
    formula_code = formula_doc.formula_code.strip()

    if not formula_code:
        frappe.throw("Formula code is not defined.")
    # Define a safe context for execution
    context = {}

   

    # Remove comments and sanitize the formula
    sanitized_formula = "\n".join(
        line for line in formula_code.split("\n") if not line.strip().startswith("#")
    )

    # Prepare execution context
    context = {}

     # Fetch related Doctype data (example: UserDoctype or ProposDoctype)
    user_doctype_name = "Person Data"   
    related_doc = frappe.get_doc(user_doctype_name,  frappe.session.user)

    # Add fields to context
    # Calculate age
    today = date.today()
    age = today.year - related_doc.birth_date.year - (
        (today.month, today.day) < (related_doc.birth_date.month, related_doc.birth_date.day)
    )
    context = {
        "age": age,
        "city": related_doc.city,
        "income_range": related_doc.income_range,
    }

    try:
        # Execute the sanitized formula
        exec(sanitized_formula, {}, context)
        return context.get("result", "No result found.")
    except Exception as e:
        frappe.throw(f"Error evaluating formula: {str(e)}")


