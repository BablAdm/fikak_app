import frappe
import json


@frappe.whitelist(allow_guest=True)
def notify_clients_on_update():
    # Use Frappe's publish_realtime function to broadcast a message
    event_data = {
        "message": "Document updated",
        "docname": "doc.name",
        "doctype": "doc.doctype"
    }
    print("Send real time message")
    frappe.publish_realtime(
        event="doc_bank_update",  # Event name
        message=json.dumps(event_data) #,
        ##user=doc.owner  # Can target specific user or use None for all
    )



