#!/bin/bash

# Install Fikak Custom App Script
# This script installs the fikak_app custom Frappe application

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_warning() { echo -e "${YELLOW}! $1${NC}"; }
print_info() { echo -e "${YELLOW}→ $1${NC}"; }

echo "========================================="
echo "  Fikak App - Install Custom App"
echo "========================================="
echo ""

# Check if backend is running
if ! docker ps | grep -q fikak_backend; then
    print_error "Frappe backend container is not running"
    print_info "Start services first with: docker compose -f docker-compose.unified.yml up -d"
    exit 1
fi

# Check if site exists
if ! docker exec fikak_backend bench list-sites | grep -q "localhost"; then
    print_error "Site 'localhost' does not exist"
    print_info "Create site first with: docker exec fikak_backend bench new-site localhost"
    exit 1
fi

print_success "Frappe backend is running and site exists"

# Ask user which method to use
echo ""
echo "Choose installation method:"
echo "  1) SSH (requires SSH key with GitHub access)"
echo "  2) Clone locally (you'll clone to workspace/fikak_api)"
echo ""
read -p "Enter choice [1-2]: " choice

case $choice in
    1)
        # SSH method
        print_info "Using SSH method..."

        # Check if SSH key exists
        if [ ! -f ~/.ssh/id_rsa ]; then
            print_error "SSH private key not found at ~/.ssh/id_rsa"
            print_info "Generate one with: ssh-keygen -t rsa -b 4096"
            exit 1
        fi

        print_info "Copying SSH keys to container..."
        docker cp ~/.ssh/id_rsa fikak_backend:/tmp/id_rsa
        docker cp ~/.ssh/id_rsa.pub fikak_backend:/tmp/id_rsa.pub 2>/dev/null || true

        print_info "Setting up SSH in container..."
        docker exec fikak_backend bash -c "
            mkdir -p ~/.ssh && \
            cp /tmp/id_rsa ~/.ssh/ && \
            chmod 600 ~/.ssh/id_rsa && \
            ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null
        "

        print_info "Getting fikak_app from GitHub..."
        if docker exec fikak_backend bench get-app fikak_app git@github.com:BablAdm/fikak_api.git; then
            print_success "Successfully cloned fikak_app"
        else
            print_error "Failed to clone fikak_app"
            print_info "Make sure your SSH key has access to the repository"
            docker exec fikak_backend bash -c "rm -f /tmp/id_rsa /tmp/id_rsa.pub ~/.ssh/id_rsa"
            exit 1
        fi

        # Do not leave the private key inside the container after cloning
        print_info "Removing copied SSH key from container..."
        docker exec fikak_backend bash -c "rm -f /tmp/id_rsa /tmp/id_rsa.pub ~/.ssh/id_rsa"
        print_success "SSH key removed from container"
        ;;

    2)
        # Local clone method
        print_info "Using local clone method..."

        # Clone locally if not exists
        if [ -d "workspace/fikak_api" ]; then
            print_warning "fikak_api already exists in workspace"
            read -p "Pull latest changes? [y/N]: " pull
            if [[ $pull =~ ^[Yy]$ ]]; then
                cd workspace/fikak_api && git pull && cd ../..
                print_success "Pulled latest changes"
            fi
        else
            print_info "Cloning fikak_api to workspace..."
            cd workspace
            if git clone git@github.com:BablAdm/fikak_api.git; then
                print_success "Cloned fikak_api"
                cd ..
            else
                print_error "Failed to clone repository"
                print_info "Make sure you have SSH access to git@github.com:BablAdm/fikak_api.git"
                exit 1
            fi
        fi

        print_info "Copying app to container..."
        docker cp workspace/fikak_api/. fikak_backend:/home/frappe/frappe-bench/apps/fikak_app/

        print_info "Installing Python dependencies..."
        docker exec fikak_backend bash -c "cd apps/fikak_app && pip install -e ."
        ;;

    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

# Install app on site
print_info "Installing fikak_app on site localhost..."
if docker exec fikak_backend bench --site localhost install-app fikak_app; then
    print_success "Installed fikak_app on site"
else
    print_error "Failed to install app"
    print_info "Check logs with: docker exec fikak_backend bench --site localhost console"
    exit 1
fi

# Migrate database
print_info "Running database migrations..."
if docker exec fikak_backend bench --site localhost migrate; then
    print_success "Migrations completed"
else
    print_warning "Migrations had warnings (this might be okay)"
fi

# Restart bench
print_info "Restarting Frappe bench..."
docker exec fikak_backend bench restart
print_success "Bench restarted"

# Verify installation
print_info "Verifying installation..."
echo ""
docker exec fikak_backend bench --site localhost list-apps
echo ""

if docker exec fikak_backend bench --site localhost list-apps | grep -q "fikak_app"; then
    print_success "fikak_app is installed!"
else
    print_error "fikak_app not found in installed apps"
    exit 1
fi

echo ""
echo "========================================="
echo "  Installation Complete!"
echo "========================================="
echo ""
print_success "fikak_app is now installed and ready to use"
echo ""
echo "The frontend (fikak-ui) should now be able to access all custom API endpoints."
echo ""
echo "Access the application at:"
echo "  • Frontend: http://localhost"
echo "  • Backend: http://localhost:8000"
echo ""
print_info "Refresh your browser to see the changes"
echo ""
