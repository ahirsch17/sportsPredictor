# SportsPredictor

Produces matchup forecasts with confidence percentages for NFL games.

## Quick Start

### Windows
Double-click `start.bat` in File Explorer to start the server and open the web interface.

### macOS/Linux
Double-click `start.command` in Finder (macOS) or run `./start.command` in terminal to start the server and open the web interface.

### Manual Start
From command line:
```bash
cd sportsPredictor
python -m uvicorn api.server:app --reload --port 8001
```
Then open `http://127.0.0.1:8001` in your browser.

## Requirements

- Python 3.7 or higher
- Dependencies will be installed automatically when you run the startup scripts

## Installation

If you need to install dependencies manually:
```bash
pip install -r requirements.txt
```
