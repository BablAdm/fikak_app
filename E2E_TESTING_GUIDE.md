# FIKAK ON FRAPPE — END-TO-END TESTING GUIDE

## PHASE 1 — LAUNCH THE REAL PLATFORM (10 minutes)

Prerequisite: **Docker Desktop for Mac** installed and running
(download: https://www.docker.com/products/docker-desktop/)

```bash
cd ~/Downloads/fikak-frappe-stack
bash setup-fikak-mac.sh
```

First run pulls ~2GB of images and takes 5-10 min for site creation.
The script watches progress and prints the access details when done.

## YOUR TESTING ACCESS DETAILS

| Item | Value |
|---|---|
| **URL** | http://localhost:8080 |
| **Username** | Administrator |
| **Password** | shown in setup-fikak-mac.sh output (or check .env.local) |
| **Framework** | Frappe v15 + ERPNext v15.54.5 (real, persistent MariaDB) |

Unlike the preview server, **data persists across restarts** — this is the
production framework with a real database.

## PHASE 1 E2E TEST SCENARIOS (vanilla ERPNext)

After login, complete the setup wizard (country: Saudi Arabia, currency: SAR,
language: English — you can add Arabic in settings later). Then test:

1. **Customer journey** — Selling > Customer > New. Create "Ahmed Al-Suwaiyan".
2. **Arabic/RTL** — Settings > My Settings > Language: العربية. Whole UI flips RTL.
3. **User & roles** — create an "Officer" user, restrict permissions, verify enforcement.
4. **Workflow engine** — Setup > Workflow: build Submitted → Approved → Disbursed
   with role-gated transitions (mirrors what you tested on the preview API).
5. **REST API** — Frappe auto-exposes every DocType:
   ```bash
   # Load the admin password from the file written by setup-fikak-mac.sh:
   source .env.local
   curl -u Administrator:$ADMIN_PASSWORD http://localhost:8080/api/resource/Customer
   ```
6. **Audit trail** — every doc has a version history; check the sidebar timeline.

## PHASE 2 — INSTALL THE FIKAK CUSTOM APP

The `fikak_app/` folder in this package is a valid Frappe v15 app with your three
core DocTypes and the business rules you already verified (SAR 50K–5M range,
approve-before-disburse enforcement).

```bash
# 1. Copy the app into the running backend container
docker compose -f frappe_docker/pwd.yml cp ../fikak_app backend:/home/frappe/frappe-bench/apps/fikak_app

# 2. Install it
docker compose -f frappe_docker/pwd.yml exec backend bash -c "
  cd /home/frappe/frappe-bench &&
  ./env/bin/pip install -e apps/fikak_app &&
  echo fikak_app >> sites/apps.txt &&
  bench --site frontend install-app fikak_app &&
  bench --site frontend migrate"

# 3. Restart
docker compose -f frappe_docker/pwd.yml restart backend
```

Then in the UI search bar type "Financing Application" — your custom DocType is live.

### Phase 2 test scenarios
1. Create a Financial Product "Home Loan" (max 1,000,000 / 4.25% / 240 months)
2. Create a Financing Application for SAR 400,000 → saves as Draft
3. Try SAR 10,000 → **must be rejected** with the range error
4. Set status to Disbursed without approval → **must be rejected**
5. Approve first, then Disburse → approval_date and disbursement_date auto-set
6. Create a Payment Transaction → gateway_reference auto-generates (TXN-...)
7. Verify via REST (run `source .env.local` first if not already done):
   `curl -u Administrator:$ADMIN_PASSWORD http://localhost:8080/api/resource/Financing%20Application`

## OPERATIONS

```bash
docker compose -f frappe_docker/pwd.yml ps        # status
docker compose -f frappe_docker/pwd.yml logs -f backend
docker compose -f frappe_docker/pwd.yml down      # stop (data kept)
docker compose -f frappe_docker/pwd.yml down -v   # full reset
```

## KNOWN GAPS (from REPO_INVENTORY.md)
- Real fikak_app / fikak_api repos are private — request access to integrate them
- waseeraweb themes are empty on main branch — check other branches with the owner
- Payment gateway / KYC integrations: Frappe has integration framework ready; wire
  real credentials when the private code or provider accounts are available
