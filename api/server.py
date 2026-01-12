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
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Ensure NFL modules are importable
BASE_DIR = Path(__file__).resolve().parent.parent
NFL_DIR = BASE_DIR / "NFL"
WEB_DIR = BASE_DIR / "web"
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
from dataextract import update_mode, get_last_week_from_file  # type: ignore


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
    "http://localhost:8001",
    "http://127.0.0.1:8001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from the web directory
if WEB_DIR.exists():
    # Serve CSS and JS files directly
    @app.get("/styles.css")
    async def serve_styles():
        file_path = WEB_DIR / "styles.css"
        if file_path.exists():
            return FileResponse(str(file_path), media_type="text/css")
        raise HTTPException(status_code=404, detail="styles.css not found")
    
    @app.get("/console.css")
    async def serve_console_css():
        file_path = WEB_DIR / "console.css"
        if file_path.exists():
            return FileResponse(str(file_path), media_type="text/css")
        raise HTTPException(status_code=404, detail="console.css not found")
    
    @app.get("/app.js")
    async def serve_app_js():
        file_path = WEB_DIR / "app.js"
        if file_path.exists():
            return FileResponse(str(file_path), media_type="application/javascript")
        raise HTTPException(status_code=404, detail="app.js not found")
    
    # Serve the main HTML file at the root
    @app.get("/")
    async def read_root():
        index_file = WEB_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file), media_type="text/html")
        return {"message": "SportsPredictor API", "docs": "/docs"}
else:
    @app.get("/")
    async def read_root():
        return {"message": "SportsPredictor API", "docs": "/docs", "note": "Web directory not found"}


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
    season_type: str = "regular"  # 'regular' includes both regular season and postseason
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


@app.get("/api/data/status")
async def get_data_status():
    """Get information about the latest data available"""
    def _get_status():
        # Get last week from NFL data
        last_week_info = get_last_week_from_file()
        nfl_data_week = None
        nfl_data_season_type = None
        
        if last_week_info:
            nfl_data_season_type, nfl_data_week = last_week_info
        
        # Check if nflData.txt exists and get file info
        file_path = NFL_DIR / "nflData.txt"
        file_exists = file_path.exists()
        file_info = {}
        if file_exists:
            stats = file_path.stat()
            file_info = {
                "size_kb": round(stats.st_size / 1024, 2),
                "modified_at": datetime.fromtimestamp(stats.st_mtime).isoformat(),
            }
        
        # Check injury file
        injury_file = NFL_DIR / "injuries_current.txt"
        injury_exists = injury_file.exists()
        injury_info = {}
        if injury_exists:
            injury_stats = injury_file.stat()
            injury_info = {
                "modified_at": datetime.fromtimestamp(injury_stats.st_mtime).isoformat(),
            }
        
        return {
            "nfl_data": {
                "latest_week": nfl_data_week,
                "season_type": nfl_data_season_type,
                "file_exists": file_exists,
                **file_info,
            },
            "injuries": {
                "file_exists": injury_exists,
                **injury_info,
            }
        }
    
    try:
        status = await run_blocking(_get_status)
        return status
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"Failed to get data status: {exc}") from exc


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
        # Auto-detect postseason for weeks 19-22
        season_type = request.season_type
        if request.week >= 19 and request.week <= 22:
            season_type = 'postseason'  # Use postseason API type for weeks 19-22
        result = batch_predict_week(request.week, season_type, use_ml=request.use_ml)
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


@app.get("/api/fantasy/qb-rankings")
async def get_qb_rankings():
    """Get QB rankings for fantasy football based on recent performance"""
    def _get_rankings():
        # Parse QB stats directly from nflData.txt to get names
        nfl_data_file = BASE_DIR / "NFL" / "nflData.txt"
        if not nfl_data_file.exists():
            return {"qbs": []}
        
        qb_stats = {}
        current_week = None
        current_game_teams = None
        
        try:
            with open(nfl_data_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Track current week
                if ('PRESEASON_WEEK' in line or 'REGULAR_WEEK' in line) and '[' not in line:
                    current_week = line
                    current_game_teams = None
                    continue
                
                # Parse game line to get team names
                if line.startswith('[') and '@' in line and '|' in line:
                    try:
                        game_part = line.split(']')[1].split('|')[0].strip()
                        away_team, home_team = game_part.split('@')
                        current_game_teams = {
                            'away': away_team.strip(),
                            'home': home_team.strip()
                        }
                    except Exception:
                        pass
                    continue
                
                # Parse QB lines: "  AWAY QB (Name): comp/att for yards, TDs/INTs, YPA, RTG"
                if ('AWAY QB (' in line or 'HOME QB (' in line) and current_week and 'PRESEASON' not in current_week:
                    try:
                        # Extract QB name
                        qb_name = line.split('(')[1].split(')')[0] if '(' in line else None
                        if not qb_name or not current_game_teams:
                            continue
                        
                        # Determine team
                        is_away = 'AWAY QB' in line
                        team_name = current_game_teams['away'] if is_away else current_game_teams['home']
                        
                        # Parse stats: "comp/att for yards, TDs/INTs, YPA, RTG"
                        stats_part = line.split('):')[1].strip() if '):' in line else ''
                        parts = [p.strip() for p in stats_part.split(',')]
                        
                        if len(parts) < 3:
                            continue
                        
                        # Parse comp/att and yards from first part: "comp/att for yards"
                        comp_att_yards = parts[0]
                        comp_att = comp_att_yards.split('for')[0].strip()
                        yards_str = comp_att_yards.split('for')[1].replace('yds', '').strip()
                        
                        # Parse TDs/INTs from second part: "TDsINTs"
                        td_int_part = parts[1]
                        tds_str = td_int_part.split('TD')[0].strip() if 'TD' in td_int_part else '0'
                        ints_str = td_int_part.split('/')[1].split('INT')[0].strip() if '/' in td_int_part and 'INT' in td_int_part else '0'
                        
                        # Parse YPA (optional)
                        ypa_str = parts[2].replace('YPA', '').strip() if len(parts) > 2 else '0.0'
                        
                        # Parse RTG (optional)
                        rating_str = parts[3].replace('RTG', '').strip() if len(parts) > 3 else '0.0'
                        
                        # Initialize QB stats if needed
                        if qb_name not in qb_stats:
                            qb_stats[qb_name] = {
                                'name': qb_name,
                                'team': team_name,
                                'games': 0,
                                'total_yards': 0,
                                'total_tds': 0,
                                'total_ints': 0,
                                'total_att': 0,
                                'total_comp': 0,
                                'qb_ratings': []
                            }
                        
                        stats = qb_stats[qb_name]
                        stats['games'] += 1
                        stats['team'] = team_name  # Update to most recent team
                        
                        # Add stats
                        try:
                            stats['total_yards'] += int(yards_str)
                            stats['total_tds'] += int(tds_str)
                            stats['total_ints'] += int(ints_str)
                            
                            if '/' in comp_att:
                                comp, att = comp_att.split('/')
                                stats['total_comp'] += int(comp)
                                stats['total_att'] += int(att)
                            
                            rating = float(rating_str)
                            if rating > 0:
                                stats['qb_ratings'].append(rating)
                        except (ValueError, TypeError):
                            pass
                            
                    except Exception:
                        continue
        
        except Exception:
            return {"qbs": []}
        
        # Calculate averages and fantasy score
        qb_list = []
        for qb_name, stats in qb_stats.items():
            if stats['games'] == 0:
                continue
            
            avg_yards = stats['total_yards'] / stats['games']
            avg_tds = stats['total_tds'] / stats['games']
            avg_ints = stats['total_ints'] / stats['games']
            completion_pct = (stats['total_comp'] / stats['total_att'] * 100) if stats['total_att'] > 0 else 0
            avg_rating = sum(stats['qb_ratings']) / len(stats['qb_ratings']) if stats['qb_ratings'] else 0
            
            # Simple fantasy score (yards/25 + TDs*4 - INTs*2)
            fantasy_score = (avg_yards / 25) + (avg_tds * 4) - (avg_ints * 2)
            
            qb_list.append({
                'name': stats['name'],
                'team': stats['team'],
                'games': stats['games'],
                'avg_yards': round(avg_yards, 1),
                'avg_tds': round(avg_tds, 1),
                'avg_ints': round(avg_ints, 1),
                'completion_pct': round(completion_pct, 1),
                'avg_rating': round(avg_rating, 1),
                'fantasy_score': round(fantasy_score, 1)
            })
        
        # Sort by fantasy score descending
        qb_list.sort(key=lambda x: x['fantasy_score'], reverse=True)
        
        return {"qbs": qb_list}
    
    try:
        rankings = await run_blocking(_get_rankings)
        return rankings
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"Failed to get QB rankings: {exc}") from exc


@app.get("/api/fantasy/team-offense")
async def get_team_offense_rankings():
    """Get team offensive rankings for fantasy (good for RB/WR picks)"""
    def _get_rankings():
        teams_data = read_nfl_data()
        if not teams_data:
            return {"teams": []}
        
        team_list = []
        
        for team_name, games in teams_data.items():
            regular_games = [g for g in games if not g.get('preseason', False)]
            if not regular_games:
                continue
            
            total_rush_yds = 0
            total_pass_yds = 0
            total_points = 0
            game_count = 0
            
            for game in regular_games:
                off_stats = game.get('off_stats', {})
                total_points += game.get('score_for', 0)
                
                rush_yds = off_stats.get('rushingYards', 0)
                pass_yds = off_stats.get('passingYards', 0)
                
                if isinstance(rush_yds, (int, float)):
                    total_rush_yds += rush_yds
                if isinstance(pass_yds, (int, float)):
                    total_pass_yds += pass_yds
                
                game_count += 1
            
            if game_count > 0:
                avg_rush = total_rush_yds / game_count
                avg_pass = total_pass_yds / game_count
                avg_points = total_points / game_count
                
                # Fantasy relevance score
                # High rushing = good for RBs, high passing = good for WRs
                rb_score = avg_rush + (avg_points * 2)  # RBs benefit from rushing and scoring
                wr_score = avg_pass + (avg_points * 2)  # WRs benefit from passing and scoring
                
                team_list.append({
                    'team': team_name,
                    'avg_rushing_yds': round(avg_rush, 1),
                    'avg_passing_yds': round(avg_pass, 1),
                    'avg_points': round(avg_points, 1),
                    'rb_score': round(rb_score, 1),
                    'wr_score': round(wr_score, 1)
                })
        
        # Sort by RB score and WR score separately
        rb_sorted = sorted(team_list, key=lambda x: x['rb_score'], reverse=True)
        wr_sorted = sorted(team_list, key=lambda x: x['wr_score'], reverse=True)
        
        return {
            "teams": team_list,
            "rb_rankings": rb_sorted[:10],  # Top 10 for RB
            "wr_rankings": wr_sorted[:10]   # Top 10 for WR
        }
    
    try:
        rankings = await run_blocking(_get_rankings)
        return rankings
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"Failed to get team rankings: {exc}") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.server:app", host="0.0.0.0", port=8001, reload=True)

