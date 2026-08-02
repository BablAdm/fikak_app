app_name = "fikak_app"
app_title = "Fikak"
app_publisher = "Waseera"
app_description = "Asset monetization & financing platform"
app_email = "dev@waseera.sa"
app_license = "MIT"

# Expose whitelisted API methods
# All @frappe.whitelist() decorated functions in api.py and fikak_api/*.py
# are auto-discovered; no explicit registration needed.

# Override standard login with JWT-based login
override_whitelisted_methods = {
    "login": "fikak_app.api.custom_login",
}
