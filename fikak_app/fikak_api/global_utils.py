import uuid
import frappe

from datetime import datetime , timedelta

def generate_request_id():
    # Generate a UUID
    uuid_part = str(uuid.uuid4())
    
    # Get the current date-time as a formatted string (year, month, day, hour, minute, second, microsecond)
    datetime_part = datetime.now().strftime('%Y%m%d%H%M%S%f')
    
    # Combine UUID with the formatted date-time string
    request_id = f"{uuid_part}{datetime_part}"
    
    return request_id


# Function to check if we are in dev mod in order to get the concerned user for each services
def get_dev_mod_propos():

    try:
        # get dev mod props
        dev_mod_props = frappe.get_single('DEV MOD PROPS')
            
        return dev_mod_props
    except Exception as e:
        
        return ""