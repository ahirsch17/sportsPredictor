# SportsPredictor

Produces matchup forecasts with confidence percentages for NFL games.

## Quick Start

**Just run this one command:**

```bash
python3 start.py
```

That's it! The server will start, your browser will open automatically, and the server will keep running until you press `Ctrl+C`.

### Platform-Specific Options

**Windows:** Double-click `start.bat` in File Explorer

**macOS:** Double-click `start.command` in Finder

**Linux:** Run `./start.command` in terminal

### Manual Start (Alternative)
From command line:
```bash
cd sportsPredictor
python3 -m uvicorn api.server:app --reload --port 8001
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
