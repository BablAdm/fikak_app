
import frappe


def update_split_service_request_status(request_id , status = None, evaluation_price = None):
	split_service_request = frappe.get_doc("Split Service Request", request_id)
	if status : split_service_request.status = status
	if evaluation_price : split_service_request.current_market_deed_price = evaluation_price
	split_service_request.save(ignore_permissions=True)
	frappe.db.commit()
	return split_service_request