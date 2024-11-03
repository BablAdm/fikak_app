
import frappe
from frappe import _
import requests
import uuid

from datetime import datetime , timedelta
import frappe.utils
import jwt
import json


REQUEST_ERRORS = {
    "422-031-046" : "طلب غير صالح: تم إرسال بيانات غير صالحة",
    "400-034-050" : "هناك طلب نشط. لقد حاولت إنشاء طلب جديد بينما لا يزال هناك طلب نشط موجود لنفس الهوية",
    "400-034-053" : "المعاملة غير موجودة. لقد حاولت الحصول على حالة الطلب باستخدام رقم معاملة غير صحيح.",
    "400-034-051" : "المعاملة منتهية. لقد حاولت الحصول على حالة الطلب باستخدام رقم معاملة منتهي الصلاحية."
} 

def creat_new_wathiq_request_deed(national_id ,deed_id , request_id , endpoint , app_id , app_key):
    try:
        params = {
            "local": "en",  # replace with actual 'local' param value
            "requestId": request_id
        }

        # Define the JSON body
        payload = {
            "nationalId":national_id,
            "service": "RequestDigitalServicesEnrollment"
        }

        # Define headers if required (e.g., authentication headers)
        headers = {
            "Content-Type": "application/json",
            "APP-ID": app_id,  # Replace with the actual token
            "APP-KEY" : app_key
        }

        # Make the POST request
        response = requests.post(endpoint +"/api/v1/mfa/request", params=params, json=payload, headers=headers)
        
        if response.status_code in (200 , 201):
            return 200 , {
                "status" : True,
                "data" : response.json(),
            }
        else:
            frappe.log_error(frappe.get_traceback(), " Nafath request error : " + response.text)
            try:
                error =  _(REQUEST_ERRORS[response.json()['code']])
            except :
                error = response.text
            return 500 , {
                "status" : False,
                "message": error
            }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(),"Nafath exception : " + str(e))
        return 500 , {
            "status" : False,
            "message": str(e)
        }
    
def create_new_wathiq_request(national_id ,deed_id , request_id):
    request = frappe.new_doc("WATHIQ Request")
    request.national_id = national_id
    request.request_id = request_id
    request.insert(ignore_permissions=True)
    frappe.db.commit()
    return request

@frappe.whitelist(allow_guest=True)
def generate_wathiq_transaction(national_id):
    try:
        if frappe.db.exists("User" , {'username' : national_id}):
            frappe.local.response.http_status_code = 400
            return {
                "status" : False,
                "message": _("المستخدم موجود بالفعل , يرجى تسجيل الدخول") 
            }
        # TODO : Create Wathiq Request
        request_id = generate_request_id()
        request_doc = create_new_wathiq_request(national_id , request_id)
        nafath_settings = frappe.get_single('WATHIQ Settings')
        response = creat_new_wathiq_request_deed(national_id , request_id , nafath_settings.api_url , nafath_settings.get_password('app_id') ,nafath_settings.get_password('app_key'))
        if response[1]['status']:
            request_doc.transaction_id = response[1]['data']['transId']
            request_doc.random = response[1]['data']['random']
            request_doc.save()
        frappe.local.response.http_status_code = response[0]
        return response[1]
    except Exception as e:
        frappe.log_error(frappe.get_traceback(),"Nafath exception : " + str(e))
        return {
            "status" : False,
            "message": str(e)
        }

def generate_request_id():
    # Generate a UUID
    uuid_part = str(uuid.uuid4())
    
    # Get the current date-time as a formatted string (year, month, day, hour, minute, second, microsecond)
    datetime_part = datetime.now().strftime('%Y%m%d%H%M%S%f')
    
    # Combine UUID with the formatted date-time string
    request_id = f"{uuid_part}{datetime_part}"
    
    return request_id


def insert_callback(jwt , decoded_json):
    doc = frappe.new_doc("Wathiq Callback")
    doc.jwt_token = jwt
    doc.decoded_json = decoded_json
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return doc.name


@frappe.whitelist(allow_guest=False)
def get_deed_data(deedNumber):
    if(frappe.session.user):
        user = frappe.db.get_value("User", {"name": frappe.session.user}, "name")
        ## TODO : We should check if the user has the right to see this deed
        deed_data = frappe.get_doc("Deed Wathiq" , {"deednumber" : deedNumber})
    else:
        frappe.throw("Session expired")  

    

    # if not frappe.db.exists("Wathiq Request" , {"deedNumber" : deedNumber , "transaction_id" : transaction_id , "random" : random}):
    #     frappe.throw("Request not found")
    return deed_data


@frappe.whitelist(allow_guest=True)
def insert_deed(data):

    # file_path = frappe.get_app_path('fikak_app', 'data', 'Wathiq_deed.json')
    # with open(file_path, 'r') as file:
    #     data = json.load(file)

    # Create the parent Deed document
    try:
        if frappe.db.exists("Deed Wathiq" , {"deednumber" : data["deedDetails"]["deedNumber"]}):
            deed_data = frappe.get_doc("Deed Wathiq" , {"deednumber" : data["deedDetails"]["deedNumber"]})            
        else :
            deed_data = frappe.new_doc("Deed Wathiq")
            deed_data.deed_number = data["deedDetails"]["deedNumber"]
            deed_data.deed_serial = data["deedDetails"]["deedSerial"]
            deed_data.deeddate = data["deedDetails"]["deedDate"]      
            deed_data.deedtext = data["deedDetails"]["deedText"]
            # courtdetails_section
            deed_data.deedsource = data["courtDetails"]["deedSource"]
            deed_data.deedcity = data["courtDetails"]["deedCity"]
            # informations_tab
            deed_data.deedstatus = data["deedStatus"]      
            deed_data.deedarea = data["deedInfo"]["deedArea"]   
            deed_data.deedareatext = data["deedInfo"]["deedAreaText"] 
            # informations_tab
            deed_data.isrealestateconstrained = data["deedInfo"]["isRealEstateConstrained"]      
            deed_data.isrealestatehalted = data["deedInfo"]["isRealEstateHalted"]   
            deed_data.isrealestatemortgaged = data["deedInfo"]["isRealEstateMortgaged"] 
            deed_data.isrealestatetestamented = data["deedInfo"]["isRealEstateTestamented"] 

            # # deedlimitsdetails__n_s__section
            deed_data.northlimitname = data["deedLimitsDetails"]["northLimitName"]      
            deed_data.northlimitdescription = data["deedLimitsDetails"]["northLimitDescription"]   
            deed_data.northlimitlength = data["deedLimitsDetails"]["northLimitLength"] 
            deed_data.northlimitlengthchar = data["deedLimitsDetails"]["northLimitLengthChar"]

            deed_data.southlimitname = data["deedLimitsDetails"]["southLimitName"]      
            deed_data.southlimitdescription = data["deedLimitsDetails"]["southLimitDescription"]   
            deed_data.southlimitlength = data["deedLimitsDetails"]["southLimitLength"] 
            deed_data.southlimitlengthchar = data["deedLimitsDetails"]["southLimitLengthChar"]

            # # informations_tab
            deed_data.eastlimitname = data["deedLimitsDetails"]["eastLimitName"]      
            deed_data.eastlimitdescription = data["deedLimitsDetails"]["eastLimitDescription"]   
            deed_data.eastlimitlength = data["deedLimitsDetails"]["eastLimitLength"] 
            deed_data.eastlimitlengthchar = data["deedLimitsDetails"]["eastLimitLengthChar"]

            deed_data.westlimitname = data["deedLimitsDetails"]["westLimitName"]      
            deed_data.westlimitdescription = data["deedLimitsDetails"]["westLimitDescription"]   
            deed_data.westlimitlength = data["deedLimitsDetails"]["westLimitLength"] 
            deed_data.westlimitlengthchar = data["deedLimitsDetails"]["westLimitLengthChar"]


            # Add Owner Details to the Deed (assuming each owner is a row in deedOwners)
            for owner in data.get("ownerDetails", []):
                # existing_owner = frappe.db.exists("Deed Owner", {"idnumber": owner["idNumber"]})

                # if existing_owner:
                #     owner_data = frappe.get_doc("Deed Owner" , {"idnumber" : existing_owner})
                #     # If owner exists, add the existing reference
                #     deed_data.append("table_fmbl", {
                #         "doctype": "Deed Owner",
                #         "idnumber": existing_owner  # Reference the existing owner's name (ID)
                #     })
                # else:
                # Now append this newly created owner to the deed
                deed_data.append("table_fmbl", {
                    "doctype": "Deed Owner",
                    "idnumber": owner["idNumber"],
                    "ownername": owner["ownerName"],
                    "birthdate": owner["birthDate"],
                    "idtype":owner["idType"],
                    "idtypetext":owner["idTypeText"],
                    "ownertype":owner["ownerType"],
                    "nationality":owner["nationality"],
                    "owningarea":owner["owningArea"],
                    "owningamount":owner["owningAmount"],
                    "constrained":owner["constrained"],
                    "halt":owner["halt"],
                    "pawned":owner["pawned"],
                    "testament":owner["testament"],
                })

            # Add Real Estate Details to the Deed (assuming each property is a row in realEstateDetails)
            for property in data.get("realEstateDetails", []):
                # existing_realEstate = frappe.db.exists("realEstateDetails", {"deedserial": property["deedSerial"]})
                # if existing_realEstate:
                #     realEstate_data = frappe.get_doc("realEstateDetails" , {"deedserial" : existing_realEstate})
                #     # If RealEstate exists, add the existing reference
                #     deed_data.append("table_bepd", {
                #         "doctype": "realEstateDetails",
                #         "deedserial": existing_realEstate  # Reference the existing owner's name (ID)
                #     })
                # else:
                # Now append this newly created RealEstate to the deed
                deed_data.append("table_bepd", {
                    "doctype": "realEstateDetails",
                    "deedserial": property["deedSerial"],
                    "regioncode": property["regionCode"],
                    "regionname": property["regionName"],
                    "citycode": property["cityCode"],
                    "cityname": property["cityName"],
                    "realestatetypename": property["realEstateTypeName"],
                    "landnumber": property["landNumber"],
                    "plannumber": property["planNumber"],
                    "area": property["area"],
                    "areatext": property["areaText"],
                    "districtcode": property["districtCode"],
                    "districtname": property["districtName"],
                    "locationdescription": property["locationDescription"],
                    "constrained": property["constrained"],
                    "halt": property["halt"],
                    "pawned": property["pawned"],
                    "testament": property["testament"],
                    "isnorthriyadhexceptioned": property["isNorthRiyadhExceptioned"],
                    "northlimitcode": property["realEstateBorderDetails"]["northLimitCode"],
                    "northlimitcescription": property["realEstateBorderDetails"]["northLimitDescription"],
                    "northlimitlength": property["realEstateBorderDetails"]["northLimitLength"],
                    "northlimitlLengthchar": property["realEstateBorderDetails"]["northLimitLengthChar"],
                    "southlimitcode": property["realEstateBorderDetails"]["southLimitCode"],
                    "southlimitdescription": property["realEstateBorderDetails"]["southLimitDescription"],
                    "southlimitlength": property["realEstateBorderDetails"]["southLimitLength"],
                    "southlimitlengthchar": property["realEstateBorderDetails"]["southLimitLengthChar"],
                    "eastlimitcode": property["realEstateBorderDetails"]["eastLimitCode"],
                    "eastlimitdescription": property["realEstateBorderDetails"]["eastLimitDescription"],
                    "eastlimitlength": property["realEstateBorderDetails"]["eastLimitLength"],
                    "eastlimitlengthchar": property["realEstateBorderDetails"]["eastLimitLengthChar"],
                    "westlimitcode": property["realEstateBorderDetails"]["westLimitCode"],
                    "westlimitdescription": property["realEstateBorderDetails"]["westLimitDescription"],
                    "westlimitlength": property["realEstateBorderDetails"]["westLimitLength"],
                    "westlimitlengthchar": property["realEstateBorderDetails"]["westLimitLengthChar"],
                    })
            deed_data.save(ignore_permissions=True)
            frappe.db.commit()
        return deed_data
    except Exception as e:
        frappe.throw(str(e))



@frappe.whitelist(allow_guest=True)
def upate_deed_data(random , transaction_id , national_id , user_data ):
    if not frappe.db.exists("Wathiq Request" , {"national_id" : national_id , "transaction_id" : transaction_id , "random" : random}):
        frappe.throw("Request not found")
    try:
        
        # user = frappe.get_doc("User" , {"username" : national_id})
        # update_password(user.name , user_data.get("password"))
        # user.email = user_data.get("email")
        # user.save(ignore_permissions=True)
        # person_data = frappe.get_doc("Person Data" , {"nin" : national_id})
        # person_data.income_range = user_data.get("income_range")
        # person_data.income_source = user_data.get("income_source")
        # person_data.martial_status = user_data.get("martial_status")
        # person_data.phone_number = user_data.get("phone_number")
        # person_data.save(ignore_permissions=True)
        
        # frappe.db.commit()
        # login_manager = frappe.auth.LoginManager()
        # login_manager.authenticate(user=user.name, pwd=user_data.get("password"))
        # login_manager.post_login()

        return user_data
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "status" : False,
            "message" : str(e)
        }