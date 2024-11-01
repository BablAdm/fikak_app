
import frappe
from frappe import _
import requests
import uuid
import json

from datetime import datetime , timedelta

@frappe.whitelist(allow_guest=True)
def get_deed_data():
    try:
        # Construct the file path

        file_path = frappe.get_app_path('fikak_app', 'data', 'najiz_deed.json')
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data
    except Exception as e:
        frappe.log_error(f"Error reading deed.json: {e}", _("Deed JSON Error"))
        frappe.throw(_("Unable to retrieve deed data."))