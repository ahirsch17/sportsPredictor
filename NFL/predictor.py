"""
NFL Game Predictor - Advanced Analysis
Analyzes detailed game stats to predict outcomes with contextual matchup analysis
"""

# Import injury data functions
try:
    from injuryextract import get_injury_data, calculate_injury_impact
    INJURIES_AVAILABLE = True
except ImportError:
    INJURIES_AVAILABLE = False
    print("WARNING: Injury data module not available")


def parse_stat(stat_str, stat_type='int'):
    """
    safely parse stat string to number
    """
    try:
        if stat_type == 'int':
            return int(stat_str.replace(',', ''))
        elif stat_type == 'float':
            return float(stat_str.replace(',', ''))
        elif stat_type == 'time':
            # parse time like "30:15" to minutes
            parts = stat_str.split(':')
            return int(parts[0]) + int(parts[1]) / 60.0
        elif stat_type == 'ratio':
            # parse like "5-12" to success rate
            parts = stat_str.split('-')
            if len(parts) == 2 and int(parts[1]) > 0:
                return int(parts[0]) / int(parts[1])
            return 0.0
        elif stat_type == 'completion':
            # parse like "15/23" to completion percentage
            parts = stat_str.split('/')
            if len(parts) == 2 and int(parts[1]) > 0:
                return int(parts[0]) / int(parts[1])
            return 0.0
    except:
        return 0 if stat_type not in ['ratio', 'completion'] else 0.0


def read_nfl_data():
    """
    reads nflData.txt with detailed stats and parses into structured format
    """
    teams_data = {}
    
    try:
        with open('nflData.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        i = 0
        current_week = None
        is_preseason = False
        
        while i < len(lines):
            line = lines[i].strip()
            
            # detect week header (lines that contain WEEK but not brackets)
            if ('PRESEASON_WEEK' in line or 'REGULAR_WEEK' in line) and '[' not in line:
                current_week = line
                is_preseason = 'PRESEASON' in line
                i += 1
                continue
            
            # parse game line
            if line.startswith('[') and '@' in line and '|' in line:
                try:
                    # extract basic game info
                    week_part = line[line.find('[')+1:line.find(']')]
                    game_part = line[line.find(']')+1:].strip()
                    teams_part = game_part.split('|')[0].strip()
                    scores_part = game_part.split('|')[1].strip()
                    
                    away_team, home_team = teams_part.split('@')
                    away_team = away_team.strip()
                    home_team = home_team.strip()
                    
                    away_score, home_score = scores_part.split('-')
                    away_score = int(away_score.strip())
                    home_score = int(home_score.strip())
                    
                    # parse detailed stats from next lines
                    away_stats = {}
                    home_stats = {}
                    away_qb_stats = {}
                    home_qb_stats = {}
                    
                    # Check for QB stats (new format)
                    peek_idx = i + 1
                    if peek_idx < len(lines) and 'AWAY QB' in lines[peek_idx]:
                        # Parse AWAY QB line: "  AWAY QB (Name): 17/34 for 204yds, 1TD/3INT, 6.0 YPA, 41.8 RTG"
                        qb_line = lines[peek_idx].strip()
                        try:
                            qb_name = qb_line.split('(')[1].split(')')[0]
                            qb_data = qb_line.split('):')[1].strip()
                            parts = qb_data.split(',')
                            
                            # comp/att for yards
                            comp_att = parts[0].split('for')[0].strip()
                            yards = parts[0].split('for')[1].replace('yds', '').strip()
                            
                            # TDs/INTs
                            td_int = parts[1].strip().split('/')
                            tds = td_int[0].replace('TD', '').strip()
                            ints = td_int[1].replace('INT', '').strip()
                            
                            # YPA
                            ypa = parts[2].replace('YPA', '').strip()
                            
                            # QB Rating
                            rating = parts[3].replace('RTG', '').strip() if len(parts) > 3 else '0.0'
                            
                            away_qb_stats = {
                                'comp_att': comp_att,
                                'yards': int(yards),
                                'tds': int(tds),
                                'ints': int(ints),
                                'ypa': float(ypa),
                                'rating': float(rating)
                            }
                        except:
                            pass
                        i += 1
                    
                    if peek_idx + 1 < len(lines) and 'HOME QB' in lines[peek_idx + 1]:
                        # Parse HOME QB line
                        qb_line = lines[peek_idx + 1].strip()
                        try:
                            qb_name = qb_line.split('(')[1].split(')')[0]
                            qb_data = qb_line.split('):')[1].strip()
                            parts = qb_data.split(',')
                            
                            # comp/att for yards
                            comp_att = parts[0].split('for')[0].strip()
                            yards = parts[0].split('for')[1].replace('yds', '').strip()
                            
                            # TDs/INTs
                            td_int = parts[1].strip().split('/')
                            tds = td_int[0].replace('TD', '').strip()
                            ints = td_int[1].replace('INT', '').strip()
                            
                            # YPA
                            ypa = parts[2].replace('YPA', '').strip()
                            
                            # QB Rating
                            rating = parts[3].replace('RTG', '').strip() if len(parts) > 3 else '0.0'
                            
                            home_qb_stats = {
                                'comp_att': comp_att,
                                'yards': int(yards),
                                'tds': int(tds),
                                'ints': int(ints),
                                'ypa': float(ypa),
                                'rating': float(rating)
                            }
                        except:
                            pass
                        i += 1
                    
                    # look ahead for AWAY stats (now 4 lines instead of 3)
                    if i + 1 < len(lines) and 'AWAY' in lines[i + 1]:
                        i += 2  # skip "AWAY (team):" line
                        
                        # Line 1: parse away yards line
                        if i < len(lines):
                            stats_line = lines[i].strip()
                            if 'Total Yards:' in stats_line:
                                parts = stats_line.split('|')
                                for part in parts:
                                    if 'Total Yards:' in part:
                                        away_stats['totalYards'] = parse_stat(part.split(':')[1].strip())
                                    elif 'Yards/Play:' in part:
                                        away_stats['yardsPerPlay'] = parse_stat(part.split(':')[1].strip(), 'float')
                                    elif 'Possession:' in part:
                                        away_stats['possession'] = parse_stat(part.split(':')[1].strip(), 'time')
                            i += 1
                        
                        # Line 2: parse away passing/rushing line (with completion % and rush avg)
                        if i < len(lines):
                            stats_line = lines[i].strip()
                            if 'Passing:' in stats_line:
                                parts = stats_line.split('|')
                                for part in parts:
                                    if 'Passing:' in part:
                                        # Extract "198yds (17/34)" -> passingYards=198, completion=17/34
                                        pass_data = part.split(':')[1].strip()
                                        if '(' in pass_data:
                                            yds_part = pass_data.split('(')[0].replace('yds', '').strip()
                                            comp_part = pass_data.split('(')[1].replace(')', '').strip()
                                            away_stats['passingYards'] = parse_stat(yds_part)
                                            away_stats['completionRate'] = parse_stat(comp_part, 'completion')
                                        else:
                                            away_stats['passingYards'] = parse_stat(pass_data.replace('yds', '').strip())
                                    elif 'Rushing:' in part:
                                        # Extract "140yds (7.8 avg)" -> rushingYards=140, rushAvg=7.8
                                        rush_data = part.split(':')[1].strip()
                                        if '(' in rush_data:
                                            yds_part = rush_data.split('(')[0].replace('yds', '').strip()
                                            avg_part = rush_data.split('(')[1].replace('avg', '').replace(')', '').strip()
                                            away_stats['rushingYards'] = parse_stat(yds_part)
                                            away_stats['rushingAvg'] = parse_stat(avg_part, 'float')
                                        else:
                                            away_stats['rushingYards'] = parse_stat(rush_data.replace('yds', '').strip())
                                    elif '1st Downs:' in part:
                                        away_stats['firstDowns'] = parse_stat(part.split(':')[1].strip())
                            i += 1
                        
                        # Line 3: parse away efficiency line (3rd down, 4th down, red zone)
                        if i < len(lines):
                            stats_line = lines[i].strip()
                            if '3rd Down:' in stats_line or '4th Down:' in stats_line:
                                parts = stats_line.split('|')
                                for part in parts:
                                    if '3rd Down:' in part:
                                        away_stats['thirdDownRate'] = parse_stat(part.split(':')[1].strip(), 'ratio')
                                    elif '4th Down:' in part:
                                        away_stats['fourthDownRate'] = parse_stat(part.split(':')[1].strip(), 'ratio')
                                    elif 'Red Zone:' in part:
                                        away_stats['redZoneRate'] = parse_stat(part.split(':')[1].strip(), 'ratio')
                            i += 1
                        
                        # Line 4: parse turnovers, sacks, penalties
                        if i < len(lines):
                            stats_line = lines[i].strip()
                            if 'Turnovers:' in stats_line:
                                parts = stats_line.split('|')
                                for part in parts:
                                    if 'Turnovers:' in part:
                                        # Extract "3 (INT: 2, Fum: 1)" -> turnovers=3, ints=2, fumbles=1
                                        to_data = part.split(':')[1].strip()
                                        if '(' in to_data:
                                            total_to = to_data.split('(')[0].strip()
                                            away_stats['turnovers'] = parse_stat(total_to)
                                            # Parse INT and Fum
                                            detail = to_data.split('(')[1].replace(')', '')
                                            if 'INT:' in detail:
                                                int_val = detail.split('INT:')[1].split(',')[0].strip()
                                                away_stats['interceptions'] = parse_stat(int_val)
                                            if 'Fum:' in detail:
                                                fum_val = detail.split('Fum:')[1].strip()
                                                away_stats['fumbles'] = parse_stat(fum_val)
                                        else:
                                            away_stats['turnovers'] = parse_stat(to_data)
                                    elif 'Sacks:' in part and 'Sacks-' not in part:
                                        away_stats['sacks'] = parse_stat(part.split(':')[1].strip())
                                    elif 'Penalties:' in part:
                                        away_stats['penalties'] = parse_stat(part.split(':')[1].strip(), 'ratio')
                            i += 1
                    
                    # look ahead for HOME stats (now 4 lines instead of 3)
                    if i < len(lines) and 'HOME' in lines[i]:
                        i += 1  # skip "HOME (team):" line
                        
                        # Line 1: parse home yards line
                        if i < len(lines):
                            stats_line = lines[i].strip()
                            if 'Total Yards:' in stats_line:
                                parts = stats_line.split('|')
                                for part in parts:
                                    if 'Total Yards:' in part:
                                        home_stats['totalYards'] = parse_stat(part.split(':')[1].strip())
                                    elif 'Yards/Play:' in part:
                                        home_stats['yardsPerPlay'] = parse_stat(part.split(':')[1].strip(), 'float')
                                    elif 'Possession:' in part:
                                        home_stats['possession'] = parse_stat(part.split(':')[1].strip(), 'time')
                            i += 1
                        
                        # Line 2: parse home passing/rushing line (with completion % and rush avg)
                        if i < len(lines):
                            stats_line = lines[i].strip()
                            if 'Passing:' in stats_line:
                                parts = stats_line.split('|')
                                for part in parts:
                                    if 'Passing:' in part:
                                        # Extract "198yds (17/34)" -> passingYards=198, completion=17/34
                                        pass_data = part.split(':')[1].strip()
                                        if '(' in pass_data:
                                            yds_part = pass_data.split('(')[0].replace('yds', '').strip()
                                            comp_part = pass_data.split('(')[1].replace(')', '').strip()
                                            home_stats['passingYards'] = parse_stat(yds_part)
                                            home_stats['completionRate'] = parse_stat(comp_part, 'completion')
                                        else:
                                            home_stats['passingYards'] = parse_stat(pass_data.replace('yds', '').strip())
                                    elif 'Rushing:' in part:
                                        # Extract "140yds (7.8 avg)" -> rushingYards=140, rushAvg=7.8
                                        rush_data = part.split(':')[1].strip()
                                        if '(' in rush_data:
                                            yds_part = rush_data.split('(')[0].replace('yds', '').strip()
                                            avg_part = rush_data.split('(')[1].replace('avg', '').replace(')', '').strip()
                                            home_stats['rushingYards'] = parse_stat(yds_part)
                                            home_stats['rushingAvg'] = parse_stat(avg_part, 'float')
                                        else:
                                            home_stats['rushingYards'] = parse_stat(rush_data.replace('yds', '').strip())
                                    elif '1st Downs:' in part:
                                        home_stats['firstDowns'] = parse_stat(part.split(':')[1].strip())
                            i += 1
                        
                        # Line 3: parse home efficiency line (3rd down, 4th down, red zone)
                        if i < len(lines):
                            stats_line = lines[i].strip()
                            if '3rd Down:' in stats_line or '4th Down:' in stats_line:
                                parts = stats_line.split('|')
                                for part in parts:
                                    if '3rd Down:' in part:
                                        home_stats['thirdDownRate'] = parse_stat(part.split(':')[1].strip(), 'ratio')
                                    elif '4th Down:' in part:
                                        home_stats['fourthDownRate'] = parse_stat(part.split(':')[1].strip(), 'ratio')
                                    elif 'Red Zone:' in part:
                                        home_stats['redZoneRate'] = parse_stat(part.split(':')[1].strip(), 'ratio')
                            i += 1
                        
                        # Line 4: parse turnovers, sacks, penalties
                        if i < len(lines):
                            stats_line = lines[i].strip()
                            if 'Turnovers:' in stats_line:
                                parts = stats_line.split('|')
                                for part in parts:
                                    if 'Turnovers:' in part:
                                        # Extract "3 (INT: 2, Fum: 1)" -> turnovers=3, ints=2, fumbles=1
                                        to_data = part.split(':')[1].strip()
                                        if '(' in to_data:
                                            total_to = to_data.split('(')[0].strip()
                                            home_stats['turnovers'] = parse_stat(total_to)
                                            # Parse INT and Fum
                                            detail = to_data.split('(')[1].replace(')', '')
                                            if 'INT:' in detail:
                                                int_val = detail.split('INT:')[1].split(',')[0].strip()
                                                home_stats['interceptions'] = parse_stat(int_val)
                                            if 'Fum:' in detail:
                                                fum_val = detail.split('Fum:')[1].strip()
                                                home_stats['fumbles'] = parse_stat(fum_val)
                                        else:
                                            home_stats['turnovers'] = parse_stat(to_data)
                                    elif 'Sacks:' in part and 'Sacks-' not in part:
                                        home_stats['sacks'] = parse_stat(part.split(':')[1].strip())
                                    elif 'Penalties:' in part:
                                        home_stats['penalties'] = parse_stat(part.split(':')[1].strip(), 'ratio')
                            i += 1
                    
                    # determine winner and create game records
                    if away_score > home_score:
                        # away team won
                        point_diff = away_score - home_score
                        
                        if away_team not in teams_data:
                            teams_data[away_team] = []
                        teams_data[away_team].append({
                            'opponent': home_team,
                            'location': 'away',
                            'result': 'W',
                            'score_for': away_score,
                            'score_against': home_score,
                            'point_diff': point_diff,
                            'preseason': is_preseason,
                            'off_stats': away_stats,
                            'def_stats': home_stats,  # opponent's offense = our defense faced
                            'qb_stats': away_qb_stats  # ACTUAL QB stats
                        })
                        
                        if home_team not in teams_data:
                            teams_data[home_team] = []
                        teams_data[home_team].append({
                            'opponent': away_team,
                            'location': 'home',
                            'result': 'L',
                            'score_for': home_score,
                            'score_against': away_score,
                            'point_diff': point_diff,
                            'preseason': is_preseason,
                            'off_stats': home_stats,
                            'def_stats': away_stats,
                            'qb_stats': home_qb_stats  # ACTUAL QB stats
                        })
                    
                    elif home_score > away_score:
                        # home team won
                        point_diff = home_score - away_score
                        
                        if home_team not in teams_data:
                            teams_data[home_team] = []
                        teams_data[home_team].append({
                            'opponent': away_team,
                            'location': 'home',
                            'result': 'W',
                            'score_for': home_score,
                            'score_against': away_score,
                            'point_diff': point_diff,
                            'preseason': is_preseason,
                            'off_stats': home_stats,
                            'def_stats': away_stats,
                            'qb_stats': home_qb_stats  # ACTUAL QB stats
                        })
                        
                        if away_team not in teams_data:
                            teams_data[away_team] = []
                        teams_data[away_team].append({
                            'opponent': home_team,
                            'location': 'away',
                            'result': 'L',
                            'score_for': away_score,
                            'score_against': home_score,
                            'point_diff': point_diff,
                            'preseason': is_preseason,
                            'off_stats': away_stats,
                            'def_stats': home_stats,
                            'qb_stats': away_qb_stats  # ACTUAL QB stats
                        })
                
                except Exception as e:
                    print(f"Error parsing game: {e}")
                    i += 1
                    continue
            
            i += 1
    
    except FileNotFoundError:
        print("ERROR: nflData.txt not found. Please run dataextract.py first.")
        return None
    
    return teams_data


def calculate_weighted_average(values, use_recency_weighting=True):
    """
    calculates weighted average with exponential recency weighting
    recent games weighted at ~65%, earlier games at ~35%
    """
    if not values:
        return 0
    
    if not use_recency_weighting or len(values) <= 3:
        return sum(values) / len(values)
    
    # exponential weights: more recent = higher weight
    weights = []
    total_weight = 0
    for i in range(len(values)):
        # exponential decay: recent games get 2.5x weight of oldest games
        weight = 1.0 * (1.5 ** (i / len(values)))
        weights.append(weight)
        total_weight += weight
    
    # normalize weights
    weights = [w / total_weight for w in weights]
    
    # calculate weighted sum
    weighted_sum = sum(v * w for v, w in zip(values, weights))
    return weighted_sum


def calculate_league_stats(teams_data, stat_name, stat_category='offense'):
    """
    calculates league-wide mean and standard deviation for a stat
    """
    values = []
    for team in teams_data.keys():
        team_avg = calculate_team_averages(team, teams_data)
        if team_avg:
            if stat_category == 'offense':
                val = team_avg['offense'].get(stat_name, 0)
            elif stat_category == 'defense':
                val = team_avg['defense'].get(stat_name, 0)
            else:
                val = team_avg.get(stat_name, 0)
            values.append(val)
    
    if not values:
        return {'mean': 0, 'std': 1}
    
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    std = variance ** 0.5
    
    return {'mean': mean, 'std': max(std, 1e-6)}  # prevent division by zero


def opponent_adjusted_z_score(team_val, opponent_val, league_mean, league_std, alpha=0.3):
    """
    calculates opponent-adjusted z-score
    alpha controls how much we shrink toward opponent average (0.3 = moderate adjustment)
    """
    # adjust team value by opponent quality
    adjusted_val = team_val - (opponent_val - league_mean) * alpha
    
    # convert to z-score
    z_score = (adjusted_val - league_mean) / max(league_std, 1e-6)
    
    return z_score


def calculate_team_averages(team, teams_data, regular_only=True):
    """
    calculates average offensive and defensive stats for a team
    includes run/pass breakdown, recent form analysis, and recency weighting
    """
    if team not in teams_data:
        return None
    
    games = teams_data[team]
    if regular_only:
        games = [g for g in games if not g['preseason']]
    
    if not games:
        return None
    
    # extract values for weighted averaging
    yards_per_play_vals = [g['off_stats'].get('yardsPerPlay', 0) for g in games]
    total_yards_vals = [g['off_stats'].get('totalYards', 0) for g in games]
    points_scored_vals = [g['score_for'] for g in games]
    third_down_vals = [g['off_stats'].get('thirdDownRate', 0) for g in games]
    fourth_down_vals = [g['off_stats'].get('fourthDownRate', 0) for g in games]
    red_zone_vals = [g['off_stats'].get('redZoneRate', 0) for g in games]
    turnovers_vals = [g['off_stats'].get('turnovers', 0) for g in games]
    interceptions_vals = [g['off_stats'].get('interceptions', 0) for g in games]
    fumbles_vals = [g['off_stats'].get('fumbles', 0) for g in games]
    rushing_vals = [g['off_stats'].get('rushingYards', 0) for g in games]
    rushing_avg_vals = [g['off_stats'].get('rushingAvg', 0) for g in games]
    passing_vals = [g['off_stats'].get('passingYards', 0) for g in games]
    completion_vals = [g['off_stats'].get('completionRate', 0) for g in games]
    sacks_vals = [g['off_stats'].get('sacks', 0) for g in games]
    penalties_vals = [g['off_stats'].get('penalties', 0) for g in games]
    
    # === ACTUAL QB STATS (Priority #1!) ===
    qb_rating_vals = []  # ACTUAL QB Rating
    qb_ypa_vals = []  # ACTUAL Yards Per Attempt
    qb_td_vals = []  # ACTUAL TDs
    qb_int_vals = []  # ACTUAL INTs
    qb_td_int_ratio_vals = []  # ACTUAL TD/INT ratio
    
    # Fallback values for games without QB stats
    ypa_vals = []  # For backwards compatibility
    td_int_ratio_vals = []
    sack_rate_vals = []
    epa_proxy_vals = []
    explosive_pass_rate_vals = []
    explosive_run_rate_vals = []
    
    for g in games:
        # Try to use ACTUAL QB stats if available
        if 'qb_stats' in g and g['qb_stats']:
            qb = g['qb_stats']
            
            # ACTUAL QB Rating (most comprehensive QB metric)
            qb_rating_vals.append(qb.get('rating', 0))
            
            # ACTUAL YPA
            qb_ypa_vals.append(qb.get('ypa', 0))
            ypa_vals.append(qb.get('ypa', 0))
            
            # ACTUAL TDs and INTs
            tds = qb.get('tds', 0)
            ints = qb.get('ints', 0)
            qb_td_vals.append(tds)
            qb_int_vals.append(ints)
            
            # ACTUAL TD/INT ratio
            td_int_ratio = tds / (ints + 0.5) if ints >= 0 else 2.0
            qb_td_int_ratio_vals.append(td_int_ratio)
            td_int_ratio_vals.append(td_int_ratio)
            
        else:
            # Fallback to estimates if no QB stats
            ints = g['off_stats'].get('interceptions', 0)
            
            ypa_vals.append(ypa)
            qb_ypa_vals.append(ypa)
            
            rz_rate = g['off_stats'].get('redZoneRate', 0.5)
            est_tds = (pts / 7) * rz_rate
            td_int_ratio = (est_tds / (ints + 0.5)) if ints >= 0 else 2.0
            td_int_ratio_vals.append(td_int_ratio)
            qb_td_int_ratio_vals.append(td_int_ratio)
            
            qb_rating_vals.append(85.0)  # League average
        
        # Sack rate (calculate from team stats)
        pass_yds = g['off_stats'].get('passingYards', 0)
        comp_rate = g['off_stats'].get('completionRate', 0)
        sacks_allowed = g['def_stats'].get('sacks', 0)
        if comp_rate > 0:
            attempts = pass_yds / (comp_rate * 7.5)
            sack_rate = sacks_allowed / (attempts + sacks_allowed) if (attempts + sacks_allowed) > 0 else 0
        else:
            sack_rate = 0
        sack_rate_vals.append(sack_rate)
        
        # EPA Proxy: (Points - League Average) / Total Plays
        # League avg ~22 points, estimate plays from yards/ypp
        pts = g['score_for']  # Define pts here for all games
        ypp = g['off_stats'].get('yardsPerPlay', 5.5)
        total_yds = g['off_stats'].get('totalYards', 0)
        plays = total_yds / ypp if ypp > 0 else 60
        epa_proxy = (pts - 22) / plays if plays > 0 else 0
        epa_proxy_vals.append(epa_proxy)
        
        # Calculate ypa for all games (needed for explosive play calculation)
        if comp_rate > 0:
            attempts = pass_yds / (comp_rate * 7.5)
            ypa = pass_yds / attempts if attempts > 0 else 0
        else:
            ypa = 0
        
        # Explosive Play Rates (proxy - estimate from YPP and yards)
        # If YPP is high, likely more explosive plays
        # Explosive pass: estimate 15+ yard completions
        if comp_rate > 0 and ypa > 0:
            # Higher YPA suggests more explosives
            explosive_pass_pct = min(ypa / 12.0, 0.3)  # Cap at 30%
        else:
            explosive_pass_pct = 0
        explosive_pass_rate_vals.append(explosive_pass_pct)
        
        # Explosive run: 10+ yard runs (estimate from rush avg)
        rush_avg = g['off_stats'].get('rushingAvg', 0)
        explosive_run_pct = min(rush_avg / 8.0, 0.25) if rush_avg > 4.5 else 0.05
        explosive_run_rate_vals.append(explosive_run_pct)
    
    yards_allowed_vals = [g['def_stats'].get('totalYards', 0) for g in games]
    yards_per_play_allowed_vals = [g['def_stats'].get('yardsPerPlay', 0) for g in games]
    points_allowed_vals = [g['score_against'] for g in games]
    rushing_allowed_vals = [g['def_stats'].get('rushingYards', 0) for g in games]
    rushing_avg_allowed_vals = [g['def_stats'].get('rushingAvg', 0) for g in games]
    passing_allowed_vals = [g['def_stats'].get('passingYards', 0) for g in games]
    completion_allowed_vals = [g['def_stats'].get('completionRate', 0) for g in games]
    sacks_allowed_vals = [g['def_stats'].get('sacks', 0) for g in games]
    red_zone_allowed_vals = [g['def_stats'].get('redZoneRate', 0) for g in games]
    third_down_allowed_vals = [g['def_stats'].get('thirdDownRate', 0) for g in games]
    interceptions_forced_vals = [g['def_stats'].get('interceptions', 0) for g in games]  # takeaways
    
    # Defensive explosive plays allowed (from opponent stats)
    explosive_pass_allowed_vals = []
    explosive_run_allowed_vals = []
    for g in games:
        opp_pass_yds = g['def_stats'].get('passingYards', 0)
        opp_comp_rate = g['def_stats'].get('completionRate', 0)
        
        # Opponent's explosive pass rate = what we allowed
        if opp_comp_rate > 0:
            opp_attempts = opp_pass_yds / (opp_comp_rate * 7.5)
            opp_ypa = opp_pass_yds / opp_attempts if opp_attempts > 0 else 0
            explosive_pass_allowed = min(opp_ypa / 12.0, 0.3)
        else:
            explosive_pass_allowed = 0
        explosive_pass_allowed_vals.append(explosive_pass_allowed)
        
        # Opponent's explosive run rate = what we allowed
        opp_rush_avg = g['def_stats'].get('rushingAvg', 0)
        explosive_run_allowed = min(opp_rush_avg / 8.0, 0.25) if opp_rush_avg > 4.5 else 0.05
        explosive_run_allowed_vals.append(explosive_run_allowed)
    
    # offensive averages with recency weighting
    avg_yards_per_play = calculate_weighted_average(yards_per_play_vals)
    avg_total_yards = calculate_weighted_average(total_yards_vals)
    avg_points_scored = calculate_weighted_average(points_scored_vals)
    avg_third_down = calculate_weighted_average(third_down_vals)
    avg_fourth_down = calculate_weighted_average(fourth_down_vals)
    avg_red_zone = calculate_weighted_average(red_zone_vals)
    avg_turnovers_committed = calculate_weighted_average(turnovers_vals)
    avg_interceptions_thrown = calculate_weighted_average(interceptions_vals)
    avg_fumbles_lost = calculate_weighted_average(fumbles_vals)
    avg_rushing_yards = calculate_weighted_average(rushing_vals)
    avg_rushing_avg = calculate_weighted_average(rushing_avg_vals)
    avg_passing_yards = calculate_weighted_average(passing_vals)
    avg_completion_rate = calculate_weighted_average(completion_vals)
    avg_sacks_made = calculate_weighted_average(sacks_vals)  # defensive stat tracked on offense
    avg_penalties = calculate_weighted_average(penalties_vals)
    
    # ACTUAL QB stats (when available)
    avg_qb_rating = calculate_weighted_average(qb_rating_vals)
    avg_qb_ypa = calculate_weighted_average(qb_ypa_vals)
    avg_qb_tds = calculate_weighted_average(qb_td_vals) if qb_td_vals else 0
    avg_qb_ints = calculate_weighted_average(qb_int_vals) if qb_int_vals else 0
    avg_qb_td_int_ratio = calculate_weighted_average(qb_td_int_ratio_vals)
    
    # Backwards compatibility
    avg_yards_per_attempt = avg_qb_ypa if avg_qb_ypa > 0 else calculate_weighted_average(ypa_vals)
    avg_td_int_ratio = avg_qb_td_int_ratio if avg_qb_td_int_ratio > 0 else calculate_weighted_average(td_int_ratio_vals)
    avg_sack_rate = calculate_weighted_average(sack_rate_vals)
    avg_epa_proxy = calculate_weighted_average(epa_proxy_vals)
    avg_explosive_pass_rate = calculate_weighted_average(explosive_pass_rate_vals)
    avg_explosive_run_rate = calculate_weighted_average(explosive_run_rate_vals)
    
    # defensive averages with recency weighting
    avg_yards_allowed = calculate_weighted_average(yards_allowed_vals)
    avg_yards_per_play_allowed = calculate_weighted_average(yards_per_play_allowed_vals)
    avg_points_allowed = calculate_weighted_average(points_allowed_vals)
    avg_rushing_yards_allowed = calculate_weighted_average(rushing_allowed_vals)
    avg_rushing_avg_allowed = calculate_weighted_average(rushing_avg_allowed_vals)
    avg_passing_yards_allowed = calculate_weighted_average(passing_allowed_vals)
    avg_completion_allowed = calculate_weighted_average(completion_allowed_vals)
    avg_sacks_allowed = calculate_weighted_average(sacks_allowed_vals)
    avg_red_zone_allowed = calculate_weighted_average(red_zone_allowed_vals)
    avg_third_down_allowed = calculate_weighted_average(third_down_allowed_vals)
    avg_interceptions_forced = calculate_weighted_average(interceptions_forced_vals)  # takeaways
    
    # recent form (last 3 games) - no weighting needed for binary outcomes
    recent_games = games[-3:] if len(games) >= 3 else games
    recent_wins = sum(1 for g in recent_games if g['result'] == 'W')
    recent_points_scored = sum(g['score_for'] for g in recent_games) / len(recent_games)
    recent_points_allowed = sum(g['score_against'] for g in recent_games) / len(recent_games)
    
    wins = sum(1 for g in games if g['result'] == 'W')
    
    # close game performance (games decided by ≤7 points)
    close_games = [g for g in games if abs(g['score_for'] - g['score_against']) <= 7]
    close_game_wins = sum(1 for g in close_games if g['result'] == 'W')
    close_game_rate = close_game_wins / len(close_games) if close_games else 0.5
    
    # home/away splits
    home_games = [g for g in games if g['location'] == 'home']
    away_games = [g for g in games if g['location'] == 'away']
    home_wins = sum(1 for g in home_games if g['result'] == 'W')
    away_wins = sum(1 for g in away_games if g['result'] == 'W')
    home_win_rate = home_wins / len(home_games) if home_games else 0.5
    away_win_rate = away_wins / len(away_games) if away_games else 0.5
    
    # pythagorean expectation (expected win rate based on points)
    total_points_scored = sum(points_scored_vals)
    total_points_allowed = sum(points_allowed_vals)
    pythagorean_exp = (total_points_scored ** 2.37) / ((total_points_scored ** 2.37) + (total_points_allowed ** 2.37))
    
    # turnover differential (NOW using actual INTs instead of proxy)
    takeaways = avg_interceptions_forced  # actual takeaways
    giveaways = avg_turnovers_committed
    turnover_margin = takeaways - giveaways
    
    return {
        'games_played': len(games),
        'wins': wins,
        'win_rate': wins / len(games),
        'pythagorean_win_rate': pythagorean_exp,
        'offense': {
            'yards_per_play': avg_yards_per_play,
            'total_yards': avg_total_yards,
            'points_scored': avg_points_scored,
            'third_down_rate': avg_third_down,
            'fourth_down_rate': avg_fourth_down,
            'red_zone_rate': avg_red_zone,
            'turnovers': avg_turnovers_committed,
            'interceptions_thrown': avg_interceptions_thrown,
            'fumbles_lost': avg_fumbles_lost,
            'rushing_yards': avg_rushing_yards,
            'rushing_avg': avg_rushing_avg,
            'passing_yards': avg_passing_yards,
            'completion_rate': avg_completion_rate,
            'yards_per_attempt': avg_yards_per_attempt,
            'td_int_ratio': avg_td_int_ratio,
            'sack_rate': avg_sack_rate,
            'sacks_made': avg_sacks_made,
            'penalties': avg_penalties,
            'epa_proxy': avg_epa_proxy,
            'explosive_pass_rate': avg_explosive_pass_rate,
            'explosive_run_rate': avg_explosive_run_rate,
            # ACTUAL QB STATS (when available)
            'qb_rating': avg_qb_rating,
            'qb_tds_per_game': avg_qb_tds,
            'qb_ints_per_game': avg_qb_ints
        },
        'defense': {
            'yards_allowed': avg_yards_allowed,
            'yards_per_play_allowed': avg_yards_per_play_allowed,
            'points_allowed': avg_points_allowed,
            'sacks_allowed': avg_sacks_allowed,
            'rushing_yards_allowed': avg_rushing_yards_allowed,
            'rushing_avg_allowed': avg_rushing_avg_allowed,
            'passing_yards_allowed': avg_passing_yards_allowed,
            'completion_allowed': avg_completion_allowed,
            'red_zone_allowed': avg_red_zone_allowed,
            'third_down_allowed': avg_third_down_allowed,
            'interceptions_forced': avg_interceptions_forced,
            'explosive_pass_allowed': calculate_weighted_average(explosive_pass_allowed_vals),
            'explosive_run_allowed': calculate_weighted_average(explosive_run_allowed_vals)
        },
        'recent_form': {
            'wins': recent_wins,
            'games': len(recent_games),
            'win_rate': recent_wins / len(recent_games),
            'points_scored': recent_points_scored,
            'points_allowed': recent_points_allowed
        },
        'close_games': {
            'total': len(close_games),
            'wins': close_game_wins,
            'win_rate': close_game_rate
        },
        'splits': {
            'home_win_rate': home_win_rate,
            'away_win_rate': away_win_rate,
            'home_advantage': home_win_rate - away_win_rate
        },
        'turnover_margin': turnover_margin
    }


def calculate_bounce_back_probability(team, teams_data):
    """
    calculates bounce-back probability based on underlying metrics vs results
    NOT gambler's fallacy - based on statistical indicators of bad luck/variance
    """
    if team not in teams_data:
        return {'bounce_back_score': 0, 'factors': [], 'has_bounce_back_potential': False}
    
    games = [g for g in teams_data[team] if not g.get('preseason', False)]
    
    if len(games) < 2:
        return {'bounce_back_score': 0, 'factors': [], 'has_bounce_back_potential': False}
    
    bounce_back_score = 0
    factors = []
    
    # only consider if team has recent losses
    recent_games = games[-3:] if len(games) >= 3 else games
    recent_losses = [g for g in recent_games if g['result'] == 'L']
    
    if len(recent_losses) < 2:  # need at least 2 recent losses to consider bounce-back
        return {'bounce_back_score': 0, 'factors': [], 'has_bounce_back_potential': False}
    
    # 1. TURNOVER LUCK - bad TO margin but not from risky play
    last_game = games[-1]
    if last_game['result'] == 'L':
        last_game_to_margin = last_game['off_stats'].get('sacks', 0) - last_game['off_stats'].get('turnovers', 0)
        if last_game_to_margin <= -2:
            bounce_back_score += 1.5
            factors.append("Bad turnover luck in last game")
    
    # check last 2 games combined
    if len(games) >= 2:
        last_2_to_margin = sum(g['off_stats'].get('sacks', 0) - g['off_stats'].get('turnovers', 0) for g in games[-2:])
        if last_2_to_margin <= -3:
            bounce_back_score += 1.0
            factors.append("Poor turnover margin last 2 games")
    
    # 2. RED ZONE/3RD DOWN EXTREMES in recent games
    if len(recent_games) >= 2:
        recent_3rd_down = sum(g['off_stats'].get('thirdDownRate', 0) for g in recent_games) / len(recent_games)
        if recent_3rd_down <= 0.25 and recent_3rd_down > 0:  # extreme low (will normalize)
            bounce_back_score += 1.0
            factors.append("Extreme 3rd down struggles (likely to improve)")
    
    # 3. UNDERLYING PERFORMANCE vs RESULT - played well but lost
    for loss_game in recent_losses:
        # check if they had more total yards but still lost
        their_yards = loss_game['off_stats'].get('totalYards', 0)
        opp_yards = loss_game['def_stats'].get('totalYards', 0)
        
        if their_yards > opp_yards + 50:  # outgained opponent significantly
            bounce_back_score += 1.5
            factors.append("Outgained opponent(s) but lost")
            break
        
        # check yards per play advantage
        their_ypp = loss_game['off_stats'].get('yardsPerPlay', 0)
        opp_ypp = loss_game['def_stats'].get('yardsPerPlay', 0)
        
        if their_ypp > opp_ypp + 0.5:
            bounce_back_score += 1.0
            factors.append("Better efficiency metrics in loss")
            break
    
    # 4. CAPPED BLOWOUT MARGINS - don't overweight blowouts
    for loss_game in recent_losses:
        loss_margin = loss_game['score_against'] - loss_game['score_for']
        if loss_margin >= 20:  # blowout
            bounce_back_score += 0.5
            factors.append("Blowout loss (less predictive)")
            break
    
    # 5. STRENGTH OF SCHEDULE CONTEXT
    # if lost to strong teams and next opponent is weak, boost bounce-back
    # (this would need opponent parameter - will add in prediction function)
    
    return {
        'bounce_back_score': bounce_back_score,
        'factors': factors,
        'has_bounce_back_potential': bounce_back_score >= 2.0
    }


def calculate_opponent_quality(team, teams_data):
    """
    calculates the average quality of opponents a team has faced
    based on those opponents' win rates
    """
    if team not in teams_data:
        return 0.5
    
    opponent_win_rates = []
    for game in teams_data[team]:
        if not game['preseason']:
            opp = game['opponent']
            opp_avg = calculate_team_averages(opp, teams_data, regular_only=True)
            if opp_avg:
                opponent_win_rates.append(opp_avg['win_rate'])
    
    if not opponent_win_rates:
        return 0.5
    
    return sum(opponent_win_rates) / len(opponent_win_rates)


def classify_offensive_style(team_avg):
    """
    Classifies team's offensive style based on run/pass balance
    Returns: 'run_heavy', 'pass_heavy', 'balanced'
    """
    if not team_avg:
        return 'balanced'
    
    rush_yards = team_avg['offense']['rushing_yards']
    pass_yards = team_avg['offense']['passing_yards']
    total_yards = rush_yards + pass_yards
    
    if total_yards == 0:
        return 'balanced'
    
    rush_pct = rush_yards / total_yards
    
    if rush_pct > 0.55:
        return 'run_heavy'
    elif rush_pct < 0.45:
        return 'pass_heavy'
    else:
        return 'balanced'


def find_similar_matchup_performance(team, opponent_style, teams_data, matchup_type='offense'):
    """
    Finds how a team performed against opponents with similar style to upcoming opponent
    matchup_type: 'offense' = how did team's offense do vs similar defenses
                  'defense' = how did team's defense do vs similar offenses
    """
    if team not in teams_data:
        return None
    
    games = [g for g in teams_data[team] if not g['preseason']]
    similar_games = []
    
    for game in games:
        opp = game['opponent']
        opp_avg = calculate_team_averages(opp, teams_data, regular_only=True)
        
        if not opp_avg:
            continue
        
        # Classify opponent's style
        opp_style = classify_offensive_style(opp_avg)
        
        # Find games against similar style opponents
        if opp_style == opponent_style:
            if matchup_type == 'offense':
                # How did our offense perform?
                similar_games.append({
                    'opponent': opp,
                    'points_scored': game['score_for'],
                    'yards': game['off_stats'].get('totalYards', 0),
                    'ypp': game['off_stats'].get('yardsPerPlay', 0),
                    'result': game['result']
                })
            else:  # defense
                # How did our defense perform?
                similar_games.append({
                    'opponent': opp,
                    'points_allowed': game['score_against'],
                    'yards_allowed': game['def_stats'].get('totalYards', 0),
                    'ypp_allowed': game['def_stats'].get('yardsPerPlay', 0),
                    'result': game['result']
                })
    
    if not similar_games:
        return None
    
    # Calculate averages against similar opponents
    if matchup_type == 'offense':
        return {
            'games': len(similar_games),
            'avg_points': sum(g['points_scored'] for g in similar_games) / len(similar_games),
            'avg_yards': sum(g['yards'] for g in similar_games) / len(similar_games),
            'avg_ypp': sum(g['ypp'] for g in similar_games) / len(similar_games),
            'win_rate': sum(1 for g in similar_games if g['result'] == 'W') / len(similar_games)
        }
    else:
        return {
            'games': len(similar_games),
            'avg_points_allowed': sum(g['points_allowed'] for g in similar_games) / len(similar_games),
            'avg_yards_allowed': sum(g['yards_allowed'] for g in similar_games) / len(similar_games),
            'avg_ypp_allowed': sum(g['ypp_allowed'] for g in similar_games) / len(similar_games),
            'win_rate': sum(1 for g in similar_games if g['result'] == 'W') / len(similar_games)
        }


def calculate_strength_adjusted_stats(team, teams_data):
    """
    calculates strength-adjusted offensive stats based on opponent defensive quality
    adjusts team's offensive performance relative to the defenses they've faced
    """
    if team not in teams_data:
        return {'adjustment_factor': 1.0, 'avg_opp_def_rank': 0.5}
    
    # Get all teams' defensive stats to calculate league averages and ranks
    all_teams_def_stats = {}
    for tm in teams_data.keys():
        tm_avg = calculate_team_averages(tm, teams_data, regular_only=True)
        if tm_avg:
            all_teams_def_stats[tm] = {
                'yards_per_play_allowed': tm_avg['defense']['yards_per_play_allowed'],
                'points_allowed': tm_avg['defense']['points_allowed']
            }
    
    if not all_teams_def_stats:
        return {'adjustment_factor': 1.0, 'avg_opp_def_rank': 0.5}
    
    # Calculate league average defense
    league_avg_ypp_allowed = sum(s['yards_per_play_allowed'] for s in all_teams_def_stats.values()) / len(all_teams_def_stats)
    league_avg_pts_allowed = sum(s['points_allowed'] for s in all_teams_def_stats.values()) / len(all_teams_def_stats)
    
    # Rank defenses (lower allowed = better defense = higher rank)
    # Better defenses have lower yards/points allowed
    sorted_by_ypp = sorted(all_teams_def_stats.items(), key=lambda x: x[1]['yards_per_play_allowed'])
    defense_ranks = {team: (i + 1) / len(sorted_by_ypp) for i, (team, _) in enumerate(sorted_by_ypp)}
    
    # Calculate average defensive quality faced by this team
    opp_def_qualities = []
    games = [g for g in teams_data[team] if not g['preseason']]
    
    for game in games:
        opp = game['opponent']
        if opp in defense_ranks:
            # defense_rank: 0.0 = best defense, 1.0 = worst defense
            opp_def_qualities.append(defense_ranks[opp])
    
    if not opp_def_qualities:
        return {'adjustment_factor': 1.0, 'avg_opp_def_rank': 0.5}
    
    avg_opp_def_rank = sum(opp_def_qualities) / len(opp_def_qualities)
    
    # Adjustment factor:
    # If avg_opp_def_rank > 0.5: faced weaker defenses (easier schedule) -> deflate stats
    # If avg_opp_def_rank < 0.5: faced stronger defenses (harder schedule) -> inflate stats
    # Factor ranges from 0.85 to 1.15
    adjustment_factor = 1.0 + (0.5 - avg_opp_def_rank) * 0.3
    
    return {
        'adjustment_factor': adjustment_factor,
        'avg_opp_def_rank': avg_opp_def_rank,
        'faced_tough_defenses': avg_opp_def_rank < 0.4,  # Top 40% of defenses
        'faced_weak_defenses': avg_opp_def_rank > 0.6   # Bottom 40% of defenses
    }


def advanced_prediction(home_team, away_team, teams_data, is_neutral=False, injury_data=None):
    """
    advanced prediction using offensive/defensive matchup analysis
    is_neutral: if True, no home field advantage is applied
    injury_data: dict of current injuries (optional)
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
    
    if not home_avg or not away_avg:
        print("Not enough regular season data for prediction")
        return None
    
    print(f"\n{'=' * 100}")
    print(f"DETAILED TEAM ANALYSIS")
    print(f"{'=' * 100}\n")
    
    # display team stats
    print(f"{home_team} (Home) - {home_avg['wins']}-{home_avg['games_played'] - home_avg['wins']} record:")
    print(f"  Offense: {home_avg['offense']['yards_per_play']:.1f} yds/play, "
          f"{home_avg['offense']['points_scored']:.1f} pts/game, "
          f"{home_avg['offense']['third_down_rate']:.1%} 3rd down")
    print(f"    Rushing: {home_avg['offense']['rushing_yards']:.1f} yds/game ({home_avg['offense']['rushing_avg']:.1f} avg) | "
          f"Passing: {home_avg['offense']['passing_yards']:.1f} yds/game ({home_avg['offense']['completion_rate']:.1%} comp%)")
    print(f"    Red Zone: {home_avg['offense']['red_zone_rate']:.1%} TD rate | "
          f"4th Down: {home_avg['offense']['fourth_down_rate']:.1%} | "
          f"Penalties: {home_avg['offense']['penalties']:.1f}/game")
    print(f"  Defense: {home_avg['defense']['points_allowed']:.1f} pts allowed/game, "
          f"{home_avg['defense']['yards_per_play_allowed']:.1f} yds/play allowed, "
          f"{home_avg['offense']['sacks_made']:.1f} sacks/game")
    print(f"    vs Rush: {home_avg['defense']['rushing_yards_allowed']:.1f} yds/game ({home_avg['defense']['rushing_avg_allowed']:.1f} avg) | "
          f"vs Pass: {home_avg['defense']['passing_yards_allowed']:.1f} yds/game ({home_avg['defense']['completion_allowed']:.1%} comp%)")
    print(f"    Red Zone D: {home_avg['defense']['red_zone_allowed']:.1%} allowed | "
          f"INTs: {home_avg['defense']['interceptions_forced']:.1f}/game")
    print(f"  Recent Form (last {home_avg['recent_form']['games']} games): "
          f"{home_avg['recent_form']['wins']}-{home_avg['recent_form']['games'] - home_avg['recent_form']['wins']}, "
          f"{home_avg['recent_form']['points_scored']:.1f} pts/game")
    print(f"  Close Games (≤7 pts): {home_avg['close_games']['wins']}-{home_avg['close_games']['total'] - home_avg['close_games']['wins']} "
          f"({home_avg['close_games']['win_rate']:.1%})")
    print(f"  Home/Away Split: {home_avg['splits']['home_win_rate']:.1%} home, {home_avg['splits']['away_win_rate']:.1%} away")
    print(f"  Turnover Margin: {home_avg['turnover_margin']:+.1f} per game")
    print(f"  Pythagorean Win %: {home_avg['pythagorean_win_rate']:.1%} (Actual: {home_avg['win_rate']:.1%})")
    
    home_opp_quality = calculate_opponent_quality(home_team, teams_data)
    home_strength_adj = calculate_strength_adjusted_stats(home_team, teams_data)
    print(f"  Opponent Quality: {home_opp_quality:.3f} avg win rate")
    print(f"  Defensive Schedule Strength: Rank {home_strength_adj['avg_opp_def_rank']:.2f} "
          f"(Adjustment: {home_strength_adj['adjustment_factor']:.2f}x)")
    if home_strength_adj['faced_tough_defenses']:
        print(f"    >> Faced TOP-TIER defenses (stats likely understated)")
    elif home_strength_adj['faced_weak_defenses']:
        print(f"    >> Faced WEAK defenses (stat-padding concern)")
    
    # Display injury information
    if home_injury_impact:
        print(f"  Injury Report: {home_injury_impact['total_injuries']} injuries (excluding healthy/active)")
        print(f"    Out/IR: {home_injury_impact['out']}, Doubtful: {home_injury_impact['doubtful']}, "
              f"Questionable: {home_injury_impact['questionable']}")
        print(f"    Impact Score: {home_injury_impact['impact_score']:.1f} (position-weighted)")
        if home_injury_impact['qb_injured']:
            print(f"    ⚠️  QB INJURED - MAJOR IMPACT")
        if home_injury_impact['injury_list']:
            print(f"    Key Injuries: {', '.join(home_injury_impact['injury_list'][:3])}")
            if len(home_injury_impact['injury_list']) > 3:
                print(f"      ... and {len(home_injury_impact['injury_list']) - 3} more")
    print()
    
    print(f"{away_team} (Away) - {away_avg['wins']}-{away_avg['games_played'] - away_avg['wins']} record:")
    print(f"  Offense: {away_avg['offense']['yards_per_play']:.1f} yds/play, "
          f"{away_avg['offense']['points_scored']:.1f} pts/game, "
          f"{away_avg['offense']['third_down_rate']:.1%} 3rd down")
    print(f"    Rushing: {away_avg['offense']['rushing_yards']:.1f} yds/game ({away_avg['offense']['rushing_avg']:.1f} avg) | "
          f"Passing: {away_avg['offense']['passing_yards']:.1f} yds/game ({away_avg['offense']['completion_rate']:.1%} comp%)")
    print(f"    Red Zone: {away_avg['offense']['red_zone_rate']:.1%} TD rate | "
          f"4th Down: {away_avg['offense']['fourth_down_rate']:.1%} | "
          f"Penalties: {away_avg['offense']['penalties']:.1f}/game")
    print(f"  Defense: {away_avg['defense']['points_allowed']:.1f} pts allowed/game, "
          f"{away_avg['defense']['yards_per_play_allowed']:.1f} yds/play allowed, "
          f"{away_avg['offense']['sacks_made']:.1f} sacks/game")
    print(f"    vs Rush: {away_avg['defense']['rushing_yards_allowed']:.1f} yds/game ({away_avg['defense']['rushing_avg_allowed']:.1f} avg) | "
          f"vs Pass: {away_avg['defense']['passing_yards_allowed']:.1f} yds/game ({away_avg['defense']['completion_allowed']:.1%} comp%)")
    print(f"    Red Zone D: {away_avg['defense']['red_zone_allowed']:.1%} allowed | "
          f"INTs: {away_avg['defense']['interceptions_forced']:.1f}/game")
    print(f"  Recent Form (last {away_avg['recent_form']['games']} games): "
          f"{away_avg['recent_form']['wins']}-{away_avg['recent_form']['games'] - away_avg['recent_form']['wins']}, "
          f"{away_avg['recent_form']['points_scored']:.1f} pts/game")
    print(f"  Close Games (≤7 pts): {away_avg['close_games']['wins']}-{away_avg['close_games']['total'] - away_avg['close_games']['wins']} "
          f"({away_avg['close_games']['win_rate']:.1%})")
    print(f"  Home/Away Split: {away_avg['splits']['home_win_rate']:.1%} home, {away_avg['splits']['away_win_rate']:.1%} away")
    print(f"  Turnover Margin: {away_avg['turnover_margin']:+.1f} per game")
    print(f"  Pythagorean Win %: {away_avg['pythagorean_win_rate']:.1%} (Actual: {away_avg['win_rate']:.1%})")
    
    away_opp_quality = calculate_opponent_quality(away_team, teams_data)
    away_strength_adj = calculate_strength_adjusted_stats(away_team, teams_data)
    print(f"  Opponent Quality: {away_opp_quality:.3f} avg win rate")
    print(f"  Defensive Schedule Strength: Rank {away_strength_adj['avg_opp_def_rank']:.2f} "
          f"(Adjustment: {away_strength_adj['adjustment_factor']:.2f}x)")
    if away_strength_adj['faced_tough_defenses']:
        print(f"    >> Faced TOP-TIER defenses (stats likely understated)")
    elif away_strength_adj['faced_weak_defenses']:
        print(f"    >> Faced WEAK defenses (stat-padding concern)")
    
    # Display injury information
    if away_injury_impact:
        print(f"  Injury Report: {away_injury_impact['total_injuries']} injuries (excluding healthy/active)")
        print(f"    Out/IR: {away_injury_impact['out']}, Doubtful: {away_injury_impact['doubtful']}, "
              f"Questionable: {away_injury_impact['questionable']}")
        print(f"    Impact Score: {away_injury_impact['impact_score']:.1f} (position-weighted)")
        if away_injury_impact['qb_injured']:
            print(f"    ⚠️  QB INJURED - MAJOR IMPACT")
        if away_injury_impact['injury_list']:
            print(f"    Key Injuries: {', '.join(away_injury_impact['injury_list'][:3])}")
            if len(away_injury_impact['injury_list']) > 3:
                print(f"      ... and {len(away_injury_impact['injury_list']) - 3} more")
    print()
    
    # MATCHUP ANALYSIS
    print(f"{'=' * 100}")
    print(f"MATCHUP ANALYSIS")
    print(f"{'=' * 100}\n")
    
    # Initialize points
    home_points = 0
    away_points = 0
    
    # Classify offensive styles
    home_style = classify_offensive_style(home_avg)
    away_style = classify_offensive_style(away_avg)
    
    print(f"Offensive Styles:")
    print(f"  {home_team}: {home_style.upper().replace('_', ' ')} "
          f"({home_avg['offense']['rushing_yards']:.0f} rush / {home_avg['offense']['passing_yards']:.0f} pass)")
    print(f"  {away_team}: {away_style.upper().replace('_', ' ')} "
          f"({away_avg['offense']['rushing_yards']:.0f} rush / {away_avg['offense']['passing_yards']:.0f} pass)")
    print()
    
    # Find performance vs similar opponents
    home_vs_similar_off = find_similar_matchup_performance(home_team, away_style, teams_data, 'defense')
    away_vs_similar_off = find_similar_matchup_performance(away_team, home_style, teams_data, 'defense')
    
    if home_vs_similar_off and home_vs_similar_off['games'] >= 2:
        print(f"Similar Matchup History:")
        print(f"  {home_team} defense vs {away_style.replace('_', '-')} offenses ({home_vs_similar_off['games']} games):")
        print(f"    Allowed {home_vs_similar_off['avg_points_allowed']:.1f} pts/game, "
              f"{home_vs_similar_off['avg_ypp_allowed']:.1f} ypp ({home_vs_similar_off['win_rate']:.1%} win rate)")
        
        # Compare to overall defensive average
        if home_vs_similar_off['avg_points_allowed'] < home_avg['defense']['points_allowed'] - 3:
            home_points += 1.5
            print(f"    >> {home_team} defense performs BETTER vs {away_style.replace('_', ' ')} teams (+1.5)")
        elif home_vs_similar_off['avg_points_allowed'] > home_avg['defense']['points_allowed'] + 3:
            away_points += 1.5
            print(f"    >> {home_team} defense struggles vs {away_style.replace('_', ' ')} teams (+1.5 to {away_team})")
    
    if away_vs_similar_off and away_vs_similar_off['games'] >= 2:
        print(f"  {away_team} defense vs {home_style.replace('_', '-')} offenses ({away_vs_similar_off['games']} games):")
        print(f"    Allowed {away_vs_similar_off['avg_points_allowed']:.1f} pts/game, "
              f"{away_vs_similar_off['avg_ypp_allowed']:.1f} ypp ({away_vs_similar_off['win_rate']:.1%} win rate)")
        
        # Compare to overall defensive average
        if away_vs_similar_off['avg_points_allowed'] < away_avg['defense']['points_allowed'] - 3:
            away_points += 1.5
            print(f"    >> {away_team} defense performs BETTER vs {home_style.replace('_', ' ')} teams (+1.5)")
        elif away_vs_similar_off['avg_points_allowed'] > away_avg['defense']['points_allowed'] + 3:
            home_points += 1.5
            print(f"    >> {away_team} defense struggles vs {home_style.replace('_', ' ')} teams (+1.5 to {home_team})")
    
    print()
    
    # 1. offensive vs defensive matchup
    # home offense vs away defense
    home_off_vs_away_def = home_avg['offense']['yards_per_play'] / (away_avg['defense']['yards_per_play_allowed'] + 0.1)
    away_off_vs_home_def = away_avg['offense']['yards_per_play'] / (home_avg['defense']['yards_per_play_allowed'] + 0.1)
    
    print(f"Offensive Efficiency vs Defense:")
    print(f"  {home_team} offense vs {away_team} defense: {home_off_vs_away_def:.2f} ratio")
    if home_off_vs_away_def > 1.2:
        home_points += 3.5
        print(f"    >> Dominant advantage for {home_team} (+3.5)")
    elif home_off_vs_away_def > 1.1:
        home_points += 2.5
        print(f"    >> Strong advantage for {home_team} (+2.5)")
    elif home_off_vs_away_def > 1.0:
        home_points += 1.5
        print(f"    >> Slight advantage for {home_team} (+1.5)")
    elif home_off_vs_away_def < 0.85:
        away_points += 2.0
        print(f"    >> {away_team} defense dominates (+2.0 to {away_team})")
    elif home_off_vs_away_def < 0.95:
        away_points += 1.0
        print(f"    >> {away_team} defense has advantage (+1.0 to {away_team})")
    
    print(f"  {away_team} offense vs {home_team} defense: {away_off_vs_home_def:.2f} ratio")
    if away_off_vs_home_def > 1.2:
        away_points += 3.5
        print(f"    >> Dominant advantage for {away_team} (+3.5)")
    elif away_off_vs_home_def > 1.1:
        away_points += 2.5
        print(f"    >> Strong advantage for {away_team} (+2.5)")
    elif away_off_vs_home_def > 1.0:
        away_points += 1.5
        print(f"    >> Slight advantage for {away_team} (+1.5)")
    elif away_off_vs_home_def < 0.85:
        home_points += 2.0
        print(f"    >> {home_team} defense dominates (+2.0 to {home_team})")
    elif away_off_vs_home_def < 0.95:
        home_points += 1.0
        print(f"    >> {home_team} defense has advantage (+1.0 to {home_team})")
    
    # 2. run game vs run defense
    print(f"\nRun Game Matchup:")
    home_rush_vs_away_rush_d = home_avg['offense']['rushing_yards'] / (away_avg['defense']['rushing_yards_allowed'] + 0.1)
    away_rush_vs_home_rush_d = away_avg['offense']['rushing_yards'] / (home_avg['defense']['rushing_yards_allowed'] + 0.1)
    
    print(f"  {home_team} rush ({home_avg['offense']['rushing_yards']:.1f} yds/g) vs "
          f"{away_team} rush D ({away_avg['defense']['rushing_yards_allowed']:.1f} yds/g allowed): {home_rush_vs_away_rush_d:.2f} ratio")
    if home_rush_vs_away_rush_d > 1.3:
        home_points += 2.5
        print(f"    >> Strong run game advantage for {home_team} (+2.5)")
    elif home_rush_vs_away_rush_d > 1.1:
        home_points += 1.5
        print(f"    >> Moderate run game advantage for {home_team} (+1.5)")
    elif home_rush_vs_away_rush_d > 1.0:
        home_points += 0.75
        print(f"    >> Slight run game advantage for {home_team} (+0.75)")
    
    print(f"  {away_team} rush ({away_avg['offense']['rushing_yards']:.1f} yds/g) vs "
          f"{home_team} rush D ({home_avg['defense']['rushing_yards_allowed']:.1f} yds/g allowed): {away_rush_vs_home_rush_d:.2f} ratio")
    if away_rush_vs_home_rush_d > 1.3:
        away_points += 2.5
        print(f"    >> Strong run game advantage for {away_team} (+2.5)")
    elif away_rush_vs_home_rush_d > 1.1:
        away_points += 1.5
        print(f"    >> Moderate run game advantage for {away_team} (+1.5)")
    elif away_rush_vs_home_rush_d > 1.0:
        away_points += 0.75
        print(f"    >> Slight run game advantage for {away_team} (+0.75)")
    
    # 3. pass game vs pass defense
    print(f"\nPass Game Matchup:")
    home_pass_vs_away_pass_d = home_avg['offense']['passing_yards'] / (away_avg['defense']['passing_yards_allowed'] + 0.1)
    away_pass_vs_home_pass_d = away_avg['offense']['passing_yards'] / (home_avg['defense']['passing_yards_allowed'] + 0.1)
    
    print(f"  {home_team} pass ({home_avg['offense']['passing_yards']:.1f} yds/g) vs "
          f"{away_team} pass D ({away_avg['defense']['passing_yards_allowed']:.1f} yds/g allowed): {home_pass_vs_away_pass_d:.2f} ratio")
    if home_pass_vs_away_pass_d > 1.3:
        home_points += 2.5
        print(f"    >> Strong pass game advantage for {home_team} (+2.5)")
    elif home_pass_vs_away_pass_d > 1.1:
        home_points += 1.5
        print(f"    >> Moderate pass game advantage for {home_team} (+1.5)")
    elif home_pass_vs_away_pass_d > 1.0:
        home_points += 0.75
        print(f"    >> Slight pass game advantage for {home_team} (+0.75)")
    
    print(f"  {away_team} pass ({away_avg['offense']['passing_yards']:.1f} yds/g) vs "
          f"{home_team} pass D ({home_avg['defense']['passing_yards_allowed']:.1f} yds/g allowed): {away_pass_vs_home_pass_d:.2f} ratio")
    if away_pass_vs_home_pass_d > 1.3:
        away_points += 2.5
        print(f"    >> Strong pass game advantage for {away_team} (+2.5)")
    elif away_pass_vs_home_pass_d > 1.1:
        away_points += 1.5
        print(f"    >> Moderate pass game advantage for {away_team} (+1.5)")
    elif away_pass_vs_home_pass_d > 1.0:
        away_points += 0.75
        print(f"    >> Slight pass game advantage for {away_team} (+0.75)")
    
    # 4. scoring efficiency
    print(f"\nScoring Efficiency:")
    points_ratio_home = home_avg['offense']['points_scored'] / (away_avg['defense']['points_allowed'] + 0.1)
    points_ratio_away = away_avg['offense']['points_scored'] / (home_avg['defense']['points_allowed'] + 0.1)
    
    print(f"  {home_team}: {home_avg['offense']['points_scored']:.1f} avg pts vs "
          f"{away_team} allowing {away_avg['defense']['points_allowed']:.1f} avg")
    if points_ratio_home > 1.25:
        home_points += 2.5
        print(f"    >> {home_team} likely to score heavily (+2.5)")
    elif points_ratio_home > 1.15:
        home_points += 1.5
        print(f"    >> {home_team} likely to score well (+1.5)")
    
    print(f"  {away_team}: {away_avg['offense']['points_scored']:.1f} avg pts vs "
          f"{home_team} allowing {home_avg['defense']['points_allowed']:.1f} avg")
    if points_ratio_away > 1.25:
        away_points += 2.5
        print(f"    >> {away_team} likely to score heavily (+2.5)")
    elif points_ratio_away > 1.15:
        away_points += 1.5
        print(f"    >> {away_team} likely to score well (+1.5)")
    
    # NEW: Third Down Conversion Matchup
    print(f"\nThird Down Efficiency:")
    home_3rd_advantage = home_avg['offense']['third_down_rate'] - away_avg['defense']['yards_per_play_allowed'] / 10  # proxy for 3rd down defense
    away_3rd_advantage = away_avg['offense']['third_down_rate'] - home_avg['defense']['yards_per_play_allowed'] / 10
    
    print(f"  {home_team} 3rd down: {home_avg['offense']['third_down_rate']:.1%}")
    print(f"  {away_team} 3rd down: {away_avg['offense']['third_down_rate']:.1%}")
    
    third_down_diff = home_avg['offense']['third_down_rate'] - away_avg['offense']['third_down_rate']
    if third_down_diff > 0.08:
        home_points += 1.5
        print(f"    >> {home_team} has significant 3rd down advantage (+1.5)")
    elif third_down_diff > 0.04:
        home_points += 0.75
        print(f"    >> {home_team} has 3rd down advantage (+0.75)")
    elif third_down_diff < -0.08:
        away_points += 1.5
        print(f"    >> {away_team} has significant 3rd down advantage (+1.5)")
    elif third_down_diff < -0.04:
        away_points += 0.75
        print(f"    >> {away_team} has 3rd down advantage (+0.75)")
    
    # NEW: Sack Differential (Pass Rush Pressure)
    print(f"\nPass Rush Pressure (Sacks):")
    home_sack_diff = home_avg['offense']['sacks_made'] - home_avg['defense']['sacks_allowed']
    away_sack_diff = away_avg['offense']['sacks_made'] - away_avg['defense']['sacks_allowed']
    
    print(f"  {home_team}: {home_avg['offense']['sacks_made']:.1f} sacks/game, {home_avg['defense']['sacks_allowed']:.1f} allowed (diff: {home_sack_diff:+.1f})")
    print(f"  {away_team}: {away_avg['offense']['sacks_made']:.1f} sacks/game, {away_avg['defense']['sacks_allowed']:.1f} allowed (diff: {away_sack_diff:+.1f})")
    
    sack_matchup_diff = home_sack_diff - away_sack_diff
    if sack_matchup_diff > 1.0:
        home_points += 1.5
        print(f"    >> {home_team} has strong pass rush advantage (+1.5)")
    elif sack_matchup_diff > 0.5:
        home_points += 0.75
        print(f"    >> {home_team} has pass rush advantage (+0.75)")
    elif sack_matchup_diff < -1.0:
        away_points += 1.5
        print(f"    >> {away_team} has strong pass rush advantage (+1.5)")
    elif sack_matchup_diff < -0.5:
        away_points += 0.75
        print(f"    >> {away_team} has pass rush advantage (+0.75)")
    
    # 5. momentum/recent form
    print(f"\nMomentum & Recent Form:")
    home_momentum = home_avg['recent_form']['win_rate']
    away_momentum = away_avg['recent_form']['win_rate']
    
    print(f"  {home_team}: {home_avg['recent_form']['wins']}-{home_avg['recent_form']['games'] - home_avg['recent_form']['wins']} "
          f"in last {home_avg['recent_form']['games']}, scoring {home_avg['recent_form']['points_scored']:.1f} pts/game")
    print(f"  {away_team}: {away_avg['recent_form']['wins']}-{away_avg['recent_form']['games'] - away_avg['recent_form']['wins']} "
          f"in last {away_avg['recent_form']['games']}, scoring {away_avg['recent_form']['points_scored']:.1f} pts/game")
    
    # hot team bonus
    if home_momentum == 1.0 and home_avg['recent_form']['games'] >= 3:
        home_points += 2.0
        print(f"  >> {home_team} is on a HOT STREAK (+2.0)")
    elif home_momentum >= 0.67:
        home_points += 1.0
        print(f"  >> {home_team} has positive momentum (+1.0)")
    elif home_momentum == 0.0 and home_avg['recent_form']['games'] >= 3:
        away_points += 1.5
        print(f"  >> {home_team} struggling lately (+1.5 to {away_team})")
    
    if away_momentum == 1.0 and away_avg['recent_form']['games'] >= 3:
        away_points += 2.0
        print(f"  >> {away_team} is on a HOT STREAK (+2.0)")
    elif away_momentum >= 0.67:
        away_points += 1.0
        print(f"  >> {away_team} has positive momentum (+1.0)")
    elif away_momentum == 0.0 and away_avg['recent_form']['games'] >= 3:
        home_points += 1.5
        print(f"  >> {away_team} struggling lately (+1.5 to {home_team})")
    
    # 6. opponent quality adjustment (only if you have a winning record)
    print(f"\nOpponent Quality Adjustment:")
    # only give credit for tough schedule if you're actually winning
    if home_avg['win_rate'] >= 0.5 and home_opp_quality > away_opp_quality + 0.15:
        home_points += 1.5
        print(f"  {home_team} winning despite tough schedule (+1.5)")
    elif home_avg['win_rate'] >= 0.5 and home_opp_quality > away_opp_quality + 0.05:
        home_points += 0.75
        print(f"  {home_team} has faced tougher opponents (+0.75)")
    elif away_avg['win_rate'] >= 0.5 and away_opp_quality > home_opp_quality + 0.15:
        away_points += 1.5
        print(f"  {away_team} winning despite tough schedule (+1.5)")
    elif away_avg['win_rate'] >= 0.5 and away_opp_quality > home_opp_quality + 0.05:
        away_points += 0.75
        print(f"  {away_team} has faced tougher opponents (+0.75)")
    else:
        print(f"  Similar opponent quality or not applicable")
    
    # NEW: Strength-Adjusted Performance
    print(f"\nStrength-of-Schedule Adjustment (Defensive Quality Faced):")
    print(f"  {home_team}: {home_strength_adj['adjustment_factor']:.2f}x adjustment "
          f"(faced defenses ranked {home_strength_adj['avg_opp_def_rank']:.2f})")
    print(f"  {away_team}: {away_strength_adj['adjustment_factor']:.2f}x adjustment "
          f"(faced defenses ranked {away_strength_adj['avg_opp_def_rank']:.2f})")
    
    # Award points for playing well against tough defenses
    if home_strength_adj['faced_tough_defenses'] and home_avg['offense']['points_scored'] > 22:
        home_points += 1.5
        print(f"    >> {home_team} scoring well vs ELITE defenses (+1.5)")
    elif home_strength_adj['faced_weak_defenses']:
        # stat-padding penalty - good stats against bad teams don't count as much
        home_points -= 2.0
        print(f"    >> {home_team} stat-padding vs WEAK defenses (-2.0)")
    
    if away_strength_adj['faced_tough_defenses'] and away_avg['offense']['points_scored'] > 22:
        away_points += 1.5
        print(f"    >> {away_team} scoring well vs ELITE defenses (+1.5)")
    elif away_strength_adj['faced_weak_defenses']:
        # stat-padding penalty - good stats against bad teams don't count as much
        away_points -= 2.0
        print(f"    >> {away_team} stat-padding vs WEAK defenses (-2.0)")
    
    # NEW: Close Game Performance
    print(f"\nClose Game Performance (≤7 points):")
    print(f"  {home_team}: {home_avg['close_games']['wins']}-{home_avg['close_games']['total'] - home_avg['close_games']['wins']} "
          f"({home_avg['close_games']['win_rate']:.1%}) in close games")
    print(f"  {away_team}: {away_avg['close_games']['wins']}-{away_avg['close_games']['total'] - away_avg['close_games']['wins']} "
          f"({away_avg['close_games']['win_rate']:.1%}) in close games")
    
    if home_avg['close_games']['total'] >= 3 and home_avg['close_games']['win_rate'] > 0.60:
        home_points += 1.0
        print(f"    >> {home_team} excels in close games (+1.0)")
    if away_avg['close_games']['total'] >= 3 and away_avg['close_games']['win_rate'] > 0.60:
        away_points += 1.0
        print(f"    >> {away_team} excels in close games (+1.0)")
    
    # 7. UPDATED: Dynamic Home Field Advantage
    if is_neutral:
        print(f"\nHome Field Advantage: NEUTRAL SITE (no advantage)")
    else:
        # Calculate dynamic home field advantage based on actual home/away split
        home_advantage_strength = home_avg['splits']['home_advantage']
        
        # Base home field advantage ranges from 0.0 to 3.0 based on actual splits
        # Winless at home = NO home field advantage
        if home_avg['splits']['home_win_rate'] == 0:
            hfa_points = 0.0
            print(f"\nHome Field Advantage: NONE (+0.0)")
            print(f"  {home_team} is WINLESS at home (0% home win rate)")
        elif home_advantage_strength > 0.25:  # Dominant home team
            hfa_points = 3.0
            print(f"\nHome Field Advantage: {home_team} has DOMINANT home advantage (+3.0)")
            print(f"  ({home_avg['splits']['home_win_rate']:.1%} home vs {home_avg['splits']['away_win_rate']:.1%} away)")
        elif home_advantage_strength > 0.15:  # Strong home team
            hfa_points = 2.5
            print(f"\nHome Field Advantage: {home_team} has STRONG home advantage (+2.5)")
            print(f"  ({home_avg['splits']['home_win_rate']:.1%} home vs {home_avg['splits']['away_win_rate']:.1%} away)")
        elif home_advantage_strength > 0.05:  # Moderate home team
            hfa_points = 2.0
            print(f"\nHome Field Advantage: {home_team} has moderate home advantage (+2.0)")
            print(f"  ({home_avg['splits']['home_win_rate']:.1%} home vs {home_avg['splits']['away_win_rate']:.1%} away)")
        elif home_advantage_strength < -0.10:  # Actually worse at home!
            hfa_points = 0.5
            print(f"\nHome Field Advantage: {home_team} minimal advantage (+0.5)")
            print(f"  WARNING: Team performs worse at home ({home_avg['splits']['home_win_rate']:.1%} home vs {home_avg['splits']['away_win_rate']:.1%} away)")
        else:  # Neutral home effect
            hfa_points = 1.5
            print(f"\nHome Field Advantage: {home_team} slight advantage (+1.5)")
            print(f"  ({home_avg['splits']['home_win_rate']:.1%} home vs {home_avg['splits']['away_win_rate']:.1%} away)")
        
        home_points += hfa_points
        
        # NEW: Home vs Away Performance Matchup
        print(f"\n  Home/Away Matchup Comparison:")
        print(f"    {home_team} at home: {home_avg['splits']['home_win_rate']:.1%}")
        print(f"    {away_team} on road: {away_avg['splits']['away_win_rate']:.1%}")
        
        # If away team is excellent on the road, reduce home field advantage
        if away_avg['splits']['away_win_rate'] >= 0.70:  # Great road team
            if away_avg['splits']['away_win_rate'] > home_avg['splits']['home_win_rate']:
                away_points += 1.5
                print(f"    >> {away_team} is ELITE on the road and better than {home_team} at home (+1.5 to {away_team})")
            else:
                away_points += 1.0
                print(f"    >> {away_team} is excellent on the road (+1.0)")
        elif away_avg['splits']['away_win_rate'] < 0.30:  # Poor road team
            home_points += 0.5
            print(f"    >> {away_team} struggles on the road (+0.5 to {home_team})")
    
    # QB Completion % Matchup
    print(f"\nQB Passing Accuracy:")
    home_comp_vs_away_def = home_avg['offense']['completion_rate'] - away_avg['defense']['completion_allowed']
    away_comp_vs_home_def = away_avg['offense']['completion_rate'] - home_avg['defense']['completion_allowed']
    
    print(f"  {home_team} QB: {home_avg['offense']['completion_rate']:.1%} vs {away_team} allowing {away_avg['defense']['completion_allowed']:.1%}")
    if home_comp_vs_away_def > 0.10:
        home_points += 2.0
        print(f"    >> {home_team} QB should have high completion rate (+2.0)")
    elif home_comp_vs_away_def > 0.05:
        home_points += 1.0
        print(f"    >> {home_team} QB has accuracy advantage (+1.0)")
    elif home_comp_vs_away_def < -0.10:
        away_points += 1.5
        print(f"    >> {away_team} pass defense should limit completions (+1.5 to {away_team})")
    
    print(f"  {away_team} QB: {away_avg['offense']['completion_rate']:.1%} vs {home_team} allowing {home_avg['defense']['completion_allowed']:.1%}")
    if away_comp_vs_home_def > 0.10:
        away_points += 2.0
        print(f"    >> {away_team} QB should have high completion rate (+2.0)")
    elif away_comp_vs_home_def > 0.05:
        away_points += 1.0
        print(f"    >> {away_team} QB has accuracy advantage (+1.0)")
    elif away_comp_vs_home_def < -0.10:
        home_points += 1.5
        print(f"    >> {home_team} pass defense should limit completions (+1.5 to {home_team})")
    
    # Red Zone Efficiency Matchup (ACTUAL red zone TD%)
    print(f"\nRed Zone TD% Matchup:")
    print(f"  {home_team} RZ: {home_avg['offense']['red_zone_rate']:.1%} TD rate vs {away_team} allowing {away_avg['defense']['red_zone_allowed']:.1%}")
    print(f"  {away_team} RZ: {away_avg['offense']['red_zone_rate']:.1%} TD rate vs {home_team} allowing {home_avg['defense']['red_zone_allowed']:.1%}")
    
    home_rz_advantage = home_avg['offense']['red_zone_rate'] - away_avg['defense']['red_zone_allowed']
    away_rz_advantage = away_avg['offense']['red_zone_rate'] - home_avg['defense']['red_zone_allowed']
    
    if home_rz_advantage > 0.15:
        home_points += 2.5
        print(f"    >> {home_team} excellent red zone matchup (+2.5)")
    elif home_rz_advantage > 0.08:
        home_points += 1.5
        print(f"    >> {home_team} favorable red zone matchup (+1.5)")
    
    if away_rz_advantage > 0.15:
        away_points += 2.5
        print(f"    >> {away_team} excellent red zone matchup (+2.5)")
    elif away_rz_advantage > 0.08:
        away_points += 1.5
        print(f"    >> {away_team} favorable red zone matchup (+1.5)")
    
    # Rushing Efficiency (yards per carry)
    print(f"\nRushing Efficiency (Yards Per Carry):")
    print(f"  {home_team}: {home_avg['offense']['rushing_avg']:.1f} ypc vs {away_team} allowing {away_avg['defense']['rushing_avg_allowed']:.1f} ypc")
    print(f"  {away_team}: {away_avg['offense']['rushing_avg']:.1f} ypc vs {home_team} allowing {home_avg['defense']['rushing_avg_allowed']:.1f} ypc")
    
    home_rush_eff_adv = home_avg['offense']['rushing_avg'] - away_avg['defense']['rushing_avg_allowed']
    away_rush_eff_adv = away_avg['offense']['rushing_avg'] - home_avg['defense']['rushing_avg_allowed']
    
    if home_rush_eff_adv > 1.5:
        home_points += 2.0
        print(f"    >> {home_team} should dominate on the ground (+2.0)")
    elif home_rush_eff_adv > 0.8:
        home_points += 1.0
        print(f"    >> {home_team} has rushing efficiency edge (+1.0)")
    
    if away_rush_eff_adv > 1.5:
        away_points += 2.0
        print(f"    >> {away_team} should dominate on the ground (+2.0)")
    elif away_rush_eff_adv > 0.8:
        away_points += 1.0
        print(f"    >> {away_team} has rushing efficiency edge (+1.0)")
    
    # Interception/Takeaway Differential
    print(f"\nTakeaway Battle (Interceptions):")
    print(f"  {home_team}: {home_avg['offense']['interceptions_thrown']:.1f} INTs thrown/game, {home_avg['defense']['interceptions_forced']:.1f} INTs forced/game")
    print(f"  {away_team}: {away_avg['offense']['interceptions_thrown']:.1f} INTs thrown/game, {away_avg['defense']['interceptions_forced']:.1f} INTs forced/game")
    
    # Matchup: home's INTs thrown vs away's INTs forced
    home_int_risk = home_avg['offense']['interceptions_thrown'] - away_avg['defense']['interceptions_forced']
    away_int_risk = away_avg['offense']['interceptions_thrown'] - home_avg['defense']['interceptions_forced']
    
    if home_int_risk < -0.5:  # Home throws few INTs but away doesn't force many = advantage
        home_points += 1.0
        print(f"    >> {home_team} protects ball well vs weak takeaway defense (+1.0)")
    elif home_int_risk > 1.0:  # Home throws many INTs and away forces many = big problem
        away_points += 2.5
        print(f"    >> {away_team} should generate turnovers (+2.5)")
    elif home_int_risk > 0.5:
        away_points += 1.0
        print(f"    >> {away_team} has turnover advantage (+1.0)")
    
    if away_int_risk < -0.5:
        away_points += 1.0
        print(f"    >> {away_team} protects ball well vs weak takeaway defense (+1.0)")
    elif away_int_risk > 1.0:
        home_points += 2.5
        print(f"    >> {home_team} should generate turnovers (+2.5)")
    elif away_int_risk > 0.5:
        home_points += 1.0
        print(f"    >> {home_team} has turnover advantage (+1.0)")
    
    # Penalty Discipline
    print(f"\nPenalty Discipline:")
    print(f"  {home_team}: {home_avg['offense']['penalties']:.1f} penalties/game")
    print(f"  {away_team}: {away_avg['offense']['penalties']:.1f} penalties/game")
    
    penalty_diff = away_avg['offense']['penalties'] - home_avg['offense']['penalties']
    if penalty_diff > 2.0:
        home_points += 1.5
        print(f"    >> {home_team} much more disciplined (+1.5)")
    elif penalty_diff > 1.0:
        home_points += 0.75
        print(f"    >> {home_team} more disciplined (+0.75)")
    elif penalty_diff < -2.0:
        away_points += 1.5
        print(f"    >> {away_team} much more disciplined (+1.5)")
    elif penalty_diff < -1.0:
        away_points += 0.75
        print(f"    >> {away_team} more disciplined (+0.75)")
    
    # 8. UPDATED: Win Rate Factor (reduced weight) + Pythagorean Expectation
    print(f"\nWin Rate & Performance Indicators:")
    
    # Actual win rate factor (reduced from 5.0 to 3.0)
    home_win_pts = home_avg['win_rate'] * 3.0
    away_win_pts = away_avg['win_rate'] * 3.0
    home_points += home_win_pts
    away_points += away_win_pts
    
    print(f"  {home_team} Win Rate: +{home_win_pts:.1f} ({home_avg['wins']}-{home_avg['games_played'] - home_avg['wins']}, {home_avg['win_rate']:.1%})")
    print(f"  {away_team} Win Rate: +{away_win_pts:.1f} ({away_avg['wins']}-{away_avg['games_played'] - away_avg['wins']}, {away_avg['win_rate']:.1%})")
    
    # BOUNCE-BACK ANALYSIS - based on underlying metrics, not gambler's fallacy
    home_bounce_back = calculate_bounce_back_probability(home_team, teams_data)
    away_bounce_back = calculate_bounce_back_probability(away_team, teams_data)
    
    print(f"\n  Bounce-Back Analysis (underlying performance vs results):")
    
    if home_bounce_back['has_bounce_back_potential']:
        home_points += home_bounce_back['bounce_back_score']
        print(f"    {home_team}: +{home_bounce_back['bounce_back_score']:.1f} bounce-back potential")
        for factor in home_bounce_back['factors']:
            print(f"      - {factor}")
    else:
        print(f"    {home_team}: No significant bounce-back indicators")
    
    if away_bounce_back['has_bounce_back_potential']:
        away_points += away_bounce_back['bounce_back_score']
        print(f"    {away_team}: +{away_bounce_back['bounce_back_score']:.1f} bounce-back potential")
        for factor in away_bounce_back['factors']:
            print(f"      - {factor}")
    else:
        print(f"    {away_team}: No significant bounce-back indicators")
    
    # Pythagorean expectation - only penalize lucky overperformers
    home_pyth_diff = home_avg['win_rate'] - home_avg['pythagorean_win_rate']
    away_pyth_diff = away_avg['win_rate'] - away_avg['pythagorean_win_rate']
    
    print(f"\n  Pythagorean Win% (luck detection):")
    print(f"    {home_team}: {home_avg['pythagorean_win_rate']:.1%} expected vs {home_avg['win_rate']:.1%} actual (diff: {home_pyth_diff:+.1%})")
    if home_pyth_diff > 0.15:  # Overperforming significantly (lucky wins)
        home_points -= 1.0
        print(f"      >> {home_team} has been lucky in close games (-1.0, regression risk)")
    
    print(f"    {away_team}: {away_avg['pythagorean_win_rate']:.1%} expected vs {away_avg['win_rate']:.1%} actual (diff: {away_pyth_diff:+.1%})")
    if away_pyth_diff > 0.15:  # Overperforming significantly (lucky wins)
        away_points -= 1.0
        print(f"      >> {away_team} has been lucky in close games (-1.0, regression risk)")
    
    # Additional penalty for losing records (scaled)
    print(f"\n  Record Quality:")
    if home_avg['win_rate'] == 0:
        home_points -= 3.0
        print(f"    >> {home_team} is WINLESS (-3.0)")
    elif home_avg['win_rate'] < 0.2:
        home_points -= 2.5
        print(f"    >> {home_team} has very poor record (-2.5)")
    elif home_avg['win_rate'] < 0.4:
        home_points -= 1.5
        print(f"    >> {home_team} has poor record (-1.5)")
    
    if away_avg['win_rate'] == 0:
        away_points -= 3.0
        print(f"    >> {away_team} is WINLESS (-3.0)")
    elif away_avg['win_rate'] < 0.2:
        away_points -= 2.5
        print(f"    >> {away_team} has very poor record (-2.5)")
    elif away_avg['win_rate'] < 0.4:
        away_points -= 1.5
        print(f"    >> {away_team} has poor record (-1.5)")
    
    # 9. UPDATED: Turnover Margin (not just giveaways)
    print(f"\nTurnover Margin:")
    print(f"  {home_team}: {home_avg['turnover_margin']:+.1f} per game")
    print(f"  {away_team}: {away_avg['turnover_margin']:+.1f} per game")
    
    margin_diff = home_avg['turnover_margin'] - away_avg['turnover_margin']
    if margin_diff > 1.0:
        home_points += 1.5
        print(f"    >> {home_team} has significantly better turnover margin (+1.5)")
    elif margin_diff > 0.5:
        home_points += 0.75
        print(f"    >> {home_team} has better turnover margin (+0.75)")
    elif margin_diff < -1.0:
        away_points += 1.5
        print(f"    >> {away_team} has significantly better turnover margin (+1.5)")
    elif margin_diff < -0.5:
        away_points += 0.75
        print(f"    >> {away_team} has better turnover margin (+0.75)")
    
    # NEW: Injury Impact (position-weighted)
    if home_injury_impact and away_injury_impact:
        print(f"\nInjury Impact (Position-Weighted):")
        print(f"  {home_team}: {home_injury_impact['impact_score']:.1f} impact score "
              f"({home_injury_impact['out']} out, {home_injury_impact['doubtful']} doubtful, "
              f"{home_injury_impact['key_injuries']} key)")
        if home_injury_impact['qb_injured']:
            print(f"    ⚠️  QB INJURED")
        
        print(f"  {away_team}: {away_injury_impact['impact_score']:.1f} impact score "
              f"({away_injury_impact['out']} out, {away_injury_impact['doubtful']} doubtful, "
              f"{away_injury_impact['key_injuries']} key)")
        if away_injury_impact['qb_injured']:
            print(f"    ⚠️  QB INJURED")
        
        # QB-specific penalties (most impactful)
        if home_injury_impact['qb_injured'] and not away_injury_impact['qb_injured']:
            away_points += 5.0
            print(f"    >> {home_team} QB injured, MAJOR advantage to {away_team} (+5.0)")
        elif away_injury_impact['qb_injured'] and not home_injury_impact['qb_injured']:
            home_points += 5.0
            print(f"    >> {away_team} QB injured, MAJOR advantage to {home_team} (+5.0)")
        elif home_injury_impact['qb_injured'] and away_injury_impact['qb_injured']:
            print(f"    >> Both QBs injured, no relative advantage")
        
        # General injury impact comparison (Award to team with FEWER injuries)
        # New thresholds adjusted for position-weighted scoring
        impact_diff = away_injury_impact['impact_score'] - home_injury_impact['impact_score']
        
        if abs(impact_diff) < 3.0 and not (home_injury_impact['qb_injured'] or away_injury_impact['qb_injured']):
            print(f"    >> Both teams relatively healthy")
        elif impact_diff > 10.0:  # Away team much more injured
            home_points += 3.0
            print(f"    >> {away_team} significantly injury-depleted (+3.0 to {home_team})")
        elif impact_diff > 5.0:  # Away team more injured
            home_points += 2.0
            print(f"    >> {away_team} dealing with major injuries (+2.0 to {home_team})")
        elif impact_diff > 3.0:
            home_points += 1.0
            print(f"    >> {away_team} more injured (+1.0 to {home_team})")
        elif impact_diff < -10.0:  # Home team much more injured
            away_points += 3.0
            print(f"    >> {home_team} significantly injury-depleted (+3.0 to {away_team})")
        elif impact_diff < -5.0:  # Home team more injured
            away_points += 2.0
            print(f"    >> {home_team} dealing with major injuries (+2.0 to {away_team})")
        elif impact_diff < -3.0:
            away_points += 1.0
            print(f"    >> {home_team} more injured (+1.0 to {away_team})")
    
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
    print("NFL Game Predictor - Advanced Analysis")
    print("=" * 100)
    print("\nReading NFL data with detailed stats...")
    
    # read and parse data
    teams_data = read_nfl_data()
    
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
                print(f"Injury data loaded! {total_injuries} total injuries across league.\n")
            else:
                print("Could not fetch injury data. Proceeding without injury analysis.\n")
        except Exception as e:
            print(f"Error loading injury data: {e}")
            print("Proceeding without injury analysis.\n")
    else:
        print("Injury module not available. Proceeding without injury analysis.\n")
    
    # get user input
    print("Enter team names (use full names as they appear in nflData.txt)")
    print("Examples: 'Tampa Bay Buccaneers', 'Seattle Seahawks', etc.\n")
    
    team1 = input("Enter TEAM 1: ").strip()
    team2 = input("Enter TEAM 2: ").strip()
    
    # ask about game location
    print("\nGame Location:")
    print("  1 - Team 1 is HOME")
    print("  2 - Team 2 is HOME")
    print("  3 - NEUTRAL site")
    location_choice = input("Choose (1/2/3): ").strip()
    
    if location_choice == "1":
        home_team = team1
        away_team = team2
        is_neutral = False
    elif location_choice == "2":
        home_team = team2
        away_team = team1
        is_neutral = False
    elif location_choice == "3":
        home_team = team1
        away_team = team2
        is_neutral = True
    else:
        print("Invalid choice, defaulting to Team 1 as home")
        home_team = team1
        away_team = team2
        is_neutral = False
    
    # predict the game
    result = advanced_prediction(home_team, away_team, teams_data, is_neutral, injury_data)
    
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
            confidence = min(diff / 6 * 100, 95)
            print(f"PREDICTION: {home_team} wins")
            print(f"Confidence: {confidence:.0f}%")
        elif away_points > home_points:
            diff = away_points - home_points
            confidence = min(diff / 6 * 100, 95)
            print(f"PREDICTION: {away_team} wins")
            print(f"Confidence: {confidence:.0f}%")
        else:
            print("PREDICTION: Too close to call")
            print("Confidence: 50% (toss-up)")
        
        print(f"{'=' * 100}")


if __name__ == "__main__":
    main()
