#!/bin/bash
# Fikak testing kit - macOS launcher
cd "$(dirname "$0")"
echo "Installing dependencies (if needed)..."
python3 -m pip install -q flask flask-cors flask-httpauth requests 2>/dev/null || pip install -q flask flask-cors flask-httpauth requests
echo "Stopping any old server..."
pkill -f fikak-complete-deployment 2>/dev/null; sleep 1
echo "Starting Fikak server..."
nohup python3 fikak-complete-deployment.py > fikak.log 2>&1 &
sleep 3
if curl -s -m 3 http://localhost:8000/api/health | grep -q healthy; then
  echo ""
  echo "✅ SERVER RUNNING at http://localhost:8000"
  echo "   Dashboard: open fikak-integrated-dashboard.html"
  echo "   API tester: open fikak-test-interface.html"
  echo "   Run tests: python3 fikak-e2e-journey-test.py"
else
  echo "❌ Server failed to start. Log output:"
  cat fikak.log
fi
