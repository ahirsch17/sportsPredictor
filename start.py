#!/usr/bin/env python3
"""
SportsPredictor Startup Script
Simple script that starts the server and keeps it running.
"""

import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path

def main():
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    print("=" * 50)
    print("Starting SportsPredictor Server")
    print("=" * 50)
    print()
    
    # Check if dependencies are installed
    try:
        import fastapi
        import uvicorn
        import numpy
        import pandas
        import sklearn
        import xgboost
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Installing required dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"], check=True)
        print("Dependencies installed!")
        print()
    
    # Start the server
    print("Starting server on http://127.0.0.1:8001")
    print("Press Ctrl+C to stop the server")
    print()
    
    # Open browser after a short delay
    def open_browser():
        time.sleep(3)  # Give server time to start
        print("Opening browser...")
        webbrowser.open("http://127.0.0.1:8001")
    
    # Start browser opener in background
    import threading
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Run the server in the foreground - this keeps it alive
    try:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "api.server:app", "--reload", "--port", "8001"],
            cwd=script_dir
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
