# Fikak — Waseera Asset Monetization & Financing Platform

A [Frappe](https://frappeframework.com/) v15 custom app providing the backend for Fikak, Waseera's asset monetization and financing platform.

## Stack

| Layer | Technology |
|---|---|
| Framework | Frappe v15 + ERPNext v15 |
| Database | MariaDB (via Frappe) |
| Runtime | Python 3.10+ |
| Deployment | Docker (frappe_docker) |
| MCP | MongoDB MCP server (read-only analytics) |

## Modules

| Module | DocTypes |
|---|---|
| **Fikak** | Financial Product, Financing Application, Payment Transaction |
| **KYC Management** | KYC, KYC Question, KYC Submission, + child tables |
| **Terms Management** | Terms And Conditions, Terms Acceptance |

## API Endpoints

All endpoints are at `/api/method/fikak_app.<module>.<function>`.

| Endpoint | Auth | Description |
|---|---|---|
| `fikak_app.api.custom_login` | Guest | JWT login |
| `fikak_app.api.get_user_info` | Token | Current user info + terms status |
| `fikak_app.api.get_country_list` | Guest | Country list |
| `fikak_app.fikak_api.kyc_api.get_kyc_questions` | Token | Active KYC question set |
| `fikak_app.fikak_api.kyc_api.get_kyc_answers` | Token | User's KYC state |
| `fikak_app.fikak_api.kyc_api.submit_kyc_answers` | Token | Submit KYC form |
| `fikak_app.fikak_api.conditions_api.get_terms_and_conditions` | Token | Active T&C |
| `fikak_app.fikak_api.conditions_api.submit_conditions` | Token | Accept T&C |

## Quick Start (Docker)

```bash
# 1. Start Frappe/ERPNext v15 (pulls ~2GB on first run, takes 5-10 min)
bash setup-fikak-mac.sh

# 2. Install fikak_app into the running stack
bash fix-and-test.sh
```

Access: http://localhost:8080 · Login: `Administrator` / *(password shown in setup script output)*

## Standalone API Testing (no Docker)

```bash
pip install flask flask-cors flask-httpauth requests
python3 testing/fikak-complete-deployment.py
```

Open `testing/fikak-test-interface.html` in a browser.
See `testing/CUSTOMER_JOURNEY_PLAYBOOK.md` for the full test script.

## Environment Variables

| Variable | Where set | Description |
|---|---|---|
| `MDB_MCP_CONNECTION_STRING` | Shell env | MongoDB URI for Claude Code MCP |
| `fikak_jwt_secret` | `site_config.json` | JWT signing secret |
| `STRIPE_API_KEY` | `site_config.json` or env | Stripe secret key |

## Business Rules

- Financing amounts: SAR 50,000 – 5,000,000
- Applications must be **Approved** before they can be **Disbursed**
- `approval_date` and `disbursement_date` are set automatically on status change
- Payment Transaction `gateway_reference` is auto-generated (`TXN-XXXXXXXX`)
- KYC risk scoring: weighted average of answer weights → No Risk / Medium Risk / High Risk
