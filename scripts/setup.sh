#!/bin/bash

echo "Setting up Report Portal LLM Query Interface..."

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p cache sessions logs config

# Copy example configurations
cp .env.example .env
cp config/config.yaml.example config/config.yaml

echo "Setup complete! Please edit .env and config/config.yaml with your settings."
echo "To start the CLI interface: python -m src.application.cli_interface interactive"
echo "To start the web interface: python -m src.application.web_interface"
