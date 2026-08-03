#!/bin/bash
# FIKAK FRAPPE STACK - macOS setup (Phase 1: real Frappe/ERPNext v15)
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/frappe_docker"

if ! command -v docker >/dev/null 2>&1; then
  echo "❌ Docker not found. Install Docker Desktop for Mac first:"
  echo "   https://www.docker.com/products/docker-desktop/"
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "❌ Docker Desktop is installed but not running. Open it, wait for the whale icon, retry."
  exit 1
fi

# Load persisted credentials from a prior run so volumes and passwords stay in sync
ENV_FILE="$SCRIPT_DIR/.env.local"
if [ -f "$ENV_FILE" ]; then
  # shellcheck source=/dev/null
  . "$ENV_FILE"
fi

# Generate random passwords for local dev if not already set via environment
: "${DB_PASSWORD:=$(openssl rand -hex 12)}"
: "${ADMIN_PASSWORD:=$(openssl rand -hex 12)}"
export DB_PASSWORD ADMIN_PASSWORD

# Write back so subsequent runs (after docker compose down) reuse the same passwords
printf 'DB_PASSWORD=%q\nADMIN_PASSWORD=%q\n' "$DB_PASSWORD" "$ADMIN_PASSWORD" > "$ENV_FILE"
chmod 600 "$ENV_FILE"

echo "🔐 Credentials saved to .env.local (keep it secure):"
echo "   DB root password:  ***REDACTED*** (check .env.local)"
echo "   Frappe admin pass: ***REDACTED*** (check .env.local)"
echo ""

echo "🚀 Starting Frappe/ERPNext v15 stack (this pulls ~2GB of images on first run)..."
docker compose -f pwd.yml up -d

echo ""
echo "⏳ Site creation runs inside the 'create-site' container (takes 3-6 min first time)."
echo "   Watching progress — wait for 'Done' or press Ctrl+C to stop watching (stack keeps running):"
docker logs -f $(docker compose -f pwd.yml ps -q create-site) 2>/dev/null || true

echo ""
echo "══════════════════════════════════════════════════════"
echo "✅ FIKAK FRAPPE STACK READY"
echo "   URL:      http://localhost:8080"
echo "   Login:    Administrator"
echo "   Password: ***REDACTED*** (stored in .env.local)"
echo "══════════════════════════════════════════════════════"
echo "Stop:    docker compose -f pwd.yml down"
echo "Destroy: docker compose -f pwd.yml down -v   (deletes all data)"
