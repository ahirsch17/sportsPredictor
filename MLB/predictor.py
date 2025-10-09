"""
MLB Game Predictor - Advanced Analysis
Analyzes detailed baseball stats to predict outcomes with pitching matchups
"""

# Import injury data functions
try:
    from injuryextract import get_injury_data, calculate_injury_impact
    INJURIES_AVAILABLE = True
except ImportError:
    INJURIES_AVAILABLE = False
    print("WARNING: Injury data module not available")

# Import park factors
try:
    from park_factors import get_park_factor, get_park_impact_score, calculate_park_adjustment
    PARK_FACTORS_AVAILABLE = True
except ImportError:
    PARK_FACTORS_AVAILABLE = False
    print("WARNING: Park factors module not available")

# Import weather
try:
    from weather import get_weather_summary
    WEATHER_AVAILABLE = True
except ImportError:
    WEATHER_AVAILABLE = False
    print("WARNING: Weather module not available")

# Import pitcher stats
try:
    from pitcher_stats import calculate_pitcher_quality_score, compare_pitchers, get_bullpen_stats, SAMPLE_PITCHERS
    PITCHER_STATS_AVAILABLE = True
except ImportError:
    PITCHER_STATS_AVAILABLE = False
    print("WARNING: Pitcher stats module not available")


def parse_stat(stat_str, stat_type='float'):
    """
    safely parse stat string to number
    """
    try:
        if stat_type == 'int':
            return int(stat_str.replace(',', ''))
        elif stat_type == 'float':
            return float(stat_str.replace(',', ''))
    except:
        return 0.0


def read_mlb_data():
    """
    reads mlbData.txt and parses into structured format
    """
    teams_data = {}
    
    try:
        with open('mlbData.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        i = 0
        current_date = None
        
        while i < len(lines):
            line = lines[i].strip()
            
            # detect date header
            if 'DATE:' in line and '=' not in line:
                current_date = line.split('DATE:')[1].strip()
                i += 1
                continue
            
            # parse game line (team @ team | score-score)
            if '@' in line and '|' in line and 'AWAY' not in line and 'HOME' not in line:
                try:
                    # extract basic game info
                    teams_part = line.split('|')[0].strip()
                    scores_part = line.split('|')[1].strip()
                    
                    away_team, home_team = teams_part.split('@')
                    away_team = away_team.strip()
                    home_team = home_team.strip()
                    
                    away_score, home_score = scores_part.split('-')
                    away_score = int(away_score.strip())
                    home_score = int(home_score.strip())
                    
                    # parse detailed stats from next lines
                    away_stats = {}
                    home_stats = {}
                    
                    # look ahead for AWAY stats
                    if i + 1 < len(lines) and 'AWAY' in lines[i + 1]:
                        i += 2  # skip "AWAY (team):" line
                        
                        # parse away runs/hits/errors
                        if i < len(lines):
                            stats_line = lines[i].strip()
                            if 'Runs:' in stats_line:
                                parts = stats_line.split('|')
                                for part in parts:
                                    if 'Runs:' in part:
                                        away_stats['runs'] = parse_stat(part.split(':')[1].strip(), 'int')
                                    elif 'Hits:' in part:
                                        away_stats['hits'] = parse_stat(part.split(':')[1].strip(), 'int')
                                    elif 'Errors:' in part:
                                        away_stats['errors'] = parse_stat(part.split(':')[1].strip(), 'int')
                            i += 1
                        
                        # parse away batting stats
                        if i < len(lines):
                            stats_line = lines[i].strip()
                            if 'Batting Avg:' in stats_line:
                                parts = stats_line.split('|')
                                for part in parts:
                                    if 'Batting Avg:' in part:
                                        away_stats['avg'] = parse_stat(part.split(':')[1].strip())
                                    elif 'OBP:' in part:
                                        away_stats['obp'] = parse_stat(part.split(':')[1].strip())
                                    elif 'SLG:' in part:
                                        away_stats['slg'] = parse_stat(part.split(':')[1].strip())
                            i += 1
                        
                        # parse away HR/RBI/LOB
                        if i < len(lines):
                            stats_line = lines[i].strip()
                            if 'HR:' in stats_line:
                                parts = stats_line.split('|')
                                for part in parts:
                                    if 'HR:' in part:
                                        away_stats['hr'] = parse_stat(part.split(':')[1].strip(), 'int')
                                    elif 'RBI:' in part:
                                        away_stats['rbi'] = parse_stat(part.split(':')[1].strip(), 'int')
                                    elif 'LOB:' in part:
                                        away_stats['lob'] = parse_stat(part.split(':')[1].strip(), 'int')
                            i += 1
                    
                    # look ahead for HOME stats
                    if i < len(lines) and 'HOME' in lines[i]:
                        i += 1  # skip "HOME (team):" line
                        
                        # parse home runs/hits/errors
                        if i < len(lines):
                            stats_line = lines[i].strip()
                            if 'Runs:' in stats_line:
                                parts = stats_line.split('|')
                                for part in parts:
                                    if 'Runs:' in part:
                                        home_stats['runs'] = parse_stat(part.split(':')[1].strip(), 'int')
                                    elif 'Hits:' in part:
                                        home_stats['hits'] = parse_stat(part.split(':')[1].strip(), 'int')
                                    elif 'Errors:' in part:
                                        home_stats['errors'] = parse_stat(part.split(':')[1].strip(), 'int')
                            i += 1
                        
                        # parse home batting stats
                        if i < len(lines):
                            stats_line = lines[i].strip()
                            if 'Batting Avg:' in stats_line:
                                parts = stats_line.split('|')
                                for part in parts:
                                    if 'Batting Avg:' in part:
                                        home_stats['avg'] = parse_stat(part.split(':')[1].strip())
                                    elif 'OBP:' in part:
                                        home_stats['obp'] = parse_stat(part.split(':')[1].strip())
                                    elif 'SLG:' in part:
                                        home_stats['slg'] = parse_stat(part.split(':')[1].strip())
                            i += 1
                        
                        # parse home HR/RBI/LOB
                        if i < len(lines):
                            stats_line = lines[i].strip()
                            if 'HR:' in stats_line:
                                parts = stats_line.split('|')
                                for part in parts:
                                    if 'HR:' in part:
                                        home_stats['hr'] = parse_stat(part.split(':')[1].strip(), 'int')
                                    elif 'RBI:' in part:
                                        home_stats['rbi'] = parse_stat(part.split(':')[1].strip(), 'int')
                                    elif 'LOB:' in part:
                                        home_stats['lob'] = parse_stat(part.split(':')[1].strip(), 'int')
                            i += 1
                    
                    # determine winner and create game records
                    if away_score > home_score:
                        # away team won
                        if away_team not in teams_data:
                            teams_data[away_team] = []
                        teams_data[away_team].append({
                            'opponent': home_team,
                            'location': 'away',
                            'result': 'W',
                            'runs_for': away_score,
                            'runs_against': home_score,
                            'date': current_date,
                            'batting_stats': away_stats,
                            'opponent_batting': home_stats
                        })
                        
                        if home_team not in teams_data:
                            teams_data[home_team] = []
                        teams_data[home_team].append({
                            'opponent': away_team,
                            'location': 'home',
                            'result': 'L',
                            'runs_for': home_score,
                            'runs_against': away_score,
                            'date': current_date,
                            'batting_stats': home_stats,
                            'opponent_batting': away_stats
                        })
                    
                    elif home_score > away_score:
                        # home team won
                        if home_team not in teams_data:
                            teams_data[home_team] = []
                        teams_data[home_team].append({
                            'opponent': away_team,
                            'location': 'home',
                            'result': 'W',
                            'runs_for': home_score,
                            'runs_against': away_score,
                            'date': current_date,
                            'batting_stats': home_stats,
                            'opponent_batting': away_stats
                        })
                        
                        if away_team not in teams_data:
                            teams_data[away_team] = []
                        teams_data[away_team].append({
                            'opponent': home_team,
                            'location': 'away',
                            'result': 'L',
                            'runs_for': away_score,
                            'runs_against': home_score,
                            'date': current_date,
                            'batting_stats': away_stats,
                            'opponent_batting': home_stats
                        })
                
                except Exception as e:
                    print(f"Error parsing game: {e}")
                    i += 1
                    continue
            
            i += 1
    
    except FileNotFoundError:
        print("ERROR: mlbData.txt not found. Please run dataextract.py first.")
        return None
    
    return teams_data


def calculate_weighted_average(values, use_recency_weighting=True):
    """
    calculates weighted average with exponential recency weighting
    recent games weighted higher (~70% for recent, ~30% for older)
    """
    if not values:
        return 0
    
    if not use_recency_weighting or len(values) <= 3:
        return sum(values) / len(values)
    
    # exponential weights: more recent = higher weight
    weights = []
    total_weight = 0
    for i in range(len(values)):
        # exponential decay: recent games get ~3x weight of oldest games
        weight = 1.0 * (2.0 ** (i / len(values)))
        weights.append(weight)
        total_weight += weight
    
    # normalize weights
    weights = [w / total_weight for w in weights]
    
    # calculate weighted sum
    weighted_sum = sum(v * w for v, w in zip(values, weights))
    return weighted_sum


def calculate_team_averages(team, teams_data):
    """
    calculates team batting and pitching averages with recency weighting
    """
    if team not in teams_data:
        return None
    
    games = teams_data[team]
    
    if not games:
        return None
    
    # extract values for weighted averaging
    runs_scored_vals = [g['runs_for'] for g in games]
    runs_allowed_vals = [g['runs_against'] for g in games]
    
    hits_vals = [g['batting_stats'].get('hits', 0) for g in games]
    errors_vals = [g['batting_stats'].get('errors', 0) for g in games]
    avg_vals = [g['batting_stats'].get('avg', 0) for g in games]
    obp_vals = [g['batting_stats'].get('obp', 0) for g in games]
    slg_vals = [g['batting_stats'].get('slg', 0) for g in games]
    hr_vals = [g['batting_stats'].get('hr', 0) for g in games]
    
    opp_hits_vals = [g['opponent_batting'].get('hits', 0) for g in games]
    opp_errors_vals = [g['opponent_batting'].get('errors', 0) for g in games]
    
    # calculate weighted averages
    avg_runs_scored = calculate_weighted_average(runs_scored_vals)
    avg_runs_allowed = calculate_weighted_average(runs_allowed_vals)
    avg_hits = calculate_weighted_average(hits_vals)
    avg_errors = calculate_weighted_average(errors_vals)
    avg_batting_avg = calculate_weighted_average(avg_vals)
    avg_obp = calculate_weighted_average(obp_vals)
    avg_slg = calculate_weighted_average(slg_vals)
    avg_hr = calculate_weighted_average(hr_vals)
    avg_opp_hits = calculate_weighted_average(opp_hits_vals)
    avg_opp_errors = calculate_weighted_average(opp_errors_vals)
    
    # OPS = OBP + SLG (key offensive metric)
    avg_ops = avg_obp + avg_slg
    
    # recent form (last 10 games in baseball)
    recent_games = games[-10:] if len(games) >= 10 else games
    recent_wins = sum(1 for g in recent_games if g['result'] == 'W')
    recent_runs_scored = sum(g['runs_for'] for g in recent_games) / len(recent_games)
    recent_runs_allowed = sum(g['runs_against'] for g in recent_games) / len(recent_games)
    
    wins = sum(1 for g in games if g['result'] == 'W')
    
    # home/away splits
    home_games = [g for g in games if g['location'] == 'home']
    away_games = [g for g in games if g['location'] == 'away']
    home_wins = sum(1 for g in home_games if g['result'] == 'W')
    away_wins = sum(1 for g in away_games if g['result'] == 'W')
    home_win_rate = home_wins / len(home_games) if home_games else 0.5
    away_win_rate = away_wins / len(away_games) if away_games else 0.5
    
    # pythagorean expectation for baseball (exponent ~1.83)
    total_runs_scored = sum(runs_scored_vals)
    total_runs_allowed = sum(runs_allowed_vals)
    pythagorean_exp = (total_runs_scored ** 1.83) / ((total_runs_scored ** 1.83) + (total_runs_allowed ** 1.83))
    
    # run differential
    run_differential = avg_runs_scored - avg_runs_allowed
    
    return {
        'games_played': len(games),
        'wins': wins,
        'win_rate': wins / len(games),
        'pythagorean_win_rate': pythagorean_exp,
        'batting': {
            'runs_per_game': avg_runs_scored,
            'avg': avg_batting_avg,
            'obp': avg_obp,
            'slg': avg_slg,
            'ops': avg_ops,
            'hr_per_game': avg_hr,
            'hits_per_game': avg_hits
        },
        'pitching': {
            'runs_allowed_per_game': avg_runs_allowed,
            'hits_allowed_per_game': avg_opp_hits,
            'errors_per_game': avg_errors
        },
        'recent_form': {
            'wins': recent_wins,
            'games': len(recent_games),
            'win_rate': recent_wins / len(recent_games),
            'runs_scored': recent_runs_scored,
            'runs_allowed': recent_runs_allowed
        },
        'splits': {
            'home_win_rate': home_win_rate,
            'away_win_rate': away_win_rate,
            'home_advantage': home_win_rate - away_win_rate
        },
        'run_differential': run_differential
    }


def advanced_prediction(home_team, away_team, teams_data, injury_data=None, 
                       home_pitcher_name=None, away_pitcher_name=None):
    """
    advanced MLB prediction using batting/pitching matchup analysis
    with park factors, weather, and pitcher matchups
    """
    if teams_data is None:
        return None
    
    # check if teams exist
    if home_team not in teams_data:
        print(f"\nWARNING: {home_team} not found in data")
        return None
    if away_team not in teams_data:
        print(f"\nWARNING: {away_team} not found in data")
        return None
    
    # calculate team averages
    home_avg = calculate_team_averages(home_team, teams_data)
    away_avg = calculate_team_averages(away_team, teams_data)
    
    # get injury impact if available
    home_injury_impact = None
    away_injury_impact = None
    if injury_data:
        home_injury_impact = calculate_injury_impact(home_team, injury_data)
        away_injury_impact = calculate_injury_impact(away_team, injury_data)
    
    # get park factors
    park_info = None
    park_impact = 0.0
    if PARK_FACTORS_AVAILABLE:
        park_info = get_park_factor(home_team)
        park_impact = get_park_impact_score(home_team)
    
    # get weather
    weather_info = None
    weather_impact = 0.0
    weather_notes = []
    if WEATHER_AVAILABLE:
        weather_summary = get_weather_summary(home_team)
        weather_info = weather_summary['weather']
        weather_impact = weather_summary['impact']
        weather_notes = weather_summary['notes']
    
    # get starting pitcher stats
    home_pitcher_stats = None
    away_pitcher_stats = None
    if PITCHER_STATS_AVAILABLE and home_pitcher_name and away_pitcher_name:
        # For now, use sample data. In production, would fetch from API
        home_pitcher_stats = SAMPLE_PITCHERS.get(home_pitcher_name)
        away_pitcher_stats = SAMPLE_PITCHERS.get(away_pitcher_name)
    
    # get bullpen quality
    home_bullpen = None
    away_bullpen = None
    if PITCHER_STATS_AVAILABLE:
        home_bullpen = get_bullpen_stats(home_team, teams_data)
        away_bullpen = get_bullpen_stats(away_team, teams_data)
    
    if not home_avg or not away_avg:
        print("Not enough data for prediction")
        return None
    
    print(f"\n{'=' * 100}")
    print(f"DETAILED TEAM ANALYSIS")
    print(f"{'=' * 100}\n")
    
    # display team stats
    print(f"{home_team} (Home) - {home_avg['wins']}-{home_avg['games_played'] - home_avg['wins']} record:")
    print(f"  Batting: .{home_avg['batting']['avg']:.3f} AVG, .{home_avg['batting']['obp']:.3f} OBP, "
          f".{home_avg['batting']['slg']:.3f} SLG (.{home_avg['batting']['ops']:.3f} OPS)")
    print(f"    {home_avg['batting']['runs_per_game']:.1f} runs/game, {home_avg['batting']['hr_per_game']:.1f} HR/game")
    print(f"  Pitching: {home_avg['pitching']['runs_allowed_per_game']:.1f} runs allowed/game")
    print(f"  Recent Form (last {home_avg['recent_form']['games']} games): "
          f"{home_avg['recent_form']['wins']}-{home_avg['recent_form']['games'] - home_avg['recent_form']['wins']}")
    print(f"  Home/Away Split: {home_avg['splits']['home_win_rate']:.1%} home, "
          f"{home_avg['splits']['away_win_rate']:.1%} away")
    print(f"  Run Differential: {home_avg['run_differential']:+.1f} per game")
    print(f"  Pythagorean Win %: {home_avg['pythagorean_win_rate']:.1%} (Actual: {home_avg['win_rate']:.1%})")
    
    if home_injury_impact:
        print(f"  Injury Report: {home_injury_impact['total_injuries']} injuries")
        print(f"    Impact Score: {home_injury_impact['impact_score']:.1f}")
        if home_injury_impact['sp_injured']:
            print(f"    ⚠️  STARTING PITCHER INJURED")
        if home_injury_impact['injury_list']:
            print(f"    Key Injuries: {', '.join(home_injury_impact['injury_list'][:2])}")
    
    # Display park factors
    if park_info:
        print(f"  Park: {park_info['name']}")
        print(f"    Run Factor: {park_info['run_factor']} (100=neutral), Altitude: {park_info['altitude']}ft")
        print(f"    Impact: {park_impact:+.1f} points", end="")
        if park_impact > 3:
            print(" (EXTREME hitter park!)")
        elif park_impact > 1:
            print(" (Hitter-friendly)")
        elif park_impact < -2:
            print(" (Very pitcher-friendly)")
        elif park_impact < 0:
            print(" (Pitcher-friendly)")
        else:
            print(" (Neutral)")
    
    # Display weather
    if weather_info:
        print(f"  Weather: {weather_info['temp_f']}°F, Wind: {weather_info['wind_speed_mph']} mph {weather_info['wind_dir']}")
        print(f"    Condition: {weather_info['condition']}")
        print(f"    Impact: {weather_impact:+.1f} points - {', '.join(weather_notes)}")
    
    print()
    
    print(f"{away_team} (Away) - {away_avg['wins']}-{away_avg['games_played'] - away_avg['wins']} record:")
    print(f"  Batting: .{away_avg['batting']['avg']:.3f} AVG, .{away_avg['batting']['obp']:.3f} OBP, "
          f".{away_avg['batting']['slg']:.3f} SLG (.{away_avg['batting']['ops']:.3f} OPS)")
    print(f"    {away_avg['batting']['runs_per_game']:.1f} runs/game, {away_avg['batting']['hr_per_game']:.1f} HR/game")
    print(f"  Pitching: {away_avg['pitching']['runs_allowed_per_game']:.1f} runs allowed/game")
    print(f"  Recent Form (last {away_avg['recent_form']['games']} games): "
          f"{away_avg['recent_form']['wins']}-{away_avg['recent_form']['games'] - away_avg['recent_form']['wins']}")
    print(f"  Home/Away Split: {away_avg['splits']['home_win_rate']:.1%} home, "
          f"{away_avg['splits']['away_win_rate']:.1%} away")
    print(f"  Run Differential: {away_avg['run_differential']:+.1f} per game")
    print(f"  Pythagorean Win %: {away_avg['pythagorean_win_rate']:.1%} (Actual: {away_avg['win_rate']:.1%})")
    
    if away_injury_impact:
        print(f"  Injury Report: {away_injury_impact['total_injuries']} injuries")
        print(f"    Impact Score: {away_injury_impact['impact_score']:.1f}")
        if away_injury_impact['sp_injured']:
            print(f"    ⚠️  STARTING PITCHER INJURED")
        if away_injury_impact['injury_list']:
            print(f"    Key Injuries: {', '.join(away_injury_impact['injury_list'][:2])}")
    print()
    
    # MATCHUP ANALYSIS
    print(f"{'=' * 100}")
    print(f"MATCHUP ANALYSIS")
    print(f"{'=' * 100}\n")
    
    home_points = 0
    away_points = 0
    
    # *** MOST IMPORTANT: STARTING PITCHER MATCHUP ***
    if home_pitcher_stats and away_pitcher_stats and PITCHER_STATS_AVAILABLE:
        print(f"🎯 STARTING PITCHER MATCHUP (MOST CRITICAL):")
        print(f"  Home: {home_pitcher_name}")
        if home_pitcher_stats:
            print(f"    ERA: {home_pitcher_stats['era']:.2f}, WHIP: {home_pitcher_stats['whip']:.2f}, "
                  f"Record: {home_pitcher_stats['wins']}-{home_pitcher_stats['losses']}")
            home_p_score = calculate_pitcher_quality_score(home_pitcher_stats)
            print(f"    Quality Score: {home_p_score}/100")
        
        print(f"  Away: {away_pitcher_name}")
        if away_pitcher_stats:
            print(f"    ERA: {away_pitcher_stats['era']:.2f}, WHIP: {away_pitcher_stats['whip']:.2f}, "
                  f"Record: {away_pitcher_stats['wins']}-{away_pitcher_stats['losses']}")
            away_p_score = calculate_pitcher_quality_score(away_pitcher_stats)
            print(f"    Quality Score: {away_p_score}/100")
        
        pitcher_points, pitcher_note = compare_pitchers(home_pitcher_stats, away_pitcher_stats)
        if pitcher_points > 0:
            home_points += pitcher_points
            print(f"  >> {pitcher_note} ({pitcher_points:+.1f} to {home_team})")
        elif pitcher_points < 0:
            away_points += abs(pitcher_points)
            print(f"  >> {pitcher_note} ({abs(pitcher_points):+.1f} to {away_team})")
        else:
            print(f"  >> {pitcher_note}")
        print()
    elif home_pitcher_name or away_pitcher_name:
        print(f"⚠️  Starting Pitcher Info:")
        if home_pitcher_name:
            print(f"  Home: {home_pitcher_name} (stats not available)")
        if away_pitcher_name:
            print(f"  Away: {away_pitcher_name} (stats not available)")
        print(f"  Note: Pitcher matchup is the #1 factor in baseball!")
        print()
    
    # Bullpen Quality Comparison
    if home_bullpen and away_bullpen:
        print(f"Bullpen Quality:")
        print(f"  {home_team}: Score {home_bullpen['quality_score']}/100 (Est. ERA: {home_bullpen['era']:.2f})")
        print(f"  {away_team}: Score {away_bullpen['quality_score']}/100 (Est. ERA: {away_bullpen['era']:.2f})")
        
        bullpen_diff = home_bullpen['quality_score'] - away_bullpen['quality_score']
        if bullpen_diff >= 20:
            home_points += 2.0
            print(f"    >> {home_team} bullpen significantly better (+2.0)")
        elif bullpen_diff >= 10:
            home_points += 1.0
            print(f"    >> {home_team} bullpen better (+1.0)")
        elif bullpen_diff <= -20:
            away_points += 2.0
            print(f"    >> {away_team} bullpen significantly better (+2.0)")
        elif bullpen_diff <= -10:
            away_points += 1.0
            print(f"    >> {away_team} bullpen better (+1.0)")
        print()
    
    # Park Factor Impact
    if park_info:
        print(f"Park Factor - {park_info['name']}:")
        print(f"  Run Factor: {park_info['run_factor']} (100=neutral)")
        print(f"  Impact: {park_impact:+.1f} points")
        if park_impact > 0:
            # Hitter-friendly park helps BOTH teams, but slightly favors home team familiarity
            home_points += park_impact * 0.6
            away_points += park_impact * 0.4
            print(f"    >> Hitter-friendly park: {home_team} +{park_impact * 0.6:.1f}, {away_team} +{park_impact * 0.4:.1f}")
        elif park_impact < 0:
            # Pitcher-friendly park helps BOTH teams, slightly favors home pitchers
            home_points += abs(park_impact) * 0.3
            print(f"    >> Pitcher-friendly park: Slight advantage to home pitchers (+{abs(park_impact) * 0.3:.1f})")
        print()
    
    # Weather Impact
    if weather_info:
        print(f"Weather Conditions:")
        print(f"  Temp: {weather_info['temp_f']}°F, Wind: {weather_info['wind_speed_mph']} mph {weather_info['wind_dir']}")
        print(f"  Impact: {weather_impact:+.1f} points")
        for note in weather_notes:
            print(f"    • {note}")
        if weather_impact > 0:
            # Good hitting weather helps both teams slightly more for home
            home_points += weather_impact * 0.6
            away_points += weather_impact * 0.4
            print(f"    >> Adds: {home_team} +{weather_impact * 0.6:.1f}, {away_team} +{weather_impact * 0.4:.1f}")
        elif weather_impact < 0:
            # Bad hitting weather (wind in, cold) helps pitchers
            home_points += abs(weather_impact) * 0.3
            print(f"    >> Helps pitchers: +{abs(weather_impact) * 0.3:.1f} to {home_team}")
        print()
    
    # 1. Batting vs Pitching Matchup
    print(f"Batting vs Pitching Matchup:")
    home_bat_vs_away_pitch = home_avg['batting']['ops'] / (away_avg['pitching']['runs_allowed_per_game'] / 4.5 + 0.1)
    away_bat_vs_home_pitch = away_avg['batting']['ops'] / (home_avg['pitching']['runs_allowed_per_game'] / 4.5 + 0.1)
    
    print(f"  {home_team} batting (OPS: {home_avg['batting']['ops']:.3f}) vs {away_team} pitching:")
    if home_bat_vs_away_pitch > 1.15:
        home_points += 3.0
        print(f"    >> Strong offensive advantage for {home_team} (+3.0)")
    elif home_bat_vs_away_pitch > 1.05:
        home_points += 1.5
        print(f"    >> Moderate advantage for {home_team} (+1.5)")
    elif home_bat_vs_away_pitch < 0.90:
        away_points += 2.0
        print(f"    >> {away_team} pitching dominates (+2.0)")
    
    print(f"  {away_team} batting (OPS: {away_avg['batting']['ops']:.3f}) vs {home_team} pitching:")
    if away_bat_vs_home_pitch > 1.15:
        away_points += 3.0
        print(f"    >> Strong offensive advantage for {away_team} (+3.0)")
    elif away_bat_vs_home_pitch > 1.05:
        away_points += 1.5
        print(f"    >> Moderate advantage for {away_team} (+1.5)")
    elif away_bat_vs_home_pitch < 0.90:
        home_points += 2.0
        print(f"    >> {home_team} pitching dominates (+2.0)")
    
    # 2. Run Production
    print(f"\nRun Production:")
    if home_avg['batting']['runs_per_game'] > away_avg['batting']['runs_per_game'] + 1.0:
        home_points += 2.0
        print(f"  {home_team} significantly outscores opponents (+2.0)")
    elif away_avg['batting']['runs_per_game'] > home_avg['batting']['runs_per_game'] + 1.0:
        away_points += 2.0
        print(f"  {away_team} significantly outscores opponents (+2.0)")
    
    # 3. Power Hitting (HR)
    print(f"\nPower Hitting:")
    if home_avg['batting']['hr_per_game'] > away_avg['batting']['hr_per_game'] + 0.5:
        home_points += 1.0
        print(f"  {home_team} has power advantage (+1.0)")
    elif away_avg['batting']['hr_per_game'] > home_avg['batting']['hr_per_game'] + 0.5:
        away_points += 1.0
        print(f"  {away_team} has power advantage (+1.0)")
    
    # 4. Recent Form / Momentum
    print(f"\nRecent Form (Last 10 Games):")
    home_momentum = home_avg['recent_form']['win_rate']
    away_momentum = away_avg['recent_form']['win_rate']
    
    if home_momentum >= 0.70:
        home_points += 2.0
        print(f"  {home_team} is HOT ({home_avg['recent_form']['wins']}-{home_avg['recent_form']['games'] - home_avg['recent_form']['wins']}) (+2.0)")
    elif home_momentum >= 0.60:
        home_points += 1.0
        print(f"  {home_team} has momentum (+1.0)")
    elif home_momentum <= 0.30:
        away_points += 1.5
        print(f"  {home_team} struggling (+1.5 to {away_team})")
    
    if away_momentum >= 0.70:
        away_points += 2.0
        print(f"  {away_team} is HOT ({away_avg['recent_form']['wins']}-{away_avg['recent_form']['games'] - away_avg['recent_form']['wins']}) (+2.0)")
    elif away_momentum >= 0.60:
        away_points += 1.0
        print(f"  {away_team} has momentum (+1.0)")
    elif away_momentum <= 0.30:
        home_points += 1.5
        print(f"  {away_team} struggling (+1.5 to {home_team})")
    
    # 5. Home Field Advantage (BIGGER in MLB)
    print(f"\nHome Field Advantage:")
    home_advantage_strength = home_avg['splits']['home_advantage']
    
    if home_advantage_strength > 0.20:
        hfa_points = 3.5
        print(f"  {home_team} has DOMINANT home advantage (+3.5)")
    elif home_advantage_strength > 0.10:
        hfa_points = 2.5
        print(f"  {home_team} has STRONG home advantage (+2.5)")
    else:
        hfa_points = 2.0
        print(f"  {home_team} has standard home advantage (+2.0)")
    
    print(f"  ({home_avg['splits']['home_win_rate']:.1%} home vs {home_avg['splits']['away_win_rate']:.1%} away)")
    home_points += hfa_points
    
    # 6. Win Rate Factor (reduced weight)
    print(f"\nWin Rate:")
    home_win_pts = home_avg['win_rate'] * 3.0
    away_win_pts = away_avg['win_rate'] * 3.0
    home_points += home_win_pts
    away_points += away_win_pts
    print(f"  {home_team}: +{home_win_pts:.1f} ({home_avg['win_rate']:.1%})")
    print(f"  {away_team}: +{away_win_pts:.1f} ({away_avg['win_rate']:.1%})")
    
    # 7. Pythagorean Expectation
    print(f"\nPythagorean Analysis:")
    home_pyth_diff = home_avg['win_rate'] - home_avg['pythagorean_win_rate']
    away_pyth_diff = away_avg['win_rate'] - away_avg['pythagorean_win_rate']
    
    if home_pyth_diff > 0.10:
        home_points -= 1.0
        print(f"  {home_team} overperforming, regression risk (-1.0)")
    elif home_pyth_diff < -0.10:
        home_points += 1.0
        print(f"  {home_team} underperforming, bounce-back candidate (+1.0)")
    
    if away_pyth_diff > 0.10:
        away_points -= 1.0
        print(f"  {away_team} overperforming, regression risk (-1.0)")
    elif away_pyth_diff < -0.10:
        away_points += 1.0
        print(f"  {away_team} underperforming, bounce-back candidate (+1.0)")
    
    # 8. Run Differential
    print(f"\nRun Differential:")
    if home_avg['run_differential'] > away_avg['run_differential'] + 1.0:
        home_points += 1.5
        print(f"  {home_team} significantly better run differential (+1.5)")
    elif away_avg['run_differential'] > home_avg['run_differential'] + 1.0:
        away_points += 1.5
        print(f"  {away_team} significantly better run differential (+1.5)")
    
    # 9. Injury Impact (if available)
    if home_injury_impact and away_injury_impact:
        print(f"\nInjury Impact:")
        print(f"  {home_team}: {home_injury_impact['impact_score']:.1f}")
        if home_injury_impact['sp_injured']:
            print(f"    ⚠️  Starting Pitcher injured")
        print(f"  {away_team}: {away_injury_impact['impact_score']:.1f}")
        if away_injury_impact['sp_injured']:
            print(f"    ⚠️  Starting Pitcher injured")
        
        # Starting pitcher injuries are HUGE in baseball
        if home_injury_impact['sp_injured'] and not away_injury_impact['sp_injured']:
            away_points += 4.0
            print(f"    >> {home_team} starting pitcher injured, major advantage to {away_team} (+4.0)")
        elif away_injury_impact['sp_injured'] and not home_injury_impact['sp_injured']:
            home_points += 4.0
            print(f"    >> {away_team} starting pitcher injured, major advantage to {home_team} (+4.0)")
        
        # General injury comparison
        impact_diff = away_injury_impact['impact_score'] - home_injury_impact['impact_score']
        if abs(impact_diff) > 5.0 and not (home_injury_impact['sp_injured'] or away_injury_impact['sp_injured']):
            if impact_diff > 0:
                home_points += 2.0
                print(f"    >> {away_team} more injured (+2.0 to {home_team})")
            else:
                away_points += 2.0
                print(f"    >> {home_team} more injured (+2.0 to {away_team})")
    
    return {
        'home_points': home_points,
        'away_points': away_points,
        'home_stats': home_avg,
        'away_stats': away_avg
    }


def main():
    """
    main function
    """
    print("=" * 100)
    print("MLB Game Predictor - Advanced Analysis")
    print("=" * 100)
    print("\nReading MLB data...")
    
    # read and parse data
    teams_data = read_mlb_data()
    
    if teams_data is None:
        print("Failed to load data. Exiting.")
        return
    
    print(f"Data loaded successfully! Found {len(teams_data)} teams.\n")
    
    # fetch current injury data
    injury_data = None
    if INJURIES_AVAILABLE:
        print("Fetching current injury reports...")
        try:
            injury_data = get_injury_data()
            if injury_data:
                total_injuries = sum(len(injuries) for injuries in injury_data.values())
                print(f"Injury data loaded! {total_injuries} total injuries.\n")
            else:
                print("Could not fetch injury data. Proceeding without injury analysis.\n")
        except Exception as e:
            print(f"Error loading injury data: {e}")
            print("Proceeding without injury analysis.\n")
    else:
        print("Injury module not available. Proceeding without injury analysis.\n")
    
    # get user input
    print("Enter team names (use full names as they appear in mlbData.txt)")
    print("Examples: 'New York Yankees', 'Los Angeles Dodgers', etc.\n")
    
    home_team = input("Enter HOME team: ").strip()
    away_team = input("Enter AWAY team: ").strip()
    
    # Get starting pitchers (CRITICAL for accuracy!)
    print("\n⚠️  IMPORTANT: Starting pitcher is the #1 factor in baseball predictions!")
    print("For best accuracy, enter starting pitcher names (or press Enter to skip)")
    print("Sample pitchers available: 'Gerrit Cole', 'Average Pitcher', 'Weak Pitcher'\n")
    
    home_pitcher = input(f"Enter {home_team} STARTING PITCHER (or press Enter): ").strip()
    away_pitcher = input(f"Enter {away_team} STARTING PITCHER (or press Enter): ").strip()
    
    if not home_pitcher:
        home_pitcher = None
    if not away_pitcher:
        away_pitcher = None
    
    if not home_pitcher or not away_pitcher:
        print("\n⚠️  Warning: Starting pitcher not provided. Prediction accuracy will be reduced!")
        print("Starting pitcher matchup typically accounts for +10% accuracy.\n")
    
    # predict the game
    result = advanced_prediction(home_team, away_team, teams_data, injury_data, home_pitcher, away_pitcher)
    
    if result:
        home_points = result['home_points']
        away_points = result['away_points']
        
        print(f"\n{'=' * 100}")
        print(f"FINAL PREDICTION")
        print(f"{'=' * 100}\n")
        
        print(f"{home_team}: {home_points:.1f} points")
        print(f"{away_team}: {away_points:.1f} points\n")
        
        if home_points > away_points:
            diff = home_points - away_points
            confidence = min(diff / 5 * 100, 92)
            print(f"PREDICTION: {home_team} wins")
            print(f"Confidence: {confidence:.0f}%")
        elif away_points > home_points:
            diff = away_points - home_points
            confidence = min(diff / 5 * 100, 92)
            print(f"PREDICTION: {away_team} wins")
            print(f"Confidence: {confidence:.0f}%")
        else:
            print("PREDICTION: Too close to call")
            print("Confidence: 50%")
        
        print(f"{'=' * 100}")


if __name__ == "__main__":
    main()

