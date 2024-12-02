import uuid
import frappe
from frappe import _

from datetime import datetime

def generate_request_id():
    # Generate a UUID
    uuid_part = str(uuid.uuid4())
    
    # Get the current date-time as a formatted string (year, month, day, hour, minute, second, microsecond)
    datetime_part = datetime.now().strftime('%Y%m%d%H%M%S%f')
    
    # Combine UUID with the formatted date-time string
    request_id = f"{uuid_part}{datetime_part}"
    
    return request_id


def translate(data, skiped_keys=[]):
    """
    Recursively translates the given data using the specified language.

    Args:
        data: The data to be translated.
        skiped_keys: A list of keys to be skipped during translation.

    Returns:
        The translated data.
    """
    pass_translation = ['id', 'email', 'first_name',
                        'last_name', 'user_name'] + skiped_keys

    def translate_data(data):

        if isinstance(data, dict):
            for key, value in data.items():
                if not any(s in key for s in pass_translation):
                    data[key] = translate_data(value)

        elif isinstance(data, list):
            for i in range(len(data)):
                data[i] = translate_data(data[i])

        return _(data, frappe.local.request.headers.get('Accept-Language'))

    translated_data = translate_data(data)
    return translated_data
