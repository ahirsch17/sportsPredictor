#!/bin/bash
# SportsPredictor Startup Script for macOS
# Double-click this file in Finder to start the server

cd "$(dirname "$0")"

echo "Starting SportsPredictor server..."
echo ""

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 is not installed or not in PATH"
    echo "Please install Python 3 from https://www.python.org/downloads/"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

# Check if dependencies are installed
if ! python3 -c "import fastapi, uvicorn" 2>/dev/null; then
    echo "Installing required dependencies..."
    echo ""
    python3 -m pip install -q -r requirements.txt
    echo ""
fi

# Start the server in the background
python3 start.py

echo ""
echo "Server should be starting. Check your browser!"
echo ""
read -p "Press Enter to close this window..."
