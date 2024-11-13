
import frappe
from frappe import _
import json

def get_deed_data():
    try:
        # Construct the file path
        file_path = frappe.get_app_path('fikak_app', 'data', 'wathiq_deed.json')
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data
    except Exception as e:
        frappe.throw(_("Unable to retrieve deed data."))