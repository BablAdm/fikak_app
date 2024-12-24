import frappe

from fikak_app.controllers.customer_price import get_evaluation_price_from_formula

@frappe.whitelist()
def get_evaluation_price():
    try:
        return {
            "data" :{    
                    "price" : get_evaluation_price_from_formula()
                },
            "status": True
        }
    except Exception as e:
        # Log the error
        frappe.log_error(frappe.get_traceback(), "Get Evaluation Price Error")
        frappe.local.response.http_status_code = 500
        return {
            "status": False,
            "message": str(e),
        }


