#!/bin/bash
# FIKAK BACKEND REPAIR + E2E — safe to re-run any time
cd "$(dirname "$0")/frappe_docker"
C="docker compose -f pwd.yml"

echo "== 1. Current backend state =="
$C ps backend
echo "-- last log lines --"
$C logs --tail 12 backend 2>/dev/null | tail -12

echo ""
echo "== 2. Restore service baseline =="
if ! curl -s -m 5 http://localhost:8080/api/method/ping | grep -q pong; then
  echo "Backend not serving — rolling back apps.txt via throwaway container..."
  $C run --rm --no-deps backend bash -c "sed -i '/^fikak_app$/d' /home/frappe/frappe-bench/sites/apps.txt; cat /home/frappe/frappe-bench/sites/apps.txt" 
  $C up -d backend
  sleep 8
fi
if curl -s -m 5 http://localhost:8080/api/method/ping | grep -q pong; then
  echo "✅ Baseline healthy — backend serving"
else
  echo "❌ Backend still down even without fikak_app. Full logs:"
  $C logs --tail 40 backend
  exit 1
fi

echo ""
echo "== 3. Clean install of fikak_app into running backend =="
$C exec -T backend rm -rf /home/frappe/frappe-bench/apps/fikak_app
$C cp ../fikak_app backend:/home/frappe/frappe-bench/apps/fikak_app
$C exec -T backend bash -c "find /home/frappe/frappe-bench/apps/fikak_app -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; true"
$C exec -T backend bash -c "cd /home/frappe/frappe-bench && ./env/bin/pip install -q -e apps/fikak_app"
if ! $C exec -T backend bash -c "cd /home/frappe/frappe-bench && ./env/bin/python -c 'import fikak_app; print(\"import OK\", fikak_app.__version__)'"; then
  echo "❌ Python import failed — NOT touching apps.txt (site stays healthy). Paste this output to Claude."
  exit 1
fi

echo ""
echo "== 4. Register + install + migrate =="
$C exec -T backend bash -c "cd /home/frappe/frappe-bench && grep -qx fikak_app sites/apps.txt || echo fikak_app >> sites/apps.txt"
$C exec -T backend bash -c "cd /home/frappe/frappe-bench && bench --site frontend install-app fikak_app || true"
$C exec -T backend bash -c "cd /home/frappe/frappe-bench && bench --site frontend migrate"

echo ""
echo "== 5. Restart + health gate =="
$C restart backend
sleep 8
if curl -s -m 5 http://localhost:8080/api/method/ping | grep -q pong; then
  echo "✅ Backend healthy WITH fikak_app installed"
else
  echo "❌ Backend failed after install — auto-rollback:"
  $C run --rm --no-deps backend bash -c "sed -i '/^fikak_app$/d' /home/frappe/frappe-bench/sites/apps.txt"
  $C up -d backend; sleep 8
  curl -s -m 5 http://localhost:8080/api/method/ping && echo "  vanilla site restored — paste full output to Claude"
  exit 1
fi

echo ""
echo "== 6. Running E2E suite inside Frappe =="
$C cp ../e2e.py backend:/home/frappe/frappe-bench/apps/fikak_app/fikak_app/e2e.py
$C exec -T backend bench --site frontend execute fikak_app.e2e.run

echo ""
echo "══════════════════════════════════════════════"
echo "Done. If you see RESULTS: 9/9 above — the real"
echo "Fikak platform on Frappe is E2E-verified."
echo "══════════════════════════════════════════════"
