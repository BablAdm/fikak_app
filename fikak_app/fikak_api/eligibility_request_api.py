

import frappe
import requests
from frappe import _
import math
from fikak_app.fikak_api.deeds_api import get_deeds_list
from fikak_app.fikak_api.tarabut_api import check_user_enabled_banks

# Create Eligbility check request
def create_elgibility_request(deeds , deed_source = "WATHEQ Deed"):
    try:
        # TODO : Before creating a request for concerned deed we should check if exist 
        # Create the parent Eligibility Check Request document
        print("ghhhhhhhhhhhhhhhhhhhhhhhhhh")
        step = 3 if check_user_enabled_banks(frappe.session.user) else 2
        print("ffffffffffffffffffffffffffffffff")
        eligibility_request = frappe.new_doc("Eligibility Check Request")
        eligibility_request.user = frappe.session.user
        eligibility_request.submission_date = frappe.utils.now()
        eligibility_request.wizard_step = step
        for deed in deeds:
            eligibility_request.append('requested_deeds' , {
                "deed_source" : deed_source,
                "deed" : deed,
                "status" : "NEW",
                "is_active" : 1
            })
        eligibility_request.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return eligibility_request
    except Exception as e:
        print("errrro " , str(e))
        frappe.log_error(str(e), "Error Creating Eligibility Check Request")
        return None


# Get ligibility check status 
@frappe.whitelist(methods="GET")
def check_elgibility_status(request_id , offset = 0 , page_size = 10 , order_direction = -1 , order_by = "creation" , **kwargs):

    try:
        if isinstance(offset, str):
            offset = int(offset)
    
        if isinstance(page_size, str):
            page_size = int(page_size)
        
        process_request(request_id ,  offset , page_size)
        
        data = get_deeds_list(filter_by_request = request_id ,  offset = offset , page_size = page_size , order_direction = order_direction , order_by = order_by , **kwargs)          
        frappe.local.response["http_status_code"] = 200
        return data
        
    except Exception as e:
        frappe.local.response["http_status_code"] = 500
        return{
            "status:" : False,
            "message" : str(e),
        }

    

def process_request(request_id , offset , page_size):
    try:
        
        request = frappe.get_doc("Eligibility Check Request" , request_id)
        if request.user != frappe.session.user:
            frappe.local.response["http_status_code"] = 403
            return {
                "message": _("You are not allowed to access this request"),
                "status": False
            }
        requested_deeds = frappe.get_all("Eligibility Check Request Deed Item" , 
                                         filters = {"parent" : request_id} , 
                                         fields = ["name as deed_request_id" , "deed_source" , "deed" , "total_interest_payment"
                                                    , "current_market_deed_price" , "total_principal_payment"
                                                    , "new_loan" , "loan_eligibility" , "split_eligibility" , "status" , "customer_equity"
                                                    ] 
                                         ,  start = offset , limit = page_size , order_by = "idx asc" )

        for requested_deed in requested_deeds:
            
            if requested_deed.status == "NEW":
                deed_object = frappe.get_doc(requested_deed.deed_source, requested_deed.deed)
                fikak_settings = frappe.get_single("Fikak Settings")
                eligibity_check = fikak_settings.eligibity_check
                max_new_loan = fikak_settings.max_new_loan
                waseera_fees = fikak_settings.waseera_fees
                #Compute customer total paid amount
                
                loan_eligibility = split_eligibility = loan_bba = None

                if requested_deed.get("current_market_deed_price") > 0 and deed_object.get("deed_price") > 0 :
                    loan_eligibility = split_eligibility = False
                    #Compute total amount due to bank
                    total_due_to_bank = deed_object.get("deed_price") + deed_object.get("interest_amount") - deed_object.get("down_price")\
                                            - (requested_deed.get("total_interest_payment") + requested_deed.get("total_principal_payment"))
                    #Compute bank equity from new market price
                    bank_equity_from_new_price = total_due_to_bank / requested_deed.get("current_market_deed_price") if requested_deed.get("current_market_deed_price") > 0 else 0
                    
                    #Compute customer equity from new market price
                    customer_equity_new_price = 1 - bank_equity_from_new_price
                    
                    
                    split_eligibility = True if customer_equity_new_price > eligibity_check / 100 else False
                    if total_due_to_bank == 0 :
                        loan_eligibility = True
                        split_eligibility = False
                    if split_eligibility or loan_eligibility:
                        loan_bba = (requested_deed.get("current_market_deed_price") * customer_equity_new_price )* \
                        (max_new_loan /100) * (1 - (waseera_fees / 100))
                    request_deed_item_doc = frappe.get_doc("Eligibility Check Request Deed Item" , requested_deed.deed_request_id)
                    status = "Not Eligible"
                    if loan_eligibility: status = "Eligible For Loan"
                    if split_eligibility: status = "Eligible For Split"
                    
                    request_deed_item_doc.status = status
                    if loan_eligibility: request_deed_item_doc.loan_eligibility = loan_eligibility
                    if split_eligibility: request_deed_item_doc.split_eligibility = split_eligibility
                    if loan_bba: request_deed_item_doc.new_loan = loan_bba
                    if customer_equity_new_price: request_deed_item_doc.customer_equity = customer_equity_new_price
                    if bank_equity_from_new_price: request_deed_item_doc.bank_equity = bank_equity_from_new_price
                    
                    request_deed_item_doc.save(ignore_permissions=True)
            
        frappe.db.commit()

    except Exception as e:
        frappe.local.response["http_status_code"] = 500
        return{
            "status:" : False,
            "message" : str(e),
        }

# Fetch all  Eligibility Request created by the current user with status
@frappe.whitelist(methods=['GET'])
def get_eligiblity_request_list(offset = 0 , page_size = 10 , order_direction = -1 , order_by = "creation"):

    if isinstance(offset, str):
        offset = int(offset)

    if isinstance(page_size, str):
        page_size = int(page_size)

    # Get the current logged-in user
    #filters = {"user" : frappe.session.user}

    eligibility_request_dt = frappe.qb.DocType("Eligibility Check Request")
 
    # Get the deeds that are not deleted
    query = (
        frappe.qb.from_(eligibility_request_dt)
     
        .select(
            eligibility_request_dt.name,
            eligibility_request_dt.user,
            eligibility_request_dt.submission_date,
            eligibility_request_dt.wizard_step
        )
        .where(eligibility_request_dt.user == frappe.session.user)  
    )

    data_len = len(query.run(as_dict=True))
    
    data = query.offset(offset).limit(page_size).run(as_dict=True)
    
    # Fetch child table data for each request
    for req in data:
        req["requested_deeds"] = frappe.get_all(
            "Eligibility Check Request Deed Item", 
            fields=["name as deed_request_id" , "deed_source" , "deed" , "total_interest_payment"
                                                    , "current_market_deed_price" , "total_principal_payment"
                                                    , "new_loan" , "loan_eligibility" , "split_eligibility" , "status" , "customer_equity"],  # Add your child table fields
            filters={"parent": req["name"]},
        )

    return {
        "data" : data,
        "meta": {
            "current_page": int((offset/page_size)+1),
            "total_items": data_len,
            "items_per_page": page_size,
            "total_pages": math.ceil(data_len / page_size)
        },
    }   
    # requests = frappe.get_all(
    #         "Eligibility Check Request",  
    #         filters=filters,
    #         fields=["name","user", "submission_date", "wizard_step"],  # Specify fields you need
    #         start = offset , limit = page_size , order_by = "modified asc",
    #     )


    return requests


@frappe.whitelist(methods=['POST'])
def update_eligibility_request(request_id,updates):
    try:
        if frappe.db.exists("Eligibility Check Request" , {'name' : request_id , "user" : frappe.session.user}):
            request_dt = frappe.get_doc("Eligibility Check Request" , request_id)
            # Check if the current user is the owner
            if request_dt.user != frappe.session.user:
                frappe.local.response.http_status_code = 403
                return {
                    "status": False,
                    "message": _("You are not the owner of this Eligbility Request")
                }

            # Update each field in the dictionary
            for field, value in updates.items():
                if hasattr(request_dt, field):  # Check if the field exists on the DocType
                    setattr(request_dt, field, value)
                else:
                    print(f"Warning: '{field}' does not exist on '{request_dt.doctype}' and will be ignored")


            # Save the changes
            request_dt.save()
            frappe.db.commit()  # Commit to ensure changes are saved to the database
            return {
                "status": True,
                "message": _("Eligiblity Request updated successfully")
            }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(),"Eligiblity Request Update exception : " + str(e))
        return {
            "status" : False,
            "message": str(e)
        }

def update_workflow_step(step , request_id = None):
    """
    Update the Eligibility Request workflow status.

    This function updates the Eligibility Request workflow status in the database.

    Args:
        status (str): The status of the deed.
    """
    filters = {"user" : frappe.session.user}
    if request_id:
        filters["name"] = request_id
    try:
        doc = frappe.get_doc("Eligibility Check Request",filters)
        doc.wizard_step = step
        doc.save(ignore_permissions=True)
    except Exception as e:
        return None


@frappe.whitelist(methods=["GET"])
def delete_eligibility_request(request_id):
    
    try:
        request_dt = frappe.get_doc("Eligibility Check Request", {"name" : request_id , "user" : frappe.session.user})
        request_dt.delete(ignore_permissions=True)
        frappe.db.commit()
        return {
            "status": True,
            "message": "Eligibility Request deleted successfully"
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "status": False,
            "message": str(e)
        }