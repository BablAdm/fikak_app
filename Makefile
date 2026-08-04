SHELL := /bin/bash

.PHONY: help install dev test clean docker-up docker-down backend-test

help:
	@echo "Fikak App - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install all dependencies"
	@echo "  make dev              Start development servers"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up        Start all services with Docker Compose"
	@echo "  make docker-down      Stop all Docker services"
	@echo "  make docker-logs      View Docker logs"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests"
	@echo "  make backend-test     Run backend tests only"
	@echo "  make test-coverage    Run tests with coverage report"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate       Run database migrations"
	@echo "  make db-reset         Reset database (WARNING: deletes all data)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Clean build artifacts and cache"

install:
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Creating environment files..."
	cp -n .env.example .env || true
	cp -n backend/.env.example backend/.env || true
	@echo "Installation complete!"

dev:
	@echo "Starting development servers..."
	@echo "Backend will be available at http://localhost:8000"
	@echo "API docs at http://localhost:8000/docs"
	cd backend && uvicorn main:app --reload

docker-up:
	@echo "Starting Docker services..."
	docker-compose up -d
	@echo "Services started!"
	@echo "Backend API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"
	@echo "PostgreSQL: localhost:5432"
	@echo "MinIO Console: http://localhost:9001"

docker-down:
	@echo "Stopping Docker services..."
	docker-compose down

docker-logs:
	docker-compose logs -f

test:
	@echo "Running all tests..."
	cd backend && pytest

backend-test:
	@echo "Running backend tests..."
	cd backend && pytest -v

test-coverage:
	@echo "Running tests with coverage..."
	cd backend && pytest --cov=. --cov-report=html --cov-report=term
	@echo "Coverage report generated in backend/htmlcov/index.html"

db-migrate:
	@echo "Running database migrations..."
	cd backend && alembic upgrade head

db-reset:
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		docker-compose up -d postgres; \
		sleep 5; \
		echo "Database reset complete!"; \
	fi

clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "Clean complete!"
