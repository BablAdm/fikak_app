#!/bin/bash
# FIKAK FRAPPE STACK - macOS setup (Phase 1: real Frappe/ERPNext v15)
set -e
cd "$(dirname "$0")/frappe_docker"

if ! command -v docker >/dev/null 2>&1; then
  echo "❌ Docker not found. Install Docker Desktop for Mac first:"
  echo "   https://www.docker.com/products/docker-desktop/"
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "❌ Docker Desktop is installed but not running. Open it, wait for the whale icon, retry."
  exit 1
fi

# Generate random passwords for local dev if not already set via environment
: "${DB_PASSWORD:=$(openssl rand -hex 12)}"
: "${ADMIN_PASSWORD:=$(openssl rand -hex 12)}"
export DB_PASSWORD ADMIN_PASSWORD

echo "🔐 Using credentials (save these):"
echo "   DB root password:  $DB_PASSWORD"
echo "   Frappe admin pass: $ADMIN_PASSWORD"
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
echo "   Password: $ADMIN_PASSWORD"
echo "══════════════════════════════════════════════════════"
echo "Stop:    docker compose -f pwd.yml down"
echo "Destroy: docker compose -f pwd.yml down -v   (deletes all data)"
