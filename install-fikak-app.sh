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
if ! docker exec fikak_backend test -d sites/localhost; then
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

        # Guarantee the private key is removed from the container on every
        # exit path from here on - success, failure, or interruption.
        # apt-get, the SSH setup, or the clone itself can all fail partway
        # through, and without this, `set -e` would terminate the script
        # before any of the cleanup below ever ran.
        cleanup_ssh_key() {
            docker exec -u root fikak_backend bash -c \
                "rm -f /tmp/id_rsa /tmp/id_rsa.pub /tmp/known_hosts /home/frappe/.ssh/id_rsa" \
                2>/dev/null || true
        }
        trap cleanup_ssh_key EXIT

        # The frappe/erpnext image doesn't ship an SSH client at all
        # (no ssh, no ssh-keyscan) - only git itself, which shells out to
        # a system ssh binary for the git@host: transport. Install it.
        print_info "Installing SSH client in container (not included in the base image)..."
        docker exec -u root fikak_backend bash -c "apt-get update -qq && apt-get install -y --no-install-recommends openssh-client -qq" > /dev/null

        # `docker cp` preserves the file's numeric host UID/GID, which the
        # container's default non-root user (frappe) usually can't read.
        # /tmp also has the sticky bit set, so that user couldn't even
        # remove a file it doesn't own during cleanup. Do the file handling
        # as root, but place the key in the *frappe* user's home (not
        # root's, which `~` would resolve to under -u root) so `bench
        # get-app` - which must run as the normal user for correct file
        # ownership on the cloned app - can still find it afterward.
        print_info "Setting up SSH in container..."
        docker exec -u root fikak_backend bash -c "
            mkdir -p /home/frappe/.ssh && \
            cp /tmp/id_rsa /home/frappe/.ssh/id_rsa && \
            chown frappe:frappe /home/frappe/.ssh /home/frappe/.ssh/id_rsa && \
            chmod 700 /home/frappe/.ssh && \
            chmod 600 /home/frappe/.ssh/id_rsa
        "

        # Pin GitHub's published host keys instead of trusting whatever a
        # first SSH connection returns: TOFU (StrictHostKeyChecking=accept-new)
        # would let a network attacker present a forged host key on that
        # first connection, and the following `bench install-app` would then
        # execute whatever it served as "fikak_app". These lines were fetched
        # from GitHub's own docs and independently verified: each key's
        # computed SHA256 fingerprint matches the fingerprint GitHub
        # separately documents at
        # https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints
        cat > /tmp/github_known_hosts <<'GHKEYS'
github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl
github.com ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBEmKSENjQEezOmxkZMy7opKgwFB9nkt5YRrYMjNuG5N87uRgg6CLrbo5wAdT/y6v0mKV0U2w0WZ2YB/++Tpockg=
github.com ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCj7ndNxQowgcQnjshcLrqPEiiphnt+VTTvDP6mHBL9j1aNUkY4Ue1gvwnGLVlOhGeYrnZaMgRK6+PKCUXaDbC7qtbW8gIkhL7aGCsOr/C56SJMy/BCZfxd1nWzAOxSDPgVsmerOBYfNqltV9/hWCqBywINIR+5dIg6JTJ72pcEpEjcYgXkE2YEFXV1JHnsKgbLWNlhScqb2UmyRkQyytRLtL+38TGxkxCflmO+5Z8CSSNY7GidjMIZ7Q4zMjA2n1nGrlTDkzwDCsw+wqFPGQA179cnfGWOWRVruj16z6XyvxvjJwbz0wQZ75XK5tKSb7FNyeIEs4TT4jk+S4dhPeAUC5y+bDYirYgM4GC7uEnztnZyaVWQ7B381AK4Qdrwt51ZqExKbQpTUNn+EjqoTwvqNj4kqx5QUCI0ThS/YkOxJCXmPUWZbhjpCg56i+2aB6CmK2JGhn57K5mj0MNdBXA4/WnwH6XoPWJzK5Nyu2zB3nAZp+S5hpQs+p1vN1/wsjk=
GHKEYS
        docker cp /tmp/github_known_hosts fikak_backend:/tmp/known_hosts
        rm -f /tmp/github_known_hosts
        docker exec -u root fikak_backend chmod 644 /tmp/known_hosts

        print_info "Getting fikak_app from GitHub..."
        if docker exec -e GIT_SSH_COMMAND="ssh -o UserKnownHostsFile=/tmp/known_hosts -o StrictHostKeyChecking=yes" \
            fikak_backend bench get-app fikak_app git@github.com:BablAdm/fikak_api.git; then
            print_success "Successfully cloned fikak_app"
        else
            print_error "Failed to clone fikak_app"
            print_info "Make sure your SSH key has access to the repository"
            exit 1
        fi
        # The `trap` above removes the private key (and known_hosts pin)
        # from the container now, and will do so again harmlessly at
        # normal script exit.
        print_success "SSH key will be removed from container on exit"
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
