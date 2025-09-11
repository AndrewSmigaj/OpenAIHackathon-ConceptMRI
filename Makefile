# Concept MRI - Development Makefile

.PHONY: help setup test run-api run-ui dev fmt typecheck clean data-sample

help:
	@echo "Available commands:"
	@echo "  setup        - Set up development environment"
	@echo "  dev          - Run both backend and frontend (requires 2 terminals)"
	@echo "  run-api      - Start FastAPI backend"
	@echo "  run-ui       - Start React frontend"
	@echo "  test         - Run tests"
	@echo "  fmt          - Format code with black"
	@echo "  typecheck    - Run mypy type checking"
	@echo "  lint         - Run ruff linting"
	@echo "  clean        - Clean cache and temp files"
	@echo "  data-sample  - Create sample data for testing"

setup:
	@echo "Setting up Python environment..."
	pip install -r backend/requirements.txt
	@echo "Setting up Frontend environment..."
	cd frontend && npm install
	@echo "Creating data directories..."
	mkdir -p data/lake data/experiments data/models
	@echo "Downloading NLTK data..."
	python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"
	@echo "Setup complete! Don't forget to add your API keys to .env file"

dev:
	@echo "Starting both backend and frontend..."
	@echo "Please run these commands in separate terminals:"
	@echo "  Terminal 1: make run-api"
	@echo "  Terminal 2: make run-ui"

test:
	@echo "Running tests..."
	cd backend && pytest tests/ -v

run-api:
	@echo "Starting FastAPI backend..."
	cd backend/src && python3 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

run-ui:
	@echo "Starting React frontend..."
	cd frontend && npm run dev

fmt:
	@echo "Formatting Python code..."
	black backend/src --line-length 100
	ruff backend/src --fix

typecheck:
	@echo "Running type checks..."
	mypy backend/src --strict

lint:
	@echo "Running linter..."
	ruff backend/src

clean:
	@echo "Cleaning cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete!"

data-sample:
	@echo "Creating sample data..."
	@echo "Sample data generation not yet implemented"