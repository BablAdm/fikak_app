


import frappe
from frappe import _
from pypika import functions as fn
import math
from operator import itemgetter
from itertools import groupby


@frappe.whitelist(methods=['GET'])
def get_user_bank_accounts(global_filter = None , offset = 0 , page_size = 10 , order_direction = -1 , order_by = "creation" , **kw):
    """
    Get the bank accounts of the user.

    Args:
    global_filter (str): A filter to apply to the bank accounts.
    offset (int): The offset of the bank accounts to retrieve.
    page_size (int): The number of bank accounts to retrieve.
    order_direction (int): The order direction of the bank accounts to retrieve.
    order_by (str): The field to order the bank accounts by.
    kw (dict): Additional keyword arguments.

    Returns:
    dict: A dictionary containing the bank accounts of the user.
    """
    if isinstance(offset, str):
        offset = int(offset)
    
    if isinstance(page_size, str):
        page_size = int(page_size)

    bank_account_dt = frappe.qb.DocType("Bank Account Details")
    bank_provider_dt = frappe.qb.DocType("Bank Provider")
    bank_provider_consents_dt = frappe.qb.DocType("Bank Account Details Consent Item")

    query = (
        frappe.qb.from_(bank_account_dt)
        .left_join(bank_provider_dt)
        .on(bank_account_dt.bank_provider == bank_provider_dt.name)
        .left_join(bank_provider_consents_dt)
        .on(bank_account_dt.name == bank_provider_consents_dt.parent)

        .select(
            bank_account_dt.name.as_("bank_account_id"),
            bank_account_dt.account_holder_name,
            bank_account_dt.account_id,
            bank_provider_dt.bank_name,
            bank_account_dt.account_description,
            bank_account_dt.creation,
            bank_account_dt.account_product_type,
            bank_provider_consents_dt.consent_id,
            bank_provider_consents_dt.status,
        )
        .where(bank_account_dt.user == frappe.session.user)
        .limit(page_size)
        .offset(offset)
    )
    # Apply the global filter
    if global_filter:
        query = query.where(
            (fn.Lower(bank_account_dt.bank_name).like(
            f"%{global_filter}%"))|
            (fn.Lower(bank_account_dt.account_number).like(
            f"%{global_filter}%"))|
            (fn.Lower(bank_account_dt.iban).like(
            f"%{global_filter}%"))|
            (fn.Lower(bank_account_dt.currency).like(
            f"%{global_filter}%"))|
            (fn.Lower(bank_account_dt.bank_account_type).like(
            f"%{global_filter}%"))
        )
    
    # Execute the query
    bank_accounts = query.run(as_dict=True)
    data = []
    bank_account_grouper = itemgetter("bank_account_id", "account_holder_name", "account_id", "bank_name" , "account_description" , "account_product_type" , "creation")
    consent_grouper = itemgetter("consent_id", "status" )
    
    for bank_account_key, bank_account_group in groupby(sorted(bank_accounts, key=itemgetter("creation")), bank_account_grouper):
        d = {
            "bank_account_id": bank_account_key[0],
            "account_holder_name": bank_account_key[1],
            "account_id": bank_account_key[2],
            "bank_name": bank_account_key[3],
            "account_description": bank_account_key[4],
            "account_product_type": bank_account_key[5],
            "creation": bank_account_key[6],
            "active_consents" : 0,
        }
        for consent_key, consent_group in groupby(sorted(bank_account_group, key=itemgetter("status")), consent_grouper):
            if consent_key[1] == "ACTIVE":
                d["active_consents"] += 1
        data.append(d)
    
    bank_accounts_len = len(data)
    bank_accounts = data[offset:offset+page_size]

    
    return {
        "status": True,
        "data": bank_accounts,
        "meta": {
            "current_page": int((offset/page_size)+1),
            "total_items": bank_accounts_len,
            "items_per_page": page_size,
            "total_pages": math.ceil(bank_accounts_len / page_size)
        },
        "message": _("Bank accounts retrieved successfully")
    }

@frappe.whitelist(methods=['GET'])
def get_bank_details(bank_account_id):
    """
    Get the details of a bank account.

    Args:
    bank_account_id (str): The ID of the bank account.

    Returns:
    dict: A dictionary containing the details of the bank account.
    """
    try:
        bank_account_doc = frappe.get_doc("Bank Account Details", {"name": bank_account_id, "user": frappe.session.user})

        return {
            "status": True,
            "data": bank_account_doc.as_dict(),
            "message": _("Bank account details retrieved successfully")
        }
    except frappe.DoesNotExistError:
        frappe.local.response.http_status_code = 404
        return {
            "status": False,
            "message": _("Bank account not found")
        }
