
import frappe
from frappe import _
import requests
import uuid

from datetime import datetime
import jwt

REQUEST_ERRORS = {
    "422-031-046" : "طلب غير صالح: تم إرسال بيانات غير صالحة",
    "400-034-050" : "هناك طلب نشط. لقد حاولت إنشاء طلب جديد بينما لا يزال هناك طلب نشط موجود لنفس الهوية",
    "400-034-053" : "المعاملة غير موجودة. لقد حاولت الحصول على حالة الطلب باستخدام رقم معاملة غير صحيح.",
    "400-034-051" : "المعاملة منتهية. لقد حاولت الحصول على حالة الطلب باستخدام رقم معاملة منتهي الصلاحية."
} 

def creat_new_nafath_request(national_id , request_id , endpoint , app_id , app_key):
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
            
            return 500 , {
                "status" : False,
                "message": _(REQUEST_ERRORS[response.json()['code']])
            }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(),"Nafath exception : " + str(e))
        return 500 , {
            "status" : False,
            "message": str(e)
        }
    
def create_new_nafath_request(national_id , request_id):
    request = frappe.new_doc("NAFATH Request")
    request.national_id = national_id
    request.request_id = request_id
    request.insert(ignore_permissions=True)
    frappe.db.commit()
    return request

@frappe.whitelist(allow_guest=True)
def generate_nafath_transaction(national_id):
    request_id = generate_request_id()
    request_doc = create_new_nafath_request(national_id , request_id)
    nafath_settings = frappe.get_single('NAFATH Settings')
    response = creat_new_nafath_request(national_id , request_id , nafath_settings.api_url , nafath_settings.get_password('app_id') ,nafath_settings.get_password('app_key'))
    if response[1]['status']:
        request_doc.transaction_id = response[1]['data']['transId']
        request_doc.random = response[1]['data']['random']
        request_doc.save()
    frappe.local.response.http_status_code = response[0]
    return response[1]
    

def generate_request_id():
    # Generate a UUID
    uuid_part = str(uuid.uuid4())
    
    # Get the current date-time as a formatted string (year, month, day, hour, minute, second, microsecond)
    datetime_part = datetime.now().strftime('%Y%m%d%H%M%S%f')
    
    # Combine UUID with the formatted date-time string
    request_id = f"{uuid_part}{datetime_part}"
    
    return request_id

@frappe.whitelist(allow_guest = True)
def nafath_callback(token , transId , requestId):
    try:
        token_decoded = decode_jwt_token(token)
        if token_decoded.get('error'):
            return token_decoded
        request_doc = frappe.get_doc("NAFATH Request" , {"transaction_id" : transId })
        request_doc.request_jwt_decoded = token_decoded
        request_doc.request_token = token
        request_doc.save(ignore_permissions=True)
        return {
            "status" : True,
            "data": token_decoded,
            "message" : "Request updated successfully"
        } 
    except Exception as e:
        return str(e)

def decode_jwt_token(token):
    try:
        # Decode the JWT token without verifying the signature
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        
        # Return the decoded JSON object (payload)
        return decoded_token
    
    except jwt.InvalidTokenError as e:
        frappe.throw(f"Invalid token: {str(e)}")

