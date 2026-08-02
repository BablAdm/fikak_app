#!/usr/bin/env python3
"""
FIKAK END-TO-END CUSTOMER JOURNEY TEST
Full-cycle verification: Auth -> Customer -> KYC -> AML -> Application ->
Approval -> Disbursement -> Payment -> Audit -> RBAC negative tests
Every assertion checked against live server. No fabricated results.
"""
import requests, json, sys

BASE = "http://localhost:8000/api"
results = []

def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((name, status, detail))
    print(f"  [{status}] {name}" + (f"  -> {detail}" if detail and not condition else ""))
    return condition

print("=" * 70)
print("FIKAK E2E CUSTOMER JOURNEY TEST - LIVE VERIFICATION")
print("=" * 70)

# ---- PHASE 1: Authentication ----
print("\nPHASE 1: Authentication & RBAC")
r = requests.post(f"{BASE}/auth/login", json={"email": "admin@fikak.sa", "password": "admin"})
check("Admin login", r.status_code == 200 and r.json().get("success"), r.text[:100])
ADMIN = {"Authorization": f"Bearer {r.json()['token']}"}

r = requests.post(f"{BASE}/auth/login", json={"email": "customer@fikak.sa", "password": "customer1"})
check("Customer login", r.status_code == 200 and r.json().get("success"))
CUSTOMER = {"Authorization": f"Bearer {r.json()['token']}"}

r = requests.post(f"{BASE}/auth/login", json={"email": "admin@fikak.sa", "password": "WRONG"})
check("Invalid credentials rejected (401)", r.status_code == 401)

r = requests.get(f"{BASE}/applications")
check("Unauthenticated request rejected (401)", r.status_code == 401)

r = requests.get(f"{BASE}/auth/profile", headers=ADMIN)
check("Profile retrieval", r.status_code == 200 and r.json()["data"]["role"] == "Admin")

# ---- PHASE 2: Customer Onboarding ----
print("\nPHASE 2: Customer Onboarding")
r = requests.post(f"{BASE}/customers", headers=ADMIN, json={
    "name": "Khalid Al-Otaibi", "email": "khalid@test.sa",
    "phone": "+966555000111", "segment": "Individual"})
check("Create customer", r.status_code == 201, r.text[:150])
CUST_ID = r.json()["id"]

r = requests.get(f"{BASE}/customers", headers=ADMIN)
check("Customer appears in list", any(c["id"] == CUST_ID for c in r.json()["data"]))

r = requests.post(f"{BASE}/customers", headers=ADMIN, json={"name": "Incomplete"})
check("Missing fields rejected (400)", r.status_code == 400)

# ---- PHASE 3: KYC / AML Compliance ----
print("\nPHASE 3: KYC / AML Compliance")
r = requests.post(f"{BASE}/kyc/{CUST_ID}/verify", headers=ADMIN)
check("KYC verification", r.status_code == 200 and r.json()["data"].get("verified") == True, r.text[:150])

r = requests.post(f"{BASE}/aml/{CUST_ID}/check", headers=ADMIN)
aml = r.json().get("data", {})
check("AML screening clear", r.status_code == 200 and aml.get("aml_status") == "Clear", r.text[:150])
check("PEP check performed", "pep_check" in aml)

r = requests.post(f"{BASE}/kyc/{CUST_ID}/verify", headers=CUSTOMER)
check("Customer role blocked from KYC ops (403)", r.status_code == 403)

# ---- PHASE 4: Application Lifecycle ----
print("\nPHASE 4: Application Lifecycle (Submit -> Approve -> Disburse)")
r = requests.post(f"{BASE}/applications", headers=CUSTOMER, json={
    "customer_id": CUST_ID, "product": "Home Loan", "amount": 400000})
check("Customer submits application", r.status_code == 201, r.text[:150])
APP_ID = r.json()["id"]
check("Application status = Submitted", r.json()["data"]["status"] == "Submitted")

r = requests.post(f"{BASE}/applications", headers=CUSTOMER, json={
    "customer_id": CUST_ID, "product": "Home Loan", "amount": 10000})
check("Below-minimum amount rejected (400)", r.status_code == 400)

r = requests.post(f"{BASE}/applications", headers=CUSTOMER, json={
    "customer_id": CUST_ID, "product": "Investment", "amount": 99999999})
check("Above-maximum amount rejected (400)", r.status_code == 400)

r = requests.post(f"{BASE}/applications/{APP_ID}/approve", headers=CUSTOMER)
check("Customer cannot approve own application (403)", r.status_code == 403)

r = requests.post(f"{BASE}/applications/{APP_ID}/disburse", headers=ADMIN)
check("Cannot disburse before approval (400)", r.status_code == 400)

r = requests.post(f"{BASE}/applications/{APP_ID}/approve", headers=ADMIN)
check("Officer/Admin approves application", r.status_code == 200 and r.json()["data"]["status"] == "Approved")

r = requests.post(f"{BASE}/applications/{APP_ID}/disburse", headers=ADMIN)
d = r.json()
check("Loan disbursed", r.status_code == 200 and d["data"]["status"] == "Disbursed", r.text[:150])
check("Disbursement transaction created", "transaction_id" in d and d["transaction_id"].startswith("TXN-"))

# ---- PHASE 5: Payment Processing ----
print("\nPHASE 5: Payment Gateway Integration")
r = requests.post(f"{BASE}/payments", headers=ADMIN, json={
    "application_id": APP_ID, "amount": 15000, "method": "bank_transfer"})
check("Bank transfer payment", r.status_code == 201 and r.json()["data"]["status"] == "Completed", r.text[:150])

r = requests.post(f"{BASE}/payments", headers=ADMIN, json={
    "application_id": APP_ID, "amount": 15000, "method": "credit_card"})
p = r.json()
check("Stripe credit card payment", r.status_code == 201, r.text[:150])
check("Gateway response recorded", p["data"]["gateway_response"]["gateway"] == "Stripe")

r = requests.post(f"{BASE}/payments", headers=ADMIN, json={
    "application_id": APP_ID, "amount": 100, "method": "bitcoin"})
check("Unsupported payment method rejected", r.status_code == 400)

# ---- PHASE 6: Audit & Reporting ----
print("\nPHASE 6: Audit Trail & Dashboard")
r = requests.get(f"{BASE}/audit/logs", headers=ADMIN)
logs = r.json()["data"]
actions = {l["action"] for l in logs}
check("Audit logs populated", r.status_code == 200 and len(logs) > 5)
check("Journey actions traced in audit", {"CREATE", "APPROVE", "DISBURSE", "PAYMENT_PROCESSED"}.issubset(actions),
      f"found: {actions}")

r = requests.get(f"{BASE}/audit/logs", headers=CUSTOMER)
check("Audit logs restricted to Admin (403)", r.status_code == 403)

r = requests.get(f"{BASE}/dashboard/full", headers=ADMIN)
stats = r.json()["data"]["statistics"]
check("Full dashboard aggregation", r.status_code == 200 and stats["disbursed_loans"] >= 1, str(stats))
check("System config (Admin)", requests.get(f"{BASE}/system/config", headers=ADMIN).status_code == 200)

# ---- SUMMARY ----
print("\n" + "=" * 70)
passed = sum(1 for _, s, _ in results if s == "PASS")
failed = sum(1 for _, s, _ in results if s == "FAIL")
print(f"RESULTS: {passed} passed / {failed} failed / {len(results)} total")
if failed:
    print("\nFAILED TESTS:")
    for n, s, d in results:
        if s == "FAIL": print(f"  ✗ {n}: {d}")
    sys.exit(1)
print("ALL TESTS PASSED — VERIFIED AGAINST LIVE SERVER")
sys.exit(0)
