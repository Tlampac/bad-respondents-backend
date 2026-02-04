#!/bin/bash

echo "======================================"
echo "Bad Respondents Detector - Local Test"
echo "======================================"
echo ""

# Check Python version
echo "1. Checking Python version..."
python3 --version

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "2. Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo ""
echo "3. Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo ""
echo "4. Installing dependencies..."
pip install -r requirements.txt --quiet

# Check if static folder exists
if [ ! -d "static" ]; then
    echo ""
    echo "ERROR: static folder not found!"
    exit 1
fi

# Run the app
echo ""
echo "5. Starting Flask application..."
echo ""
echo "======================================"
echo "App running at: http://localhost:5000"
echo "Press Ctrl+C to stop"
echo "======================================"
echo ""

python app.py
