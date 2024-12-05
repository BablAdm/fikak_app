import uuid
import frappe
from frappe import _

from datetime import datetime
from convertdate import islamic
import re


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



def convert_hijri_to_gregorian(hijri_date_str):
    """
    Convert a Hijri date string to Gregorian and format it as an ISO 8601 date string.

    :param hijri_date_str: Hijri date as a string in the format 'YYYY-M-Dxxx'
                           (e.g., '1446-4-702')
    :return: Gregorian date formatted as 'YYYY-MM-DDT00:00:00Z'
    """
    # Extract the Hijri year, month, and day using regex
    match = re.match(r"(\d+)-(\d+)-(\d+)", hijri_date_str)
    if not match:
        raise ValueError("Invalid Hijri date format. Expected format: 'YYYY-M-Dxxx'.")

    hijri_year, hijri_month, hijri_day = map(int, match.groups())

    # Convert Hijri to Gregorian
    gregorian_year, gregorian_month, gregorian_day = islamic.to_gregorian(hijri_year, hijri_month, hijri_day)

    # Format as ISO 8601
    gregorian_date = datetime(gregorian_year, gregorian_month, gregorian_day)
    return gregorian_date.strftime("%Y-%m-%dT00:00:00Z")