
import frappe



def update_split_service_request_status(request_id , status = None, evaluation_price = None , evaluation_source = None):

	split_service_request = frappe.get_doc(evaluation_source, request_id)
	if status : split_service_request.status = status
	if evaluation_price : split_service_request.current_market_deed_price = evaluation_price
	split_service_request.save(ignore_permissions=True)
	frappe.db.commit()
	return split_service_request



def approve_auto_stpes(split_service_request_id , deed_id):
	from fikak_app.fikak_api.split_service_api import create_bank_split_request , update_bank_offer_status
	from fikak_app.controllers.lba_controller import insert_new_lba_request
	from fikak_app.fikak_api.lba_api import create_bank_lba_request

	fikak_settings = frappe.get_single("Fikak Settings")
	if fikak_settings.split_auto_validation:
		updated_obj = create_bank_split_request(split_service_request_id , deed_id)
		bank_offer_id = updated_obj.get("data").get("bank_request").get("responses")[0].get("name")
		bank_split_request_id = updated_obj.get("data").get("bank_request").get("name")
		update_bank_offer_status(bank_offer_id , bank_split_request_id , "Accepted")
		lba_request =   insert_new_lba_request(deed_id)
		create_bank_lba_request(lba_request.name , deed_id)

		
