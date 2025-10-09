"""
MLB Game Data Extractor
Fetches detailed game statistics from ESPN API for MLB
"""

import requests
import json
from datetime import datetime
import time


def get_games_for_date(date_str, year=2024):
    """
    gets all completed MLB games for a specific date from ESPN API
    date_str format: YYYYMMDD (e.g., "20240715")
    """
    base_api_url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
    
    params = {
        'dates': date_str
    }
    
    try:
        response = requests.get(base_api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        games = []
        
        if 'events' in data:
            for event in data['events']:
                status = event.get('status', {}).get('type', {}).get('name', '')
                
                # only include completed games
                if status.lower() == 'status_final':
                    game_id = event.get('id')
                    if game_id:
                        games.append(game_id)
        
        return games
        
    except Exception as e:
        print(f"  Error getting games for {date_str}: {e}")
        return []


def get_game_details(game_id):
    """
    gets detailed stats for a specific MLB game from ESPN API
    """
    game_detail_url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary"
    params = {'event': game_id}
    
    try:
        response = requests.get(game_detail_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # extract team info
        header = data.get('header', {})
        competitions = header.get('competitions', [{}])[0]
        competitors = competitions.get('competitors', [])
        
        game_info = {
            'away_team': {},
            'home_team': {},
            'game_date': header.get('competitions', [{}])[0].get('date', '')
        }
        
        # get team names and scores
        for competitor in competitors:
            team = competitor.get('team', {})
            team_name = team.get('displayName', 'Unknown')
            score = competitor.get('score', '0')
            home_away = competitor.get('homeAway', '')
            
            if home_away == 'home':
                game_info['home_team']['name'] = team_name
                game_info['home_team']['score'] = int(score)
            else:
                game_info['away_team']['name'] = team_name
                game_info['away_team']['score'] = int(score)
        
        # extract team statistics from boxscore
        if 'boxscore' in data:
            boxscore = data['boxscore']
            teams = boxscore.get('teams', [])
            
            for team in teams:
                team_info = team.get('team', {})
                team_name = team_info.get('displayName', '')
                
                # create stats dict
                stats = {}
                statistics = team.get('statistics', [])
                for stat in statistics:
                    stat_name = stat.get('name', '')
                    stat_value = stat.get('displayValue', '')
                    stats[stat_name] = stat_value
                
                # determine if home or away and store stats
                if team_name == game_info['home_team'].get('name'):
                    game_info['home_team']['stats'] = stats
                elif team_name == game_info['away_team'].get('name'):
                    game_info['away_team']['stats'] = stats
        
        return game_info
        
    except Exception as e:
        print(f"    Error getting game details: {e}")
        return None


def scrape_mlb_season():
    """
    scrapes MLB season data (April through October)
    """
    all_games = []
    
    print("Starting MLB data extraction from ESPN API...")
    print("This will take several minutes as we process the full season...\n")
    
    # MLB season typically runs March-October
    # Format: YYYYMMDD
    year = 2025
    
    # Define date ranges for 2025 season INCLUDING POSTSEASON
    # Spring Training (March) through October (postseason)
    dates_to_scrape = []
    
    # Generate dates for each month
    months = [
        (3, 31),   # March (31 days) - Spring Training/Preseason
        (4, 30),   # April (30 days) - Regular season start
        (5, 31),   # May (31 days)
        (6, 30),   # June (30 days)
        (7, 31),   # July (31 days)
        (8, 31),   # August (31 days)
        (9, 30),   # September (30 days)
        (10, 31),  # October (31 days) - POSTSEASON
    ]
    
    for month, days in months:
        for day in range(1, days + 1):
            date_str = f"{year}{month:02d}{day:02d}"
            dates_to_scrape.append(date_str)
    
    print(f"Scanning {len(dates_to_scrape)} days for completed games...\n")
    
    games_found = 0
    for i, date_str in enumerate(dates_to_scrape):
        if i % 10 == 0:
            print(f"Progress: {i}/{len(dates_to_scrape)} days scanned, {games_found} games found...")
        
        game_ids = get_games_for_date(date_str, year)
        
        for game_id in game_ids:
            try:
                game_info = get_game_details(game_id)
                
                if not game_info or not game_info['away_team'] or not game_info['home_team']:
                    continue
                
                games_found += 1
                print(f"  [{date_str}] {game_info['away_team']['name']} @ {game_info['home_team']['name']} "
                      f"({game_info['away_team']['score']}-{game_info['home_team']['score']})")
                
                all_games.append(game_info)
                
                # be respectful to the API
                time.sleep(0.5)
                
            except Exception as e:
                print(f"    Error processing game {game_id}: {e}")
                continue
        
        # brief pause between days
        time.sleep(0.2)
    
    return all_games


def write_to_file(games):
    """
    writes game data to mlbData.txt with detailed statistics
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open('mlbData.txt', 'w', encoding='utf-8') as f:
        f.write(f"MLB Game Data - Last Updated: {timestamp}\n")
        f.write("=" * 100 + "\n\n")
        
        if not games:
            f.write("No game data available.\n")
            return
        
        # group games by date
        games_by_date = {}
        for game in games:
            date = game['game_date'][:10]  # YYYY-MM-DD
            if date not in games_by_date:
                games_by_date[date] = []
            games_by_date[date].append(game)
        
        for date in sorted(games_by_date.keys()):
            f.write(f"\n{'=' * 100}\n")
            f.write(f"DATE: {date}\n")
            f.write(f"{'=' * 100}\n\n")
            
            for game in games_by_date[date]:
                away = game['away_team']
                home = game['home_team']
                away_stats = away.get('stats', {})
                home_stats = home.get('stats', {})
                
                # basic game info
                f.write(f"{away['name']} @ {home['name']} | {away['score']}-{home['score']}\n")
                
                # detailed stats
                f.write(f"  AWAY ({away['name']}):\n")
                f.write(f"    Runs: {away_stats.get('runs', '0')} | "
                       f"Hits: {away_stats.get('hits', '0')} | "
                       f"Errors: {away_stats.get('errors', '0')}\n")
                f.write(f"    Batting Avg: {away_stats.get('avg', '.000')} | "
                       f"OBP: {away_stats.get('obp', '.000')} | "
                       f"SLG: {away_stats.get('slg', '.000')}\n")
                f.write(f"    HR: {away_stats.get('homeRuns', '0')} | "
                       f"RBI: {away_stats.get('rbi', '0')} | "
                       f"LOB: {away_stats.get('leftOnBase', '0')}\n")
                
                f.write(f"  HOME ({home['name']}):\n")
                f.write(f"    Runs: {home_stats.get('runs', '0')} | "
                       f"Hits: {home_stats.get('hits', '0')} | "
                       f"Errors: {home_stats.get('errors', '0')}\n")
                f.write(f"    Batting Avg: {home_stats.get('avg', '.000')} | "
                       f"OBP: {home_stats.get('obp', '.000')} | "
                       f"SLG: {home_stats.get('slg', '.000')}\n")
                f.write(f"    HR: {home_stats.get('homeRuns', '0')} | "
                       f"RBI: {home_stats.get('rbi', '0')} | "
                       f"LOB: {home_stats.get('leftOnBase', '0')}\n")
                f.write("\n")
        
        f.write(f"\n{'=' * 100}\n")
        f.write(f"Total games recorded: {len(games)}\n")
    
    print(f"\nData written to mlbData.txt - {len(games)} games recorded")


def main():
    """
    main execution function
    """
    print("MLB Data Extractor - Using ESPN API")
    print("=" * 100)
    
    # scrape the data
    games = scrape_mlb_season()
    
    # write to file
    write_to_file(games)
    
    print("\nExtraction complete!")


def get_last_date_from_file():
    """
    reads mlbData.txt and finds the last game date
    returns date string in YYYYMMDD format or None
    """
    try:
        with open('mlbData.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # find the last date header
        last_date = None
        for line in reversed(lines):
            if 'DATE:' in line:
                # extract date like "2024-10-01" and convert to "20241001"
                date_str = line.split('DATE:')[1].strip()
                last_date = date_str.replace('-', '')
                break
        
        return last_date
        
    except FileNotFoundError:
        return None


def update_mode():
    """
    incremental update - only fetch games after last date
    """
    print("MLB Data Updater - Incremental Mode")
    print("=" * 100)
    
    last_date = get_last_date_from_file()
    
    if not last_date:
        print("No existing data found. Running full extraction...\n")
        main()
        return
    
    print(f"Last game date in file: {last_date[:4]}-{last_date[4:6]}-{last_date[6:]}")
    print("Fetching only games after this date...\n")
    
    # parse last date
    year = int(last_date[:4])
    month = int(last_date[4:6])
    day = int(last_date[6:])
    
    # generate dates from day after last date through end of October
    dates_to_scrape = []
    
    # define month ranges (start from where we left off)
    months = [
        (3, 31), (4, 30), (5, 31), (6, 30), 
        (7, 31), (8, 31), (9, 30), (10, 31)
    ]
    
    started = False
    for m, max_days in months:
        if m < month:
            continue  # skip months before our last date
        
        start_day = day + 1 if m == month else 1
        
        for d in range(start_day, max_days + 1):
            date_str = f"{year}{m:02d}{d:02d}"
            dates_to_scrape.append(date_str)
    
    if not dates_to_scrape:
        print("Already up to date!")
        return
    
    print(f"Checking {len(dates_to_scrape)} days for new games...\n")
    
    new_games = []
    for i, date_str in enumerate(dates_to_scrape):
        if i % 10 == 0:
            print(f"Progress: {i}/{len(dates_to_scrape)} days checked...")
        
        game_ids = get_games_for_date(date_str, year)
        
        for game_id in game_ids:
            try:
                game_info = get_game_details(game_id)
                
                if game_info and game_info['away_team'] and game_info['home_team']:
                    print(f"  [{date_str}] {game_info['away_team']['name']} @ {game_info['home_team']['name']}")
                    new_games.append(game_info)
                    time.sleep(0.5)
            except:
                continue
        
        time.sleep(0.2)
    
    if not new_games:
        print("\nNo new games found!")
        return
    
    print(f"\n{len(new_games)} new games found. Appending to mlbData.txt...")
    
    # append to file
    with open('mlbData.txt', 'a', encoding='utf-8') as f:
        games_by_date = {}
        for game in new_games:
            date = game['game_date'][:10]
            if date not in games_by_date:
                games_by_date[date] = []
            games_by_date[date].append(game)
        
        for date in sorted(games_by_date.keys()):
            f.write(f"\n{'=' * 100}\n")
            f.write(f"DATE: {date}\n")
            f.write(f"{'=' * 100}\n\n")
            
            for game in games_by_date[date]:
                away = game['away_team']
                home = game['home_team']
                away_stats = away.get('stats', {})
                home_stats = home.get('stats', {})
                
                f.write(f"{away['name']} @ {home['name']} | {away['score']}-{home['score']}\n")
                f.write(f"  AWAY ({away['name']}):\n")
                f.write(f"    Runs: {away_stats.get('runs', '0')} | Hits: {away_stats.get('hits', '0')} | Errors: {away_stats.get('errors', '0')}\n")
                f.write(f"    Batting Avg: {away_stats.get('avg', '.000')} | OBP: {away_stats.get('obp', '.000')} | SLG: {away_stats.get('slg', '.000')}\n")
                f.write(f"    HR: {away_stats.get('homeRuns', '0')} | RBI: {away_stats.get('rbi', '0')} | LOB: {away_stats.get('leftOnBase', '0')}\n")
                f.write(f"  HOME ({home['name']}):\n")
                f.write(f"    Runs: {home_stats.get('runs', '0')} | Hits: {home_stats.get('hits', '0')} | Errors: {home_stats.get('errors', '0')}\n")
                f.write(f"    Batting Avg: {home_stats.get('avg', '.000')} | OBP: {home_stats.get('obp', '.000')} | SLG: {home_stats.get('slg', '.000')}\n")
                f.write(f"    HR: {home_stats.get('homeRuns', '0')} | RBI: {home_stats.get('rbi', '0')} | LOB: {home_stats.get('leftOnBase', '0')}\n\n")
    
    print(f"Update complete! Added {len(new_games)} games")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--update':
        update_mode()
    else:
        main()


