"""
College Football Game Data Extractor
Fetches detailed game statistics from ESPN API for NCAA Football (FBS)
"""

import requests
import json
from datetime import datetime
import time


def get_games_for_week(season_type, week_num, year=2025):
    """
    gets all games with their IDs for a specific week from ESPN API
    season_type: 'preseason', 'regular', 'postseason'
    """
    base_api_url = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
    
    # College football season types: 1=preseason, 2=regular, 3=postseason
    if season_type == 'preseason':
        season_type_num = 1
    elif season_type == 'postseason':
        season_type_num = 3
    else:
        season_type_num = 2
    
    params = {
        'seasontype': season_type_num,
        'week': week_num,
        'year': year,
        'groups': 80  # FBS only (division I-A)
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
                    competitions = event.get('competitions', [])
                    
                    if competitions and game_id:
                        games.append(game_id)
        
        return games
        
    except Exception as e:
        print(f"  Error getting games: {e}")
        return []


def get_game_details(game_id):
    """
    gets detailed stats for a specific game from ESPN API
    """
    game_detail_url = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary"
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
            'home_team': {}
        }
        
        # get team names and scores
        for competitor in competitors:
            team = competitor.get('team', {})
            team_name = team.get('displayName', 'Unknown')
            score = competitor.get('score', '0')
            home_away = competitor.get('homeAway', '')
            
            if home_away == 'home':
                game_info['home_team']['name'] = team_name
                game_info['home_team']['score'] = score
            else:
                game_info['away_team']['name'] = team_name
                game_info['away_team']['score'] = score
        
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


def scrape_cfb_season():
    """
    scrapes college football season data using ESPN API
    """
    all_games = []
    
    print("Starting College Football data extraction from ESPN API...")
    
    # College football season structure (2024 season for now, since 2025 hasn't started)
    # Week 0 is typically in late August, regular season runs through November
    # Postseason is December-January
    
    year = 2024  # Change to 2025 when that season starts
    
    weeks_config = [
        ('regular', 0),   # Week 0 (late August)
        ('regular', 1), ('regular', 2), ('regular', 3), ('regular', 4),
        ('regular', 5), ('regular', 6), ('regular', 7), ('regular', 8),
        ('regular', 9), ('regular', 10), ('regular', 11), ('regular', 12),
        ('regular', 13), ('regular', 14), ('regular', 15),  # Conference championship week
        ('postseason', 1), ('postseason', 2), ('postseason', 3),  # Bowl games
    ]
    
    for season_type, week_num in weeks_config:
        if season_type == 'postseason':
            week_label = f"POSTSEASON_WEEK_{week_num}"
        else:
            week_label = f"WEEK_{week_num}"
        
        print(f"\nScraping {week_label}...")
        
        # get game IDs for this week
        game_ids = get_games_for_week(season_type, week_num, year)
        
        if not game_ids:
            print(f"  No completed games for {week_label}")
            time.sleep(1)
            continue
        
        print(f"  Found {len(game_ids)} games")
        
        for game_id in game_ids:
            try:
                # get detailed game info
                game_info = get_game_details(game_id)
                
                if not game_info or not game_info['away_team'] or not game_info['home_team']:
                    continue
                
                print(f"  OK: {game_info['away_team']['name']} @ {game_info['home_team']['name']} "
                      f"({game_info['away_team']['score']}-{game_info['home_team']['score']})")
                
                # format game data
                game_data = {
                    'week': week_label,
                    'season_type': season_type.upper(),
                    'week_number': week_num,
                    'away_team': game_info['away_team'],
                    'home_team': game_info['home_team'],
                    'status': 'Final'
                }
                
                all_games.append(game_data)
                
                # be respectful to the API
                time.sleep(1.5)
                
            except Exception as e:
                print(f"    Error processing game {game_id}: {e}")
                continue
        
        # wait between weeks
        time.sleep(1)
    
    return all_games


def write_to_file(games):
    """
    writes game data to cfbData.txt with detailed statistics
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open('cfbData.txt', 'w', encoding='utf-8') as f:
        f.write(f"College Football Game Data - Last Updated: {timestamp}\n")
        f.write("=" * 100 + "\n\n")
        
        if not games:
            f.write("No game data available.\n")
            return
        
        # group games by week
        current_week = None
        for game in games:
            if game['week'] != current_week:
                current_week = game['week']
                f.write(f"\n{'=' * 100}\n")
                f.write(f"{current_week}\n")
                f.write(f"{'=' * 100}\n\n")
            
            away = game['away_team']
            home = game['home_team']
            away_stats = away.get('stats', {})
            home_stats = home.get('stats', {})
            
            # basic game info
            f.write(f"[{game['week']}] {away['name']} @ {home['name']} | "
                   f"{away['score']}-{home['score']} | {game['status']}\n")
            
            # detailed stats
            f.write(f"  AWAY ({away['name']}):\n")
            f.write(f"    Total Yards: {away_stats.get('totalYards', '0')} | "
                   f"Yards/Play: {away_stats.get('yardsPerPlay', '0')} | "
                   f"Possession: {away_stats.get('possessionTime', '0:00')}\n")
            f.write(f"    Passing: {away_stats.get('netPassingYards', '0')}yds | "
                   f"Rushing: {away_stats.get('rushingYards', '0')}yds | "
                   f"1st Downs: {away_stats.get('firstDowns', '0')}\n")
            f.write(f"    3rd Down: {away_stats.get('thirdDownEff', '0-0')} | "
                   f"Turnovers: {away_stats.get('turnovers', '0')} | "
                   f"Sacks: {away_stats.get('sacksYardsLost', '0-0').split('-')[0] if '-' in away_stats.get('sacksYardsLost', '0') else '0'}\n")
            
            f.write(f"  HOME ({home['name']}):\n")
            f.write(f"    Total Yards: {home_stats.get('totalYards', '0')} | "
                   f"Yards/Play: {home_stats.get('yardsPerPlay', '0')} | "
                   f"Possession: {home_stats.get('possessionTime', '0:00')}\n")
            f.write(f"    Passing: {home_stats.get('netPassingYards', '0')}yds | "
                   f"Rushing: {home_stats.get('rushingYards', '0')}yds | "
                   f"1st Downs: {home_stats.get('firstDowns', '0')}\n")
            f.write(f"    3rd Down: {home_stats.get('thirdDownEff', '0-0')} | "
                   f"Turnovers: {home_stats.get('turnovers', '0')} | "
                   f"Sacks: {home_stats.get('sacksYardsLost', '0-0').split('-')[0] if '-' in home_stats.get('sacksYardsLost', '0') else '0'}\n")
            f.write("\n")
        
        f.write(f"\n{'=' * 100}\n")
        f.write(f"Total games recorded: {len(games)}\n")
    
    print(f"\nData written to cfbData.txt - {len(games)} games recorded")


def main():
    """
    main execution function
    """
    print("College Football Data Extractor - Using ESPN API")
    print("=" * 100)
    
    # scrape the data
    games = scrape_cfb_season()
    
    # write to file
    write_to_file(games)
    
    print("\nExtraction complete!")


def get_last_week_from_file():
    """
    reads cfbData.txt and determines the last week scraped
    """
    try:
        with open('cfbData.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        last_week = None
        for line in reversed(lines):
            if ('WEEK_' in line or 'POSTSEASON' in line) and '[' not in line and '=' not in line:
                last_week = line.strip()
                break
        
        if last_week:
            if 'POSTSEASON' in last_week:
                week_num = int(last_week.split('_')[-1])
                return ('postseason', week_num)
            else:
                week_num = int(last_week.split('_')[-1])
                return ('regular', week_num)
        
        return None
    except FileNotFoundError:
        return None


def update_mode():
    """
    incremental update - only fetch new games
    """
    print("CFB Data Updater - Incremental Mode")
    print("=" * 100)
    
    last_week_info = get_last_week_from_file()
    
    if not last_week_info:
        print("No existing data. Running full extraction...\n")
        main()
        return
    
    season_type, last_week_num = last_week_info
    print(f"Last scraped: {season_type.upper()} Week {last_week_num}")
    print("Fetching new games...\n")
    
    year = 2024  # Update when 2025 season starts
    
    weeks_to_scrape = []
    if season_type == 'regular':
        for week in range(last_week_num + 1, 16):
            weeks_to_scrape.append(('regular', week))
        # add postseason
        for week in range(1, 4):
            weeks_to_scrape.append(('postseason', week))
    else:  # postseason
        for week in range(last_week_num + 1, 4):
            weeks_to_scrape.append(('postseason', week))
    
    if not weeks_to_scrape:
        print("Already up to date!")
        return
    
    new_games = []
    for season_type, week_num in weeks_to_scrape:
        week_label = f"POSTSEASON_WEEK_{week_num}" if season_type == 'postseason' else f"WEEK_{week_num}"
        print(f"Checking {week_label}...")
        
        game_ids = get_games_for_week(season_type, week_num, year)
        
        if not game_ids:
            continue
        
        print(f"  Found {len(game_ids)} games")
        
        for game_id in game_ids:
            try:
                game_info = get_game_details(game_id)
                if game_info and game_info['away_team'] and game_info['home_team']:
                    new_games.append({
                        'week': week_label,
                        'season_type': season_type.upper(),
                        'week_number': week_num,
                        'away_team': game_info['away_team'],
                        'home_team': game_info['home_team'],
                        'status': 'Final'
                    })
                    print(f"  OK: {game_info['away_team']['name']} @ {game_info['home_team']['name']}")
                time.sleep(1.5)
            except Exception as e:
                continue
        time.sleep(1)
    
    if not new_games:
        print("\nNo new games found!")
        return
    
    # append to file (similar format as write_to_file)
    with open('cfbData.txt', 'a', encoding='utf-8') as f:
        current_week = None
        for game in new_games:
            if game['week'] != current_week:
                current_week = game['week']
                f.write(f"\n{'=' * 100}\n{current_week}\n{'=' * 100}\n\n")
            
            away = game['away_team']
            home = game['home_team']
            away_stats = away.get('stats', {})
            home_stats = home.get('stats', {})
            
            f.write(f"[{game['week']}] {away['name']} @ {home['name']} | {away['score']}-{home['score']} | {game['status']}\n")
            f.write(f"  AWAY ({away['name']}):\n")
            f.write(f"    Total Yards: {away_stats.get('totalYards', '0')} | Yards/Play: {away_stats.get('yardsPerPlay', '0')} | Possession: {away_stats.get('possessionTime', '0:00')}\n")
            f.write(f"    Passing: {away_stats.get('netPassingYards', '0')}yds | Rushing: {away_stats.get('rushingYards', '0')}yds | 1st Downs: {away_stats.get('firstDowns', '0')}\n")
            f.write(f"    3rd Down: {away_stats.get('thirdDownEff', '0-0')} | Turnovers: {away_stats.get('turnovers', '0')} | Sacks: {away_stats.get('sacksYardsLost', '0-0').split('-')[0] if '-' in away_stats.get('sacksYardsLost', '0') else '0'}\n")
            f.write(f"  HOME ({home['name']}):\n")
            f.write(f"    Total Yards: {home_stats.get('totalYards', '0')} | Yards/Play: {home_stats.get('yardsPerPlay', '0')} | Possession: {home_stats.get('possessionTime', '0:00')}\n")
            f.write(f"    Passing: {home_stats.get('netPassingYards', '0')}yds | Rushing: {home_stats.get('rushingYards', '0')}yds | 1st Downs: {home_stats.get('firstDowns', '0')}\n")
            f.write(f"    3rd Down: {home_stats.get('thirdDownEff', '0-0')} | Turnovers: {home_stats.get('turnovers', '0')} | Sacks: {home_stats.get('sacksYardsLost', '0-0').split('-')[0] if '-' in home_stats.get('sacksYardsLost', '0') else '0'}\n\n")
    
    print(f"Update complete! Added {len(new_games)} games")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--update':
        update_mode()
    else:
        main()

