.PHONY: install test lint format clean run-cli run-web docker-build docker-run

# Install dependencies
install:
	pip install -r requirements.txt

# Run tests
test:
	pytest tests/ -v --cov=src --cov-report=html

# Lint code
lint:
	flake8 src/ tests/
	mypy src/

# Format code
format:
	black src/ tests/
	isort src/ tests/

# Clean temporary files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

# Run CLI interface
run-cli:
	python -m src.application.cli_interface interactive

# Run web interface
run-web:
	python -m src.application.web_interface

# Docker commands
docker-build:
	docker-compose build

docker-run:
	docker-compose up -d

docker-logs:
	docker-compose logs -f

docker-stop:
	docker-compose down

# Development setup
dev-setup:
	pip install -r requirements.txt
	pre-commit install
	cp .env.example .env
	cp config/config.yaml.example config/config.yaml
	mkdir -p cache sessions logs

# Generate documentation
docs:
	pdoc --html --output-dir docs src
