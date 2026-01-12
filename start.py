#!/usr/bin/env python3
"""
SportsPredictor Startup Script
This script starts the FastAPI server and opens the web interface automatically.
"""

import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path

def check_server_ready(url: str, max_attempts: int = 15) -> bool:
    """Check if the server is ready by pinging the health endpoint."""
    import urllib.request
    import urllib.error
    
    for attempt in range(max_attempts):
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=1) as response:
                if response.getcode() == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(1)
    return False

def main():
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    
    # Change to the sportsPredictor directory
    os.chdir(script_dir)
    
    print("Starting SportsPredictor server...")
    print()
    
    # Start the server in a separate process
    # Use subprocess.Popen to run in background on Unix/Mac, or start in new window on Windows
    if sys.platform == "win32":
        # On Windows, start in a new window
        subprocess.Popen(
            [
                "python", "-m", "uvicorn", "api.server:app",
                "--reload", "--port", "8001"
            ],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    else:
        # On macOS/Linux, open a new terminal window to run the server
        # This keeps the server running even after this script exits
        if sys.platform == "darwin":  # macOS
            # Escape the path properly for AppleScript
            escaped_path = str(script_dir).replace('"', '\\"')
            escaped_python = str(sys.executable).replace('"', '\\"')
            apple_script = f'tell application "Terminal" to do script "cd \\"{escaped_path}\\" && \\"{escaped_python}\\" -m uvicorn api.server:app --reload --port 8001"'
            subprocess.Popen(
                ["osascript", "-e", apple_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:  # Linux
            # For Linux, use xterm or gnome-terminal if available
            subprocess.Popen(
                [
                    "xterm", "-e",
                    f"cd {script_dir} && {sys.executable} -m uvicorn api.server:app --reload --port 8001"
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
    
    # Wait for server to be ready
    print("Waiting for server to be ready...")
    server_url = "http://127.0.0.1:8001"
    
    # Give the server more time to start (especially if opening a new terminal)
    time.sleep(2)
    
    if check_server_ready(server_url):
        print("Server is ready!")
    else:
        print("Warning: Server may not be fully ready yet, but opening browser anyway...")
        print("If the page doesn't load, wait a few seconds and refresh.")
    
    print()
    
    # Open the web interface via HTTP (not file://) to avoid CORS issues
    print(f"Opening web interface at {server_url}...")
    print()
    webbrowser.open(server_url)
    
    print(f"Server is running on {server_url}")
    print("Web interface should open in your browser shortly.")
    print()
    
    if sys.platform == "win32":
        print("To stop the server, close the 'SportsPredictor Server' window.")
    elif sys.platform == "darwin":
        print("Server is running in a new Terminal window.")
        print("To stop it, close that Terminal window or press Ctrl+C in that window.")
    else:
        print("Server is running in a new terminal window.")
        print("To stop it, close that window or press Ctrl+C.")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)

