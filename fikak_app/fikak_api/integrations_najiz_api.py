
import frappe
from frappe import _
import requests
import uuid

from datetime import datetime , timedelta
import frappe.utils
import jwt

from frappe.utils.password import update_password

REQUEST_ERRORS = {
    "422-031-046" : "طلب غير صالح: تم إرسال بيانات غير صالحة",
    "400-034-050" : "هناك طلب نشط. لقد حاولت إنشاء طلب جديد بينما لا يزال هناك طلب نشط موجود لنفس الهوية",
    "400-034-053" : "المعاملة غير موجودة. لقد حاولت الحصول على حالة الطلب باستخدام رقم معاملة غير صحيح.",
    "400-034-051" : "المعاملة منتهية. لقد حاولت الحصول على حالة الطلب باستخدام رقم معاملة منتهي الصلاحية."
} 

def creat_new_najiz_request(national_id ,deed_id , request_id , endpoint , app_id , app_key):
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
    
def create_new_najiz_request(national_id ,deed_id , request_id):
    request = frappe.new_doc("NADJIZ Request")
    request.national_id = national_id
    request.request_id = request_id
    request.insert(ignore_permissions=True)
    frappe.db.commit()
    return request

@frappe.whitelist(allow_guest=True)
def generate_najiz_transaction(national_id):
    try:
        if frappe.db.exists("User" , {'username' : national_id}):
            frappe.local.response.http_status_code = 400
            return {
                "status" : False,
                "message": _("المستخدم موجود بالفعل , يرجى تسجيل الدخول") 
            }
        request_id = generate_request_id()
        request_doc = create_new_najiz_request(national_id , request_id)
        nafath_settings = frappe.get_single('NADJIZ Settings')
        response = creat_new_najiz_request(national_id , request_id , nafath_settings.api_url , nafath_settings.get_password('app_id') ,nafath_settings.get_password('app_key'))
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

@frappe.whitelist(allow_guest = True)
def najiz_callback(token , transId , requestId , national_id = None):
    try:
        decoded_token = decode_jwt_token(token)
        callback_id = insert_callback(token , decoded_token)
        if decoded_token.get('error'):
            return decoded_token
        
        if national_id:
            decoded_token['PersonId'] = national_id
        if decoded_token.get("status") == "REJECTED":
            update_request_status(transId , requestId ,"REJECTED")
            return
        
        user_doc = insert_user_data(decoded_token)
        
        insert_deed_data(user_doc , decoded_token)
        update_request_status(transId , requestId , "COMPLETED")
        request_doc = frappe.get_doc("NAFATH Request" , {"transaction_id" : transId })
        request_doc.nafath_callback = callback_id
        request_doc.save(ignore_permissions=True)
        frappe.db.commit()
        return {
            "status" : True,
            "data": decoded_token,
            "message" : "Request updated successfully"
        } 
    except Exception as e:
        frappe.log_error(frappe.get_traceback(),"Nafath callback : " + str(e))
        return str(e)

def insert_callback(jwt , decoded_json):
    doc = frappe.new_doc("NAFATH Callback")
    doc.jwt_token = jwt
    doc.decoded_json = decoded_json
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return doc.name

@frappe.whitelist(allow_guest=True)
def check_request_status(national_id , tansaction_id , random ):
    try:
        # nafath_settings = frappe.get_single('NAFATH Settings')
        #response = check_request(national_id , tansaction_id, random , nafath_settings.api_url , nafath_settings.get_password('app_id') ,nafath_settings.get_password('app_key'))
        # frappe.local.response.http_status_code = response[0]
        # return response[1]
        request_record = frappe.get_doc("NAJIZ Request" , {  "transaction_id" : tansaction_id , "random" : random})
        status = request_record.status
        if is_request_older_than_3_minutes(request_record):
            update_request_status(tansaction_id , request_record.request_id , "EXPIRED")
            status = "EXPIRED"
        return {
            "status" : True,
            "data" : {
                "status" : status
            }
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(),"NAJIZ exception : " + str(e))
        return {
            "status" : False,
            "message": str(e)
        }

def is_request_older_than_3_minutes(request_record):
    
    # Get the creation timestamp from the record
    # Get the creation timestamp from the record and convert it to datetime
    creation_time = datetime.strptime(str(request_record.creation), "%Y-%m-%d %H:%M:%S.%f")
    
    # Calculate the time 3 minutes after the creation time
    time_limit = creation_time + timedelta(minutes=3)

    # Get the current time from frappe.utils.now() and convert it to datetime
    current_time = datetime.strptime(frappe.utils.now(), "%Y-%m-%d %H:%M:%S.%f")

    # Check if the current time has passed the time limit
    return current_time > time_limit  # True if more than 3 minutes have passed, False otherwise

def update_request_status(tansaction_id ,request_id , status):
    request_record = frappe.get_doc("NAFATH Request" , {"request_id" : request_id , "transaction_id" : tansaction_id})
    if request_record.status != status:
        request_record.status = status
        request_record.save(ignore_permissions=True)
    

def check_request(national_id , tansaction_id , random , endpoint, app_id , app_key):
    try:
        # Define the JSON body
        payload = {
            "nationalId":national_id,
            "transId": tansaction_id,
            "random": random
        }

        # Define headers if required (e.g., authentication headers)
        headers = {
            "Content-Type": "application/json",
            "APP-ID": app_id,  # Replace with the actual token
            "APP-KEY" : app_key
        }

        # Make the POST request
        response = requests.post(endpoint +"/api/v1/mfa/request/status",  json=payload, headers=headers)
        if response.status_code in (200 , 201):
            return response.status_code , {
                "status" : True,
                "data" : response.json(),
            }
        else:
            frappe.log_error(frappe.get_traceback(), " Nafath request error : " + response.text)
            
            return response.status_code   , {
                "status" : False,
                "message": _(REQUEST_ERRORS[response.text])
            }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(),"Nafath exception : " + str(e))
        return 500 , {
            "status" : False,
            "message": str(e)
        }



def decode_jwt_token(token):
    try:
        # Decode the JWT token without verifying the signature
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        
        # Return the decoded JSON object (payload)
        return decoded_token
    
    except jwt.InvalidTokenError as e:
        frappe.throw(f"Invalid token: {str(e)}")

def insert_deed_data(wajiz_data):
    user_exists = frappe.db.exists("User" , {"username" : str(wajiz_data['PersonId'])})
    if not user_exists:
        user = frappe.new_doc("User")
        user.last_name = wajiz_data.get('familyName') or wajiz_data.get('lastName')
        user.first_name = wajiz_data['firstName']
        formatted_date = datetime.strptime(wajiz_data['dateOfBirthG'], "%d-%m-%Y").strftime("%Y-%m-%d")
        user.birth_date = formatted_date
        user.username = str(wajiz_data['PersonId'])
        user.email = str(wajiz_data['PersonId']) + "@waseera.sa"
        user.save(ignore_permissions=True)
        return user.name
    else:
        return user_exists


def insert_deed_data(user_name , wajiz_data):
    try:
        if not frappe.db.exists("Deed Data" , {"user" : user_name}):
            deed_data = frappe.new_doc("Deed Data")
            formatted_date = datetime.strptime(wajiz_data['dateOfBirthG'], "%d-%m-%Y").strftime("%Y-%m-%d")
            deed_data.birth_date = formatted_date
            deed_data.user = user_name
            
            deed_data.first_name = wajiz_data.get('firstName')
            deed_data.last_name = wajiz_data.get('familyName') or wajiz_data.get('lastName')
            deed_data.nin = wajiz_data.get('PersonId')
            deed_data.user_type = "B2C User"
            deed_data.grand_father_name = wajiz_data.get('grandFatherName')
            deed_data.second_name = wajiz_data.get('fatherName')
            country_exists = frappe.get_all("Country" , filters={'code' : str(wajiz_data.get("nationalityCode"))}  , fields= ["name"] , pluck="name")
            deed_data.nationality = country_exists[0] if country_exists else None
            deed_data.father_name = wajiz_data.get('fatherName')
            deed_data.english_third_name = wajiz_data.get('englishThirdName')
            deed_data.gender = "Male" if wajiz_data.get('gender') == "M" else "Female"
            deed_data.nationality_code = wajiz_data.get("nationalityCode")
            deed_data.exp = wajiz_data.get("exp")
            deed_data.street = wajiz_data["nationalAddress"][0].get("streetName")
            if not frappe.db.exists("City" , wajiz_data["nationalAddress"][0].get("city")):
                city = frappe.new_doc("City")
                city.city_name = wajiz_data["nationalAddress"][0].get("city")
                city.save(ignore_permissions=True)

            deed_data.city = wajiz_data["nationalAddress"][0].get("city")
            deed_data.region_name = wajiz_data["nationalAddress"][0].get("regionName")
            deed_data.additional_number = wajiz_data["nationalAddress"][0].get("additionalNumber")
            deed_data.building_number = wajiz_data["nationalAddress"][0].get("buildingNumber")
            deed_data.post_code = wajiz_data["nationalAddress"][0].get("postCode")
            deed_data.district = wajiz_data["nationalAddress"][0].get("district")
            deed_data.save(ignore_permissions=True)
            return deed_data
    except Exception as e:
        frappe.throw(str(e))

@frappe.whitelist(allow_guest=True)
def get_deed_data(national_id,deed_id , random , transaction_id):
    deed_data = frappe.get_doc("Deed Data" , {"deed_id" : deed_id})
    if not frappe.db.exists("NAJIZ Request" , {"deed_id" : deed_id , "transaction_id" : transaction_id , "random" : random}):
        frappe.throw("Request not found")
    return deed_data

@frappe.whitelist(allow_guest=True)
def upate_deed_data(random , transaction_id , national_id , user_data ):
    if not frappe.db.exists("NAJIZ Request" , {"national_id" : national_id , "transaction_id" : transaction_id , "random" : random}):
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