
import frappe
from frappe import _
import requests
import json

from . import global_utils
from . import fake_api

from fikak_app.fikak_api.eligibility_request_api import create_elgibility_request

def create_new_watheq_request_deed(deed_id , national_id ,  endpoint , app_id , app_key):
    try:

        dev_mod_props = dev_mod_props = frappe.get_single('DEV MOD PROPS')

        if dev_mod_props.user_id_watheq:
            national_id = dev_mod_props.get("user_id_watheq")

        # Define headers if required (e.g., authentication headers)
        headers = {
            "Content-Type": "application/json",
           # "APP-ID": app_id,  # Replace with the actual token
            "apiKey" : app_key
        }

        endpointURL = endpoint + '/deed/' + deed_id + '/'+national_id+'/National_ID'
        response = requests.get(endpointURL,  headers=headers)
        # TODO remove this fake api 
        
        if response.status_code in (200 , 201):
            return 200 , {
                "status" : True,
                "data" : response.json(),
            }
        else:
            frappe.log_error(frappe.get_traceback(), " Watheq request error : " + response.text)
            return 500 , {
                "status" : False,
                "message": response.text
            }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(),"WATHEQ exception : " + str(e))
        return 500 , {
            "status" : False,
            "message": str(e)
        }
    
def create_new_watheq_request(national_id ,deed_id , request_id):
    request = frappe.new_doc("WATHEQ Request")
    request.national_id = national_id
    request.deed_id = deed_id
    request.request_id = request_id
    request.insert(ignore_permissions=True)
    frappe.db.commit()
    return request

@frappe.whitelist(methods=["GET"])
def get_deed_data(deed_id):
    try:
        user_data = frappe.get_doc("User" , frappe.session.user)
        national_id = user_data.get("username")

        if frappe.db.exists("WATHEQ Deed" , {'deed_number' : deed_id , "deed_owner" : frappe.session.user}):
            deed_data = frappe.get_doc("WATHEQ Deed" , {"deed_number" : deed_id , "deed_owner" : frappe.session.user}).as_dict()
            eligibility_check_details =  get_deed_request_details(deed_data.name)
            if eligibility_check_details:
                deed_data.update(eligibility_check_details)
            ## TODO : We should check if the user has the right to see this deed
            
        else:
            watheq_settings = frappe.get_single('WATHEQ Settings')
            # Check if we are using api or fake date
            if watheq_settings.is_enabled:
                # Create watheq request
                response = create_new_watheq_request_deed(deed_id, national_id , watheq_settings.api_url , watheq_settings.get_password('app_id') ,watheq_settings.get_password('app_key'))
                responseData = response[1].get("data")
            else :
                # save global result for traking 
                responseData = fake_api.get_deed_data()

            #  Create watheq Request/Response obj
            insert_watheq_request_callback(national_id,deed_id, responseData)
            deed_data = insert_deed(responseData)
        
        

        return deed_data
        
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "status" : False,
            "message": str(e)
        }


def get_deed_request_details(deed_id):
    eligibility_dt = frappe.qb.DocType("Eligibility Check Request")
    eligibility_deed_item_dt = frappe.qb.DocType("Eligibility Check Request Deed Item")

    query = (
        frappe.qb.from_(eligibility_dt)
        .inner_join(eligibility_deed_item_dt)
        .on(eligibility_dt.name == eligibility_deed_item_dt.parent)
        .select(
            eligibility_dt.name.as_("request_id"),
            eligibility_dt.wizard_step.as_("wizard_step"),
            eligibility_deed_item_dt.status.as_("workflow_state")
        ).where((eligibility_deed_item_dt.deed == deed_id) & (eligibility_deed_item_dt.is_active == 1) & (eligibility_dt.user == frappe.session.user))
    )
    res = query.run(as_dict=True)
    if res:
        return res[0]
    return None

def get_deed_request_details_by_status():
    eligibility_dt = frappe.qb.DocType("Eligibility Check Request")
    eligibility_deed_item_dt = frappe.qb.DocType("Eligibility Check Request Deed Item")

    query = (
        frappe.qb.from_(eligibility_dt)
        .inner_join(eligibility_deed_item_dt)
        .on(eligibility_dt.name == eligibility_deed_item_dt.parent)
        .select(
            eligibility_dt.name.as_("request_id"),
            eligibility_deed_item_dt.deed.as_("deed_number"),
            eligibility_dt.wizard_step.as_("wizard_step"),
            eligibility_deed_item_dt.status.as_("workflow_state")
        ).where((eligibility_deed_item_dt.is_active == 1) & (eligibility_dt.user == frappe.session.user))
    )
    res = query.run(as_dict=True)
    if res:
        return res[0]
    return None


 

def insert_watheq_request_callback(national_id,deed_id,response_data):
    request_id = global_utils.generate_request_id()
    # Convert the JSON dictionary to a JSON string
    json_string = json.dumps(response_data)
    doc = frappe.get_doc({
        "doctype": "WATHEQ Response",
        "request_id": request_id ,
        "deed_id": deed_id ,
        "national_id": national_id ,
        "response": json_string  # Assuming "text_field" is where you want to store it
    })

    # Insert or update the document
    try:
        doc.insert(ignore_permissions=True)
        frappe.db.commit()  # Save changes to the database
    except Exception as e:
        frappe.db.rollback()  # Rollback if there's an error
        frappe.log_error(str(e), "Error Saving JSON Data")
        print("Error saving document:", e)

def insert_deed(data):
    # Create the parent Deed document
    try:
        if frappe.db.exists("WATHEQ Deed" , {"deed_number" : data["deedDetails"]["deedNumber"] , "deed_owner" : frappe.session.user}):
            deed_data = frappe.get_doc("WATHEQ Deed" , {"deed_number" : data["deedDetails"]["deedNumber"]})
            eligibility_check_details =  get_deed_request_details(deed_data.name)
            if eligibility_check_details:
                deed_data.update(eligibility_check_details)           
        else :
            deed_data = frappe.new_doc("WATHEQ Deed")
            deed_data.deed_owner = frappe.session.user
            deed_data.deed_number = data["deedDetails"]["deedNumber"]
            deed_data.deed_serial = data["deedDetails"]["deedSerial"]
            deed_data.deed_date = data["deedDetails"]["deedDate"]      
            deed_data.deed_text = data["deedDetails"]["deedText"]
            # courtdetails_section
            deed_data.deed_source = data["courtDetails"]["deedSource"]
            deed_data.deed_city = data["courtDetails"]["deedCity"]
            # informations_tab
            deed_data.deed_status = data["deedStatus"]      
            deed_data.deed_area = data["deedInfo"]["deedArea"]   
            deed_data.deed_area_text = data["deedInfo"]["deedAreaText"] 
            # informations_tab
            deed_data.is_real_estate_constrained = data["deedInfo"]["isRealEstateConstrained"]      
            deed_data.is_real_estate_halted = data["deedInfo"]["isRealEstateHalted"]   
            deed_data.is_reale_state_mortgaged = data["deedInfo"]["isRealEstateMortgaged"] 
            deed_data.is_reale_statet_estamented = data["deedInfo"]["isRealEstateTestamented"] 

            # # deedlimitsdetails__n_s__section
            deed_data.north_limit_name = data["deedLimitsDetails"]["northLimitName"]      
            deed_data.north_limit_description = data["deedLimitsDetails"]["northLimitDescription"]   
            deed_data.north_limit_length = data["deedLimitsDetails"]["northLimitLength"] 
            deed_data.north_limit_length_char = data["deedLimitsDetails"]["northLimitLengthChar"]

            deed_data.south_limit_name = data["deedLimitsDetails"]["southLimitName"]      
            deed_data.south_limit_description = data["deedLimitsDetails"]["southLimitDescription"]   
            deed_data.south_limit_length = data["deedLimitsDetails"]["southLimitLength"] 
            deed_data.south_limit_length_char = data["deedLimitsDetails"]["southLimitLengthChar"]

            # # informations_tab
            deed_data.east_limit_name = data["deedLimitsDetails"]["eastLimitName"]      
            deed_data.east_limit_description = data["deedLimitsDetails"]["eastLimitDescription"]   
            deed_data.east_limit_length = data["deedLimitsDetails"]["eastLimitLength"] 
            deed_data.east_limit_length_char = data["deedLimitsDetails"]["eastLimitLengthChar"]

            deed_data.west_limit_name = data["deedLimitsDetails"]["westLimitName"]      
            deed_data.west_limit_description = data["deedLimitsDetails"]["westLimitDescription"]   
            deed_data.west_limit_length = data["deedLimitsDetails"]["westLimitLength"] 
            deed_data.west_limit_length_char = data["deedLimitsDetails"]["westLimitLengthChar"]


            # Add Owner Details to the Deed (assuming each owner is a row in deedOwners)
            for owner in data.get("ownerDetails", []):
                deed_data.append("owner_details", {
                    "id_number": owner["idNumber"],
                    "owner_name": owner["ownerName"],
                    "birth_date": owner["birthDate"],
                    "id_type":owner["idType"],
                    "id_type_text":owner["idTypeText"],
                    "owner_type":owner["ownerType"],
                    "nationality":owner["nationality"],
                    "owning_area":owner["owningArea"],
                    "owning_amount":owner["owningAmount"],
                    "constrained":owner["constrained"],
                    "halt":owner["halt"],
                    "pawned":owner["pawned"],
                    "testament":owner["testament"],
                })

            # Add Real Estate Details to the Deed (assuming each property is a row in realEstateDetails)
            for property in data.get("realEstateDetails", []):
                deed_data.append("real_estate_details", {
                    "deed_serial": property["deedSerial"],
                    "region_code": property["regionCode"],
                    "region_name": property["regionName"],
                    "city_code": property["cityCode"],
                    "city_name": property["cityName"],
                    "real_estate_type_name": property["realEstateTypeName"],
                    "land_number": property["landNumber"],
                    "plan_number": property["planNumber"],
                    "area": property["area"],
                    "area_text": property["areaText"],
                    "district_code": property["districtCode"],
                    "district_name": property["districtName"],
                    "location_description": property["locationDescription"],
                    "constrained": property["constrained"],
                    "halt": property["halt"],
                    "pawned": property["pawned"],
                    "testament": property["testament"],
                    "is_north_riyadh_exceptioned": property["isNorthRiyadhExceptioned"],
                    "north_limit_code": property["realEstateBorderDetails"]["northLimitCode"],
                    "north_limit_description": property["realEstateBorderDetails"]["northLimitDescription"],
                    "north_limit_length": property["realEstateBorderDetails"]["northLimitLength"],
                    "north_limit_length_char": property["realEstateBorderDetails"]["northLimitLengthChar"],
                    "south_limit_code": property["realEstateBorderDetails"]["southLimitCode"],
                    "south_limit_description": property["realEstateBorderDetails"]["southLimitDescription"],
                    "south_limit_length": property["realEstateBorderDetails"]["southLimitLength"],
                    "south_limit_length_char": property["realEstateBorderDetails"]["southLimitLengthChar"],
                    "east_limit_code": property["realEstateBorderDetails"]["eastLimitCode"],
                    "east_limit_description": property["realEstateBorderDetails"]["eastLimitDescription"],
                    "east_limit_length": property["realEstateBorderDetails"]["eastLimitLength"],
                    "east_limit_length_char": property["realEstateBorderDetails"]["eastLimitLengthChar"],
                    "west_limit_code": property["realEstateBorderDetails"]["westLimitCode"],
                    "west_limit_description": property["realEstateBorderDetails"]["westLimitDescription"],
                    "west_limit_length": property["realEstateBorderDetails"]["westLimitLength"],
                    "west_limit_length_char": property["realEstateBorderDetails"]["westLimitLengthChar"],
                    })
            
            deed_data.save(ignore_permissions=True)
            deed_data = deed_data.as_dict()
            eligibility_request = create_elgibility_request([deed_data.name] , deed_source = "WATHEQ Deed")
            frappe.db.commit()
            deed_data.workflow_state = "NEW"
            deed_data.wizard_step = 2
            deed_data.request_id = eligibility_request.name
            
        return deed_data
    except Exception as e:
        frappe.throw(str(e))

# Fetch the first deed created by the current user with status 
@frappe.whitelist(methods=['GET'])
def get_user_last_active_deed(status = None):
    document = get_deed_request_details_by_status()
    if document:
        deed_data = frappe.get_doc("WATHEQ Deed" , document["deed_number"]).as_dict()
        deed_data.workflow_state = status
        deed_data.wizard_step = document["wizard_step"]
        deed_data.request_id = document["request_id"]

        return deed_data
    return None

# Fetch all Deeds Eligibility Request created by the current user with status
@frappe.whitelist(methods=['GET'])
def get_user_deeds(status):
    # Get the current logged-in user
    filters = {"deed_owner": frappe.session.user}
    if(status != ""):
        filters["workflow_state"] = status
        
    return frappe.get_all(
            "WATHEQ Deed",  
            filters=filters,
            fields=["deed_number", "deed_serial", "deed_city", "workflow_state"],  # Specify fields you need
            order_by="modified desc"
        )

# Update deed eligibility request state
@frappe.whitelist(methods=['POST'])
def update_deed_doc(deed_id,updates):
    try:
        if frappe.db.exists("WATHEQ Deed" , {'deed_number' : deed_id , "deed_owner" : frappe.session.user}):
            deedDoc = frappe.get_doc("WATHEQ Deed" , {"deed_number" : deed_id , "deed_owner" : frappe.session.user})
            # Check if the current user is the owner
            if deedDoc.deed_owner != frappe.session.user:
                frappe.local.response.http_status_code = 403
                return {
                    "status": False,
                    "message": _("You are not the owner of this deed")
                }

            # Update each field in the dictionary
            for field, value in updates.items():
                if hasattr(deedDoc, field):  # Check if the field exists on the DocType
                    setattr(deedDoc, field, value)
                else:
                    print(f"Warning: '{field}' does not exist on '{deedDoc.doctype}' and will be ignored")


            # Save the changes
            deedDoc.save()
            frappe.db.commit()  # Commit to ensure changes are saved to the database
            return {
                "status": True,
                "message": _("Deed updated successfully")
            }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(),"WATHEQ exception : " + str(e))
        return {
            "status" : False,
            "message": str(e)
        }
