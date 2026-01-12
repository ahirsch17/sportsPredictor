# SportsPredictor

Produces matchup forecasts with confidence percentages for NFL games.

## Quick Start

**Recommended: Use `start.py`** - Works on Windows, macOS, and Linux!

### Easiest Method (All Platforms)
```bash
python3 start.py
```
or
```bash
./start.py
```

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
