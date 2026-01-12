#!/bin/bash
# SportsPredictor Startup Script for macOS
# Double-click this file in Finder to start the server

cd "$(dirname "$0")"

# Open in Terminal so you can see the server output and stop it with Ctrl+C
osascript -e 'tell application "Terminal" to activate' -e 'tell application "Terminal" to do script "cd \"'"$(pwd)"'\" && python3 start.py"'
