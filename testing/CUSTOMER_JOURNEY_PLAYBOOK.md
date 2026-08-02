# FIKAK CUSTOMER JOURNEY TESTING PLAYBOOK
## Follow these steps in order. Each step lists the action + expected result.

---

## STEP 0 — SETUP (once, ~2 minutes)

If testing on your own machine, copy the files from outputs/ locally first, then:

```bash
pip install flask flask-cors flask-httpauth requests --break-system-packages
cd <folder-with-files>
setsid nohup python3 fikak-complete-deployment.py > fikak.log 2>&1 &
curl http://localhost:8000/api/health        # expect "status":"healthy"
```

Open in browser: `fikak-test-interface.html` (API tester) and keep a terminal for curl.

**Test accounts:**
| Role | Email | Password | Can do |
|---|---|---|---|
| Customer | customer@fikak.sa | customer1 | Submit applications only |
| Officer | officer@fikak.sa | officer1 | Approve, disburse, KYC, payments |
| Admin | admin@fikak.sa | admin | Everything + audit logs |

---

## ACT 1 — CUSTOMER PERSPECTIVE (the journey begins)

### Step 1: Customer logs in
```bash
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"customer@fikak.sa","password":"customer1"}'
```
✅ **Expect:** `"success":true` + a token. Save it:
```bash
CUST_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"email":"customer@fikak.sa","password":"customer1"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
```

### Step 2: Customer browses products
```bash
curl -s http://localhost:8000/api/health | python3 -m json.tool | grep -A5 database_stats
```
Products available: Home Loan (4.25%), Asset Finance (3.50%), Investment (5.00%), Savings (2.50%).

### Step 3: Get a customer ID to apply with
```bash
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"email":"admin@fikak.sa","password":"admin"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

curl -s http://localhost:8000/api/customers -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool | grep '"id"'
```
Copy one `CUST-XXXXXXXX` id.

### Step 4: Customer submits a financing application
```bash
curl -s -X POST http://localhost:8000/api/applications \
  -H "Content-Type: application/json" -H "Authorization: Bearer $CUST_TOKEN" \
  -d '{"customer_id":"CUST-XXXXXXXX","product":"Home Loan","amount":400000}'
```
✅ **Expect:** `"status":"Submitted"` + an `APP-XXXXXXXX` id. **Save this APP_ID.**

### Step 5 (negative test): Try to break the rules
```bash
# Amount too low — expect 400 error
curl -s -X POST http://localhost:8000/api/applications \
  -H "Content-Type: application/json" -H "Authorization: Bearer $CUST_TOKEN" \
  -d '{"customer_id":"CUST-XXXXXXXX","product":"Home Loan","amount":10000}'

# Customer tries to approve own application — expect 403
curl -s -X POST http://localhost:8000/api/applications/APP-XXXXXXXX/approve \
  -H "Authorization: Bearer $CUST_TOKEN"
```
✅ **Expect:** Both rejected. If either succeeds, that's a bug — report it.

---

## ACT 2 — BACK OFFICE (compliance & approval)

### Step 6: Officer runs KYC verification
```bash
curl -s -X POST http://localhost:8000/api/kyc/CUST-XXXXXXXX/verify \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```
✅ **Expect:** `"verified":true`

### Step 7: Officer runs AML screening
```bash
curl -s -X POST http://localhost:8000/api/aml/CUST-XXXXXXXX/check \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```
✅ **Expect:** `"aml_status":"Clear"`, `"pep_check":false`

### Step 8 (negative test): Try disbursing BEFORE approval
```bash
curl -s -X POST http://localhost:8000/api/applications/APP-XXXXXXXX/disburse \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```
✅ **Expect:** 400 error — "must be approved before disbursement"

### Step 9: Officer approves the application
```bash
curl -s -X POST http://localhost:8000/api/applications/APP-XXXXXXXX/approve \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```
✅ **Expect:** `"status":"Approved"` + approval_date set

### Step 10: Officer disburses the loan
```bash
curl -s -X POST http://localhost:8000/api/applications/APP-XXXXXXXX/disburse \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```
✅ **Expect:** `"status":"Disbursed"` + `transaction_id: TXN-XXXXXXXX`

---

## ACT 3 — REPAYMENT

### Step 11: Process a repayment (bank transfer)
```bash
curl -s -X POST http://localhost:8000/api/payments \
  -H "Content-Type: application/json" -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"application_id":"APP-XXXXXXXX","amount":15000,"method":"bank_transfer"}'
```
✅ **Expect:** `"status":"Completed"` + gateway reference `BT-PAY-...`

### Step 12: Process a card payment (Stripe path)
```bash
curl -s -X POST http://localhost:8000/api/payments \
  -H "Content-Type: application/json" -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"application_id":"APP-XXXXXXXX","amount":15000,"method":"credit_card"}'
```
✅ **Expect:** `"gateway":"Stripe"`, transaction `ch_PAY-...`

---

## ACT 4 — VERIFICATION & AUDIT

### Step 13: Review the complete audit trail
```bash
curl -s "http://localhost:8000/api/audit/logs?limit=30" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -m json.tool
```
✅ **Expect:** Every action you performed above logged with timestamp, user, action, entity, IP. Look for: LOGIN_SUCCESS, CREATE, KYC_VERIFY, AML_CHECK, APPROVE, DISBURSE, PAYMENT_PROCESSED.

### Step 14: Verify dashboard reflects the full journey
```bash
curl -s http://localhost:8000/api/dashboard/full \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin)['data']['statistics'], indent=2))"
```
✅ **Expect:** disbursed_loans incremented, your application counted.

### Step 15 (negative test): Customer tries to read audit logs
```bash
curl -s http://localhost:8000/api/audit/logs -H "Authorization: Bearer $CUST_TOKEN"
```
✅ **Expect:** 403 — "Insufficient permissions"

---

## RESET BETWEEN TEST RUNS

Restart the server = fresh seed data (3 customers, 3 apps, 4 products):
```bash
pkill -f fikak-complete-deployment; sleep 1
setsid nohup python3 fikak-complete-deployment.py > fikak.log 2>&1 &
```

## AUTOMATED RE-VERIFICATION ANYTIME
```bash
python3 fikak-e2e-journey-test.py    # runs all 30 checks in ~5 seconds
```

---

## WHAT TO LOG AS A BUG

- Any negative test (Steps 5, 8, 15) that SUCCEEDS instead of being rejected
- Any status transition that skips a state (e.g., Submitted → Disbursed)
- Any action missing from the audit trail
- Any 500 error at any point
- Response times over 100ms consistently

## TEST COMPLETION CHECKLIST

- [ ] Act 1: Customer login + application submitted
- [ ] Act 1: Both negative tests rejected correctly
- [ ] Act 2: KYC verified, AML clear
- [ ] Act 2: Premature disbursement blocked
- [ ] Act 2: Approve → Disburse sequence completed
- [ ] Act 3: Both payment methods processed
- [ ] Act 4: Full audit trail present
- [ ] Act 4: RBAC restriction on audit confirmed
