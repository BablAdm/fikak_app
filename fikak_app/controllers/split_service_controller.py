
import frappe


def update_split_service_request_status(request_id , status , evaluation_price):
	split_service_request = frappe.get_doc("Split Service Request", request_id)
	split_service_request.status = status
	split_service_request.current_market_deed_price = evaluation_price
	split_service_request.save(ignore_permissions=True)
	frappe.db.commit()
	return split_service_request