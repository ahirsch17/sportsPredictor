from __future__ import annotations

import asyncio
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure NFL modules are importable
BASE_DIR = Path(__file__).resolve().parent.parent
NFL_DIR = BASE_DIR / "NFL"
if str(NFL_DIR) not in sys.path:
    sys.path.insert(0, str(NFL_DIR))

# Imports that rely on NFL_DIR being on sys.path
from batch_predict import batch_predict_week  # type: ignore
from injuryextract import (  # type: ignore
    calculate_injury_impact,
    get_injury_data,
    write_injury_report,
)
from predictor import advanced_prediction, read_nfl_data  # type: ignore
from dataextract import update_mode  # type: ignore


app = FastAPI(
    title="SportsPredictor NFL API",
    description="Local API bridge so the SportsPredictor front-end can trigger Python analytics routines.",
    version="0.1.0",
)

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


cwd_lock = threading.Lock()


def run_in_nfl_context(fn, *args, **kwargs):
    """Execute a callable while temporarily switching to the NFL directory."""
    with cwd_lock:
        previous_cwd = Path.cwd()
        try:
            os.chdir(NFL_DIR)
            return fn(*args, **kwargs)
        finally:
            os.chdir(previous_cwd)


async def run_blocking(fn, *args, **kwargs):
    """Run a blocking task tied to NFL data inside a thread."""
    return await asyncio.to_thread(run_in_nfl_context, fn, *args, **kwargs)


class MatchupRequest(BaseModel):
    home_team: str
    away_team: str
    neutral_site: bool = False
    use_ml: bool = False


class BatchRequest(BaseModel):
    week: int
    season_type: str = "regular"
    use_ml: bool = True


class RefreshResponse(BaseModel):
    status: str
    updated_at: datetime
    details: Dict[str, Any]


def format_matchup_response(result: Dict[str, Any], injury_data: Optional[Dict[str, Any]], home_team: str, away_team: str) -> Dict[str, Any]:
    home_injury = calculate_injury_impact(home_team, injury_data) if injury_data else None
    away_injury = calculate_injury_impact(away_team, injury_data) if injury_data else None

    return {
        "prediction": result,
        "injuries": {
            "home_team": home_injury,
            "away_team": away_injury,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"}


@app.get("/api/teams")
async def get_teams():
    def _load():
        teams = read_nfl_data()
        if not teams:
            return []
        return sorted(teams.keys())

    teams = await run_blocking(_load)
    if not teams:
        raise HTTPException(status_code=500, detail="NFL dataset not available. Run dataextract.py first.")
    return {"teams": teams}


@app.post("/api/matchup")
async def predict_matchup(request: MatchupRequest):
    def _predict():
        teams = read_nfl_data()
        if not teams:
            raise ValueError("NFL data is unavailable. Run dataextract.py first.")

        missing = [team for team in (request.home_team, request.away_team) if team not in teams]
        if missing:
            raise ValueError(f"Unknown teams: {', '.join(missing)}. Refresh dataextract output.")

        injury_data = get_injury_data()

        prediction = advanced_prediction(
            request.home_team,
            request.away_team,
            teams,
            request.neutral_site,
            injury_data,
        )

        if not prediction:
            raise ValueError("Prediction failed. Check logs for details.")

        return format_matchup_response(prediction, injury_data, request.home_team, request.away_team)

    try:
        payload = await run_blocking(_predict)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"Matchup prediction failed: {exc}") from exc

    return payload


@app.post("/api/batch")
async def run_batch_prediction(request: BatchRequest):
    def _batch():
        result = batch_predict_week(request.week, request.season_type, use_ml=request.use_ml)
        return result or {
            "predictions": [],
            "failed_games": [],
            "summary": {
                "week": request.week,
                "season_type": request.season_type,
                "total_games": 0,
                "predicted_games": 0,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

    try:
        payload = await run_blocking(_batch)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {exc}") from exc
    return payload


@app.post("/api/refresh/injuries")
async def refresh_injuries():
    def _refresh():
        injury_data = get_injury_data()
        if injury_data is None:
            raise ValueError("Injury API returned no data.")
        write_injury_report(injury_data)
        total_injuries = sum(len(players) for players in injury_data.values())
        busiest = sorted(
            (
                (team, len(players), calculate_injury_impact(team, injury_data))
                for team, players in injury_data.items()
            ),
            key=lambda item: item[1],
            reverse=True,
        )[:5]
        return {
            "teams_with_data": len(injury_data),
            "total_injuries": total_injuries,
            "top_impacted": [
                {
                    "team": team,
                    "injury_count": count,
                    "impact_score": round(impact.get("impact_score", 0), 2) if isinstance(impact, dict) else 0.0,
                }
                for team, count, impact in busiest
            ],
        }

    try:
        details = await run_blocking(_refresh)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"Injury refresh failed: {exc}") from exc

    return {
        "status": "ok",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "details": details,
    }


@app.post("/api/refresh/data")
async def refresh_nfl_data():
    def _refresh():
        update_mode()
        file_path = NFL_DIR / "nflData.txt"
        stats = file_path.stat()
        return {
            "file": str(file_path),
            "size_kb": round(stats.st_size / 1024, 2),
            "modified_at": datetime.fromtimestamp(stats.st_mtime).isoformat(),
        }

    try:
        details = await run_blocking(_refresh)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail="nflData.txt not generated. Check scrape output.") from exc
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"NFL data refresh failed: {exc}") from exc

    return {
        "status": "ok",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "details": details,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.server:app", host="0.0.0.0", port=8001, reload=True)

