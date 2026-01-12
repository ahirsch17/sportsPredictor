import requests
import json
from datetime import datetime
import time

def get_games_for_week(season_type, week_num, year=2024):
    """
    gets all games with their IDs for a specific week from ESPN API
    season_type: 'preseason', 'regular', or 'postseason'
    week_num: For postseason, this should be 1-4 (Wild Card, Divisional, Conference, Super Bowl)
              For regular, this is 1-18
              If week_num >= 19, it's converted to postseason week (week_num - 18)
    """
    base_api_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    
    # Convert week 19-22 to postseason weeks 1-4
    actual_week = week_num
    if week_num >= 19 and week_num <= 22:
        actual_week = week_num - 18  # Convert 19->1, 20->2, 21->3, 22->4
        season_type = 'postseason'
    
    if season_type == 'preseason':
        season_type_num = 1
    elif season_type == 'postseason':
        season_type_num = 3
    else:  # regular
        season_type_num = 2
    
    params = {
        'seasontype': season_type_num,
        'week': actual_week,  # Use converted week for API
        'year': year
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
                        competition = competitions[0]
                        competitors = competition.get('competitors', [])
                        
                        if len(competitors) >= 2:
                            games.append(game_id)
        
        return games
        
    except Exception as e:
        print(f"  Error getting games: {e}")
        return []


def get_game_details(game_id):
    """
    gets detailed stats for a specific game from ESPN API INCLUDING QB stats
    """
    game_detail_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary"
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
        
        # Extract QB stats from players section
        if 'boxscore' in data and 'players' in data['boxscore']:
            players_by_team = data['boxscore']['players']
            
            for team_players in players_by_team:
                team_info = team_players.get('team', {})
                team_name = team_info.get('displayName', '')
                
                # Find passing statistics
                for stat_group in team_players.get('statistics', []):
                    if stat_group.get('name') == 'passing':
                        athletes = stat_group.get('athletes', [])
                        if athletes:
                            # Get primary QB (first in list)
                            qb = athletes[0]
                            qb_name = qb.get('athlete', {}).get('displayName', 'Unknown')
                            qb_stats = qb.get('stats', [])
                            
                            # Parse QB stats: ['17/34', '204', '6.0', '1', '3', '1-6', '31.5', '41.8']
                            qb_data = {
                                'name': qb_name,
                                'comp_att': qb_stats[0] if len(qb_stats) > 0 else '0/0',
                                'yards': qb_stats[1] if len(qb_stats) > 1 else '0',
                                'ypa': qb_stats[2] if len(qb_stats) > 2 else '0.0',
                                'tds': qb_stats[3] if len(qb_stats) > 3 else '0',
                                'ints': qb_stats[4] if len(qb_stats) > 4 else '0',
                                'sacks_lost': qb_stats[5] if len(qb_stats) > 5 else '0-0',
                                'qb_rating': qb_stats[7] if len(qb_stats) > 7 else '0.0'
                            }
                            
                            # Store QB data for the correct team
                            if team_name == game_info['home_team'].get('name'):
                                game_info['home_team']['qb'] = qb_data
                            elif team_name == game_info['away_team'].get('name'):
                                game_info['away_team']['qb'] = qb_data
        
        # extract team statistics from boxscore
        if 'boxscore' in data:
            boxscore = data['boxscore']
            teams = boxscore.get('teams', [])
            
            for team in teams:
                team_info = team.get('team', {})
                team_name = team_info.get('displayName', '')
                
                # create stats dict - capture ALL available stats
                stats = {}
                statistics = team.get('statistics', [])
                for stat in statistics:
                    stat_name = stat.get('name', '')
                    stat_value = stat.get('displayValue', '')
                    stats[stat_name] = stat_value
                
                # Also capture numeric values for key stats
                for stat in statistics:
                    stat_name = stat.get('name', '')
                    if 'value' in stat and isinstance(stat.get('value'), (int, float)):
                        stats[f"{stat_name}_value"] = stat.get('value')
                
                # determine if home or away and store stats
                if team_name == game_info['home_team'].get('name'):
                    game_info['home_team']['stats'] = stats
                elif team_name == game_info['away_team'].get('name'):
                    game_info['away_team']['stats'] = stats
        
        return game_info
        
    except Exception as e:
        print(f"    Error getting game details: {e}")
        return None


def scrape_nfl_scores():
    """
    scrapes NFL scores and detailed stats using ESPN API
    """
    all_games = []
    
    print("Starting NFL data extraction with detailed stats from ESPN API...")
    
    # define weeks to scrape
    # Regular weeks 1-18, Postseason weeks 19-22 (mapped to API weeks 1-4)
    weeks_config = [
        ('preseason', 1), ('preseason', 2), ('preseason', 3),
        ('regular', 1), ('regular', 2), ('regular', 3), ('regular', 4), ('regular', 5),
        ('regular', 6), ('regular', 7), ('regular', 8), ('regular', 9), ('regular', 10),
        ('regular', 11), ('regular', 12), ('regular', 13), ('regular', 14), ('regular', 15),
        ('regular', 16), ('regular', 17), ('regular', 18),
        ('postseason', 19), ('postseason', 20), ('postseason', 21), ('postseason', 22)
    ]
    
    for season_type, week_num in weeks_config:
        if season_type == 'preseason':
            week_label = f"PRESEASON_WEEK_{week_num}"
        elif season_type == 'postseason':
            # Store as REGULAR_WEEK_19-22 for compatibility, but these are postseason games
            week_label = f"REGULAR_WEEK_{week_num}"  # Will be 19, 20, 21, or 22
        else:
            week_label = f"REGULAR_WEEK_{week_num}"
        
        print(f"\nScraping {week_label}...")
        
        # get game IDs for this week
        game_ids = get_games_for_week(season_type, week_num)
        
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
    writes game data to nflData.txt with detailed statistics
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open('nflData.txt', 'w', encoding='utf-8') as f:
        f.write(f"NFL Game Data - Last Updated: {timestamp}\n")
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
            
            # QB stats (if available)
            if 'qb' in away:
                qb = away['qb']
                f.write(f"  AWAY QB ({qb['name']}): {qb['comp_att']} for {qb['yards']}yds, {qb['tds']}TD/{qb['ints']}INT, "
                       f"{qb['ypa']} YPA, {qb['qb_rating']} RTG\n")
            if 'qb' in home:
                qb = home['qb']
                f.write(f"  HOME QB ({qb['name']}): {qb['comp_att']} for {qb['yards']}yds, {qb['tds']}TD/{qb['ints']}INT, "
                       f"{qb['ypa']} YPA, {qb['qb_rating']} RTG\n")
            
            # detailed stats
            f.write(f"  AWAY ({away['name']}):\n")
            f.write(f"    Total Yards: {away_stats.get('totalYards', '0')} | "
                   f"Yards/Play: {away_stats.get('yardsPerPlay', '0')} | "
                   f"Possession: {away_stats.get('possessionTime', '0:00')}\n")
            f.write(f"    Passing: {away_stats.get('netPassingYards', '0')}yds ({away_stats.get('completionAttempts', '0-0')}) | "
                   f"Rushing: {away_stats.get('rushingYards', '0')}yds ({away_stats.get('yardsPerRushAttempt', '0.0')} avg) | "
                   f"1st Downs: {away_stats.get('firstDowns', '0')}\n")
            f.write(f"    3rd Down: {away_stats.get('thirdDownEff', '0-0')} | "
                   f"4th Down: {away_stats.get('fourthDownEff', '0-0')} | "
                   f"Red Zone: {away_stats.get('redZoneAttempts', '0-0')}\n")
            f.write(f"    Turnovers: {away_stats.get('turnovers', '0')} (INT: {away_stats.get('interceptions', '0')}, Fum: {away_stats.get('fumblesLost', '0')}) | "
                   f"Sacks: {away_stats.get('sacksYardsLost', '0-0').split('-')[0] if '-' in away_stats.get('sacksYardsLost', '0') else '0'} | "
                   f"Penalties: {away_stats.get('totalPenaltiesYards', '0-0')}\n")
            
            f.write(f"  HOME ({home['name']}):\n")
            f.write(f"    Total Yards: {home_stats.get('totalYards', '0')} | "
                   f"Yards/Play: {home_stats.get('yardsPerPlay', '0')} | "
                   f"Possession: {home_stats.get('possessionTime', '0:00')}\n")
            f.write(f"    Passing: {home_stats.get('netPassingYards', '0')}yds ({home_stats.get('completionAttempts', '0-0')}) | "
                   f"Rushing: {home_stats.get('rushingYards', '0')}yds ({home_stats.get('yardsPerRushAttempt', '0.0')} avg) | "
                   f"1st Downs: {home_stats.get('firstDowns', '0')}\n")
            f.write(f"    3rd Down: {home_stats.get('thirdDownEff', '0-0')} | "
                   f"4th Down: {home_stats.get('fourthDownEff', '0-0')} | "
                   f"Red Zone: {home_stats.get('redZoneAttempts', '0-0')}\n")
            f.write(f"    Turnovers: {home_stats.get('turnovers', '0')} (INT: {home_stats.get('interceptions', '0')}, Fum: {home_stats.get('fumblesLost', '0')}) | "
                   f"Sacks: {home_stats.get('sacksYardsLost', '0-0').split('-')[0] if '-' in home_stats.get('sacksYardsLost', '0') else '0'} | "
                   f"Penalties: {home_stats.get('totalPenaltiesYards', '0-0')}\n")
            f.write("\n")
        
        f.write(f"\n{'=' * 100}\n")
        f.write(f"Total games recorded: {len(games)}\n")
    
    print(f"\nData written to nflData.txt - {len(games)} games recorded")


def main():
    """
    main execution function
    """
    print("NFL Data Extractor - Using ESPN API")
    print("=" * 100)
    
    # scrape the data
    games = scrape_nfl_scores()
    
    # write to file
    write_to_file(games)
    
    print("\nExtraction complete!")


def get_last_week_from_file():
    """
    reads nflData.txt and determines the last week that was scraped
    returns (season_type, week_number) or None
    """
    try:
        with open('nflData.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # find the last week header
        last_week = None
        for line in reversed(lines):
            if 'PRESEASON_WEEK' in line or 'REGULAR_WEEK' in line:
                if '[' not in line and '=' not in line:
                    last_week = line.strip()
                    break
        
        if last_week:
            if 'PRESEASON' in last_week:
                week_num = int(last_week.split('_')[-1])
                return ('preseason', week_num)
            elif 'REGULAR' in last_week:
                week_num = int(last_week.split('_')[-1])
                # Weeks 19-22 are postseason, but stored as REGULAR_WEEK
                if week_num >= 19:
                    return ('postseason', week_num)
                return ('regular', week_num)
        
        return None
        
    except FileNotFoundError:
        return None


def update_mode():
    """
    only fetches games from weeks after the last scraped week
    """
    print("NFL Data Updater - Incremental Mode")
    print("=" * 100)
    
    last_week_info = get_last_week_from_file()
    
    if not last_week_info:
        print("No existing data found or couldn't determine last week.")
        print("Running full extraction instead...\n")
        main()
        return
    
    season_type, last_week_num = last_week_info
    print(f"Last scraped: {season_type.upper()} Week {last_week_num}")
    print("Fetching only new games...\n")
    
    # determine which weeks to scrape
    weeks_to_scrape = []
    
    if season_type == 'preseason':
        # finish preseason, then start regular/postseason
        for week in range(last_week_num, 4):  # Re-check current week for missed games
            weeks_to_scrape.append(('preseason', week))
        # add all regular season weeks (1-18)
        for week in range(1, 19):
            weeks_to_scrape.append(('regular', week))
        # add postseason weeks (19-22)
        for week in range(19, 23):
            weeks_to_scrape.append(('postseason', week))
    elif season_type == 'postseason':
        # Continue from last postseason week
        for week in range(last_week_num, 23):
            weeks_to_scrape.append(('postseason', week))
    else:  # regular season - continue through postseason
        # Re-check the last scraped week to catch any missed games, then continue
        if last_week_num < 19:
            # Still in regular season, continue to postseason
            for week in range(last_week_num, 19):
                weeks_to_scrape.append(('regular', week))
            # Add all postseason weeks
            for week in range(19, 23):
                weeks_to_scrape.append(('postseason', week))
        else:
            # Already in postseason
            for week in range(last_week_num, 23):
                weeks_to_scrape.append(('postseason', week))
    
    if not weeks_to_scrape:
        print("Already up to date! No new weeks to fetch.")
        return
    
    print(f"Will check {len(weeks_to_scrape)} weeks for new games\n")
    
    # fetch new games
    new_games = []
    for season_type, week_num in weeks_to_scrape:
        if season_type == 'preseason':
            week_label = f"PRESEASON_WEEK_{week_num}"
        elif season_type == 'postseason':
            week_label = f"REGULAR_WEEK_{week_num}"  # Store as REGULAR_WEEK_19-22 for compatibility
        else:
            week_label = f"REGULAR_WEEK_{week_num}"
        
        print(f"Checking {week_label} (season_type={season_type}, week={week_num})...")
        
        # get_games_for_week will handle the week conversion (19-22 -> 1-4 for API)
        game_ids = get_games_for_week(season_type, week_num)
        
        if not game_ids:
            print(f"  No completed games")
            continue
        
        print(f"  Found {len(game_ids)} games")
        
        for game_id in game_ids:
            try:
                game_info = get_game_details(game_id)
                
                if not game_info or not game_info['away_team'] or not game_info['home_team']:
                    continue
                
                print(f"  OK: {game_info['away_team']['name']} @ {game_info['home_team']['name']} "
                      f"({game_info['away_team']['score']}-{game_info['home_team']['score']})")
                
                game_data = {
                    'week': week_label,
                    'season_type': season_type.upper(),
                    'week_number': week_num,
                    'away_team': game_info['away_team'],
                    'home_team': game_info['home_team'],
                    'status': 'Final'
                }
                
                new_games.append(game_data)
                time.sleep(1.5)
                
            except Exception as e:
                print(f"    Error: {e}")
                continue
        
        time.sleep(1)
    
    if not new_games:
        print("\nNo new games found. Data is up to date!")
        return
    
    # append new games to existing file
    print(f"\n{len(new_games)} new games found. Appending to nflData.txt...")
    
    with open('nflData.txt', 'a', encoding='utf-8') as f:
        current_week = None
        for game in new_games:
            if game['week'] != current_week:
                current_week = game['week']
                f.write(f"\n{'=' * 100}\n")
                f.write(f"{current_week}\n")
                f.write(f"{'=' * 100}\n\n")
            
            away = game['away_team']
            home = game['home_team']
            away_stats = away.get('stats', {})
            home_stats = home.get('stats', {})
            
            f.write(f"[{game['week']}] {away['name']} @ {home['name']} | "
                   f"{away['score']}-{home['score']} | {game['status']}\n")
            
            # QB stats (if available)
            if 'qb' in away:
                qb = away['qb']
                f.write(f"  AWAY QB ({qb['name']}): {qb['comp_att']} for {qb['yards']}yds, {qb['tds']}TD/{qb['ints']}INT, "
                       f"{qb['ypa']} YPA, {qb['qb_rating']} RTG\n")
            if 'qb' in home:
                qb = home['qb']
                f.write(f"  HOME QB ({qb['name']}): {qb['comp_att']} for {qb['yards']}yds, {qb['tds']}TD/{qb['ints']}INT, "
                       f"{qb['ypa']} YPA, {qb['qb_rating']} RTG\n")
            
            # detailed stats with enhanced metrics
            f.write(f"  AWAY ({away['name']}):\n")
            f.write(f"    Total Yards: {away_stats.get('totalYards', '0')} | "
                   f"Yards/Play: {away_stats.get('yardsPerPlay', '0')} | "
                   f"Possession: {away_stats.get('possessionTime', '0:00')}\n")
            f.write(f"    Passing: {away_stats.get('netPassingYards', '0')}yds ({away_stats.get('completionAttempts', '0-0')}) | "
                   f"Rushing: {away_stats.get('rushingYards', '0')}yds ({away_stats.get('yardsPerRushAttempt', '0.0')} avg) | "
                   f"1st Downs: {away_stats.get('firstDowns', '0')}\n")
            f.write(f"    3rd Down: {away_stats.get('thirdDownEff', '0-0')} | "
                   f"4th Down: {away_stats.get('fourthDownEff', '0-0')} | "
                   f"Red Zone: {away_stats.get('redZoneAttempts', '0-0')}\n")
            f.write(f"    Turnovers: {away_stats.get('turnovers', '0')} (INT: {away_stats.get('interceptions', '0')}, Fum: {away_stats.get('fumblesLost', '0')}) | "
                   f"Sacks: {away_stats.get('sacksYardsLost', '0-0').split('-')[0] if '-' in away_stats.get('sacksYardsLost', '0') else '0'} | "
                   f"Penalties: {away_stats.get('totalPenaltiesYards', '0-0')}\n")
            
            f.write(f"  HOME ({home['name']}):\n")
            f.write(f"    Total Yards: {home_stats.get('totalYards', '0')} | "
                   f"Yards/Play: {home_stats.get('yardsPerPlay', '0')} | "
                   f"Possession: {home_stats.get('possessionTime', '0:00')}\n")
            f.write(f"    Passing: {home_stats.get('netPassingYards', '0')}yds ({home_stats.get('completionAttempts', '0-0')}) | "
                   f"Rushing: {home_stats.get('rushingYards', '0')}yds ({home_stats.get('yardsPerRushAttempt', '0.0')} avg) | "
                   f"1st Downs: {home_stats.get('firstDowns', '0')}\n")
            f.write(f"    3rd Down: {home_stats.get('thirdDownEff', '0-0')} | "
                   f"4th Down: {home_stats.get('fourthDownEff', '0-0')} | "
                   f"Red Zone: {home_stats.get('redZoneAttempts', '0-0')}\n")
            f.write(f"    Turnovers: {home_stats.get('turnovers', '0')} (INT: {home_stats.get('interceptions', '0')}, Fum: {home_stats.get('fumblesLost', '0')}) | "
                   f"Sacks: {home_stats.get('sacksYardsLost', '0-0').split('-')[0] if '-' in home_stats.get('sacksYardsLost', '0') else '0'} | "
                   f"Penalties: {home_stats.get('totalPenaltiesYards', '0-0')}\n")
            f.write("\n")
    
    print(f"Update complete! Added {len(new_games)} games to nflData.txt")


if __name__ == "__main__":
    import sys
    
    # Check if user wants update mode
    if len(sys.argv) > 1 and sys.argv[1] == '--update':
        update_mode()
    else:
        main()
