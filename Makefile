.PHONY: all setup build run start clean test help docker-build docker-run

# Default target
all: docker-build

# Help target
help:
	@echo "Dropbox to Google Drive Migration Tool"
	@echo ""
	@echo "Available targets:"
	@echo "  make setup       - Install dependencies and set up the environment"
	@echo "  make build       - Build the Docker container"
	@echo "  make run         - Run the migration tool locally"
	@echo "  make start       - Setup, build and run in one command (Docker)"
	@echo "  make docker-run  - Run the migration tool in Docker"
	@echo "  make test        - Run tests"
	@echo "  make clean       - Clean build artifacts"
	@echo "  make help        - Show this help message"

# Setup dependencies
setup:
	@echo "Setting up environment..."
	@echo "Checking for Docker..."
	@docker --version || (echo "Docker not found. Please install Docker." && exit 1)
	@echo "Creating directory structure..."
	@mkdir -p src/core src/dropbox_integration src/google_drive_integration src/auth tests
	@touch src/__init__.py src/core/__init__.py src/dropbox_integration/__init__.py
	@touch src/google_drive_integration/__init__.py src/auth/__init__.py tests/__init__.py
	@echo "Creating requirements.txt..."
	@echo "Environment setup complete."

# Build Docker container
build: setup
	@echo "Building Docker container..."
	docker compose build
	@echo "Build complete."

# Run the migration tool locally
run:
	@echo "Starting migration (local)..."
	@echo "Checking environment variables..."
	@test -n "$(GOOGLE_CLIENT_ID)" || (echo "Error: GOOGLE_CLIENT_ID not set" && exit 1)
	@test -n "$(GOOGLE_CLIENT_SECRET)" || (echo "Error: GOOGLE_CLIENT_SECRET not set" && exit 1)
	@test -n "$(DROPBOX_APP_KEY)" || (echo "Error: DROPBOX_APP_KEY not set" && exit 1)
	@test -n "$(DROPBOX_APP_SECRET)" || (echo "Error: DROPBOX_APP_SECRET not set" && exit 1)
	python src/main.py

# Run in Docker
docker-run:
	@echo "Starting migration (Docker)..."
	@echo "Checking environment variables..."
	@test -n "$(GOOGLE_CLIENT_ID)" || (echo "Error: GOOGLE_CLIENT_ID not set" && exit 1)
	@test -n "$(GOOGLE_CLIENT_SECRET)" || (echo "Error: GOOGLE_CLIENT_SECRET not set" && exit 1)
	@test -n "$(DROPBOX_APP_KEY)" || (echo "Error: DROPBOX_APP_KEY not set" && exit 1)
	@test -n "$(DROPBOX_APP_SECRET)" || (echo "Error: DROPBOX_APP_SECRET not set" && exit 1)
	docker compose run --rm migration

# One-command execution
start: setup build docker-run
	@echo "Migration complete!"

# Run tests
test:
	python -m pytest tests/

# Clean build artifacts
clean:
	docker compose down
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Clean complete."