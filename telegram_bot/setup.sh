#!/bin/bash
# Script for initializing and running the Telegram Bot

echo "=========================================="
echo "Telegram Bot - Setup and Initialization"
echo "=========================================="

# Check Python version
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file and add your BOT_TOKEN"
    echo "Then run: python main.py"
else
    echo ".env file already exists"
fi

echo "=========================================="
echo "Setup complete!"
echo "Run: python main.py"
echo "=========================================="
