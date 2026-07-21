#!/bin/bash

# Fikak App - Automated Setup Script
# This script sets up the complete Fikak App environment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}! $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

# Banner
echo "========================================="
echo "  Fikak App - Complete Setup"
echo "========================================="
echo ""

# Step 1: Check prerequisites
print_info "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi
print_success "Docker is installed"

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi
print_success "Docker Compose is installed"

# Step 2: Setup environment files
print_info "Setting up environment files..."

if [ ! -f workspace/fikak-ui/.env.local ]; then
    cp workspace/fikak-ui/.env.example workspace/fikak-ui/.env.local
    print_success "Created .env.local for fikak-ui"
else
    print_warning ".env.local already exists for fikak-ui"
fi

# Step 3: Check Docker resources
print_info "Checking Docker resources..."
DOCKER_MEM=$(docker info --format '{{.MemTotal}}')
if [ -n "$DOCKER_MEM" ]; then
    MEM_GB=$((DOCKER_MEM / 1024 / 1024 / 1024))
    if [ $MEM_GB -lt 6 ]; then
        print_warning "Docker has less than 6GB memory allocated ($MEM_GB GB). 8GB+ recommended for Frappe."
        print_warning "Consider increasing Docker memory in settings."
    else
        print_success "Docker memory: $MEM_GB GB"
    fi
fi

# Step 4: Pull images
print_info "Pulling Docker images (this may take a while)..."
docker-compose -f docker-compose.unified.yml pull || print_warning "Some images couldn't be pulled, will build instead"

# Step 5: Build custom images
print_info "Building frontend image..."
docker-compose -f docker-compose.unified.yml build fikak_ui

# Step 6: Start services
print_info "Starting all services..."
docker-compose -f docker-compose.unified.yml up -d

# Step 7: Wait for services to be healthy
print_info "Waiting for services to become healthy (this may take 2-3 minutes)..."
sleep 10

# Check MariaDB health
print_info "Checking MariaDB..."
for i in {1..30}; do
    if docker exec fikak_mariadb mysqladmin ping -h localhost -padmin123 --silent 2>/dev/null; then
        print_success "MariaDB is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "MariaDB failed to start"
        exit 1
    fi
    sleep 2
done

# Check Redis
print_info "Checking Redis..."
if docker exec fikak_redis_cache redis-cli ping | grep -q "PONG"; then
    print_success "Redis is ready"
else
    print_warning "Redis might not be fully ready"
fi

# Check Frappe backend
print_info "Checking Frappe backend..."
for i in {1..60}; do
    if curl -s http://localhost:8000 > /dev/null 2>&1; then
        print_success "Frappe backend is ready"
        break
    fi
    if [ $i -eq 60 ]; then
        print_error "Frappe backend failed to start"
        print_info "Check logs with: docker-compose -f docker-compose.unified.yml logs fikak_backend"
        exit 1
    fi
    sleep 3
done

# Step 8: Create Frappe site
print_info "Creating Frappe site..."
if docker exec fikak_backend bench list-sites | grep -q "localhost"; then
    print_warning "Site 'localhost' already exists, skipping creation"
else
    docker exec fikak_backend bench new-site localhost \
        --mariadb-root-password admin123 \
        --admin-password admin \
        --no-mariadb-socket 2>&1 | grep -v "WARN"

    if [ $? -eq 0 ]; then
        print_success "Created Frappe site: localhost"
    else
        print_error "Failed to create site"
        exit 1
    fi
fi

# Set site as current
docker exec fikak_backend bench use localhost
print_success "Set localhost as current site"

# Enable developer mode
docker exec fikak_backend bench --site localhost set-config developer_mode 1
print_success "Enabled developer mode"

# Step 9: Check frontend
print_info "Checking frontend..."
sleep 5
for i in {1..20}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        print_success "Frontend is ready"
        break
    fi
    if [ $i -eq 20 ]; then
        print_warning "Frontend might not be ready yet"
        print_info "Check logs with: docker-compose -f docker-compose.unified.yml logs fikak_ui"
    fi
    sleep 2
done

# Step 10: Show status
echo ""
echo "========================================="
echo "  Setup Complete!"
echo "========================================="
echo ""
print_success "All services are running"
echo ""
echo "Access Points:"
echo "  • Frontend (via Nginx):  http://localhost"
echo "  • Frontend (direct):     http://localhost:3000"
echo "  • Backend API:           http://localhost:8000"
echo "  • Frappe Desk:           http://localhost:8000/app"
echo ""
echo "Default Credentials:"
echo "  • Username: Administrator"
echo "  • Password: admin"
echo ""
echo "Useful Commands:"
echo "  • View logs:      docker-compose -f docker-compose.unified.yml logs -f"
echo "  • Stop services:  docker-compose -f docker-compose.unified.yml down"
echo "  • Check status:   docker-compose -f docker-compose.unified.yml ps"
echo ""
echo "For detailed testing instructions, see: COMPLETE_SETUP.md"
echo ""
print_info "Opening browser..."
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost &
elif command -v open &> /dev/null; then
    open http://localhost &
fi

print_success "Setup completed successfully!"
