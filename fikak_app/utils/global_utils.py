import uuid
import frappe
from frappe import _

from datetime import datetime
from convertdate import islamic
import re
from frappe.translate import get_translations

def generate_request_id():
    # Generate a UUID
    uuid_part = str(uuid.uuid4())
    
    # Get the current date-time as a formatted string (year, month, day, hour, minute, second, microsecond)
    datetime_part = datetime.now().strftime('%Y%m%d%H%M%S%f')
    
    # Combine UUID with the formatted date-time string
    request_id = f"{uuid_part}{datetime_part}"
    
    return request_id


def translate(data, skipped_keys=None):
    """
    Translates the given data structure (list or dict) based on the language from request headers.

    Args:
        data (dict | list): The data to be translated. Can be a dictionary or a list of dictionaries.
        skipped_keys (list): List of keys to exclude from translation.

    Returns:
        dict | list: Translated data structure.
    """
    if skipped_keys is None:
        skipped_keys = []

    # Get the desired language from headers, default to 'en'
    language = frappe.local.request.headers.get("Accept-Language", "en")
   
    def translate_value(value, key=None):
        """Translates individual values unless the key is in skipped_keys."""
        if key in skipped_keys:
            return value  # Skip translation for this key
        if isinstance(value, str):
            # Use translations as a dictionary to translate strings
            print("value , "  , key , value ,"  ,  " ,  _(value, frappe.local.request.headers.get('Accept-Language')) )
    
        if isinstance(value, dict):
            return translate_dict(value)  # Recursively translate dictionaries
        if isinstance(value, list):
            return translate_list(value)  # Recursively translate lists
        return value  # Return other types as-is

    def translate_dict(d):
        """Translates all key-value pairs in a dictionary."""
        return {key: translate_value(value, key) for key, value in d.items()}

    def translate_list(lst):
        """Translates all items in a list."""
        return [translate_value(item) for item in lst]

    # Determine the type of data and translate accordingly
    if isinstance(data, dict):
        return translate_dict(data)
    if isinstance(data, list):
        return translate_list(data)

    # Return as-is if data is neither a list nor a dictionary
    return data





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