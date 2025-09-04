# Concept MRI - Development Makefile

.PHONY: help setup test run-api run-ui fmt typecheck clean data-sample

help:
	@echo "Available commands:"
	@echo "  setup        - Set up development environment"
	@echo "  test         - Run tests"
	@echo "  run-api      - Start FastAPI backend"
	@echo "  run-ui       - Start React frontend"
	@echo "  fmt          - Format code with black"
	@echo "  typecheck    - Run mypy type checking"
	@echo "  lint         - Run ruff linting"
	@echo "  clean        - Clean cache and temp files"
	@echo "  data-sample  - Create sample data for testing"

setup:
	@echo "Setting up Python environment..."
	pip install -r backend/requirements.txt
	@echo "Creating data directories..."
	mkdir -p data/lake data/experiments data/models
	@echo "Setup complete!"

test:
	@echo "Running tests..."
	cd backend && pytest tests/ -v

run-api:
	@echo "Starting FastAPI backend..."
	cd backend && uvicorn src.api.main:app --reload --port 8000

run-ui:
	@echo "Starting React frontend..."
	@echo "Frontend not yet implemented"
	# cd frontend && npm run dev

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