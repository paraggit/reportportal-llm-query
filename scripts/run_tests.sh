#!/bin/bash

# Run all tests with coverage
pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# Run linting
echo "Running flake8..."
flake8 src/ tests/

echo "Running mypy..."
mypy src/

# Format check
echo "Checking code formatting..."
black --check src/ tests/