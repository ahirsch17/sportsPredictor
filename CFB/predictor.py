"""
College Football Game Predictor - Advanced Analysis
Analyzes detailed game stats to predict CFB outcomes with contextual matchup analysis
"""

# Import injury data functions
try:
    from injuryextract import get_injury_data, calculate_injury_impact
    INJURIES_AVAILABLE = True
except ImportError:
    INJURIES_AVAILABLE = False


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
    except:
        return 0 if stat_type != 'ratio' else 0.0


def read_cfb_data():
    """
    reads cfbData.txt with detailed stats and parses into structured format
    """
    teams_data = {}
    
    try:
        with open('cfbData.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        i = 0
        current_week = None
        is_preseason = False
        
        while i < len(lines):
            line = lines[i].strip()
            
            # detect week header (lines that contain WEEK but not brackets)
            if ('WEEK_' in line or 'POSTSEASON' in line) and '[' not in line and '=' not in line:
                current_week = line
                is_preseason = False  # CFB doesn't really have preseason like NFL
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
                    
                    # look ahead for AWAY stats
                    if i + 1 < len(lines) and 'AWAY' in lines[i + 1]:
                        i += 2  # skip "AWAY (team):" line
                        
                        # parse away yards line
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
                        
                        # parse away passing/rushing line
                        if i < len(lines):
                            stats_line = lines[i].strip()
                            if 'Passing:' in stats_line:
                                parts = stats_line.split('|')
                                for part in parts:
                                    if 'Passing:' in part:
                                        away_stats['passingYards'] = parse_stat(part.split(':')[1].replace('yds', '').strip())
                                    elif 'Rushing:' in part:
                                        away_stats['rushingYards'] = parse_stat(part.split(':')[1].replace('yds', '').strip())
                                    elif '1st Downs:' in part:
                                        away_stats['firstDowns'] = parse_stat(part.split(':')[1].strip())
                            i += 1
                        
                        # parse away efficiency line
                        if i < len(lines):
                            stats_line = lines[i].strip()
                            if '3rd Down:' in stats_line:
                                parts = stats_line.split('|')
                                for part in parts:
                                    if '3rd Down:' in part:
                                        away_stats['thirdDownRate'] = parse_stat(part.split(':')[1].strip(), 'ratio')
                                    elif 'Turnovers:' in part:
                                        away_stats['turnovers'] = parse_stat(part.split(':')[1].strip())
                                    elif 'Sacks:' in part:
                                        away_stats['sacks'] = parse_stat(part.split(':')[1].strip())
                            i += 1
                    
                    # look ahead for HOME stats
                    if i < len(lines) and 'HOME' in lines[i]:
                        i += 1  # skip "HOME (team):" line
                        
                        # parse home yards line
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
                        
                        # parse home passing/rushing line
                        if i < len(lines):
                            stats_line = lines[i].strip()
                            if 'Passing:' in stats_line:
                                parts = stats_line.split('|')
                                for part in parts:
                                    if 'Passing:' in part:
                                        home_stats['passingYards'] = parse_stat(part.split(':')[1].replace('yds', '').strip())
                                    elif 'Rushing:' in part:
                                        home_stats['rushingYards'] = parse_stat(part.split(':')[1].replace('yds', '').strip())
                                    elif '1st Downs:' in part:
                                        home_stats['firstDowns'] = parse_stat(part.split(':')[1].strip())
                            i += 1
                        
                        # parse home efficiency line
                        if i < len(lines):
                            stats_line = lines[i].strip()
                            if '3rd Down:' in stats_line:
                                parts = stats_line.split('|')
                                for part in parts:
                                    if '3rd Down:' in part:
                                        home_stats['thirdDownRate'] = parse_stat(part.split(':')[1].strip(), 'ratio')
                                    elif 'Turnovers:' in part:
                                        home_stats['turnovers'] = parse_stat(part.split(':')[1].strip())
                                    elif 'Sacks:' in part:
                                        home_stats['sacks'] = parse_stat(part.split(':')[1].strip())
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
                            'postseason': 'POSTSEASON' in current_week if current_week else False,
                            'off_stats': away_stats,
                            'def_stats': home_stats  # opponent's offense = our defense faced
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
                            'postseason': 'POSTSEASON' in current_week if current_week else False,
                            'off_stats': home_stats,
                            'def_stats': away_stats
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
                            'postseason': 'POSTSEASON' in current_week if current_week else False,
                            'off_stats': home_stats,
                            'def_stats': away_stats
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
                            'postseason': 'POSTSEASON' in current_week if current_week else False,
                            'off_stats': away_stats,
                            'def_stats': home_stats
                        })
                
                except Exception as e:
                    print(f"Error parsing game: {e}")
                    i += 1
                    continue
            
            i += 1
    
    except FileNotFoundError:
        print("ERROR: cfbData.txt not found. Please run dataextract.py first.")
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
    
    return {'mean': mean, 'std': max(std, 1e-6)}


def opponent_adjusted_z_score(team_val, opponent_val, league_mean, league_std, alpha=0.3):
    """
    calculates opponent-adjusted z-score
    alpha controls how much we shrink toward opponent average
    """
    adjusted_val = team_val - (opponent_val - league_mean) * alpha
    z_score = (adjusted_val - league_mean) / max(league_std, 1e-6)
    return z_score


def calculate_team_averages(team, teams_data, exclude_postseason=False):
    """
    calculates average offensive and defensive stats for a team
    includes run/pass breakdown, recent form analysis, and recency weighting
    """
    if team not in teams_data:
        return None
    
    games = teams_data[team]
    if exclude_postseason:
        games = [g for g in games if not g.get('postseason', False)]
    
    if not games:
        return None
    
    # extract values for weighted averaging
    yards_per_play_vals = [g['off_stats'].get('yardsPerPlay', 0) for g in games]
    total_yards_vals = [g['off_stats'].get('totalYards', 0) for g in games]
    points_scored_vals = [g['score_for'] for g in games]
    third_down_vals = [g['off_stats'].get('thirdDownRate', 0) for g in games]
    turnovers_vals = [g['off_stats'].get('turnovers', 0) for g in games]
    rushing_vals = [g['off_stats'].get('rushingYards', 0) for g in games]
    passing_vals = [g['off_stats'].get('passingYards', 0) for g in games]
    sacks_vals = [g['off_stats'].get('sacks', 0) for g in games]
    
    yards_allowed_vals = [g['def_stats'].get('totalYards', 0) for g in games]
    yards_per_play_allowed_vals = [g['def_stats'].get('yardsPerPlay', 0) for g in games]
    points_allowed_vals = [g['score_against'] for g in games]
    rushing_allowed_vals = [g['def_stats'].get('rushingYards', 0) for g in games]
    passing_allowed_vals = [g['def_stats'].get('passingYards', 0) for g in games]
    sacks_allowed_vals = [g['def_stats'].get('sacks', 0) for g in games]
    
    # offensive averages with recency weighting
    avg_yards_per_play = calculate_weighted_average(yards_per_play_vals)
    avg_total_yards = calculate_weighted_average(total_yards_vals)
    avg_points_scored = calculate_weighted_average(points_scored_vals)
    avg_third_down = calculate_weighted_average(third_down_vals)
    avg_turnovers_committed = calculate_weighted_average(turnovers_vals)
    avg_rushing_yards = calculate_weighted_average(rushing_vals)
    avg_passing_yards = calculate_weighted_average(passing_vals)
    avg_sacks_made = calculate_weighted_average(sacks_vals)  # defensive stat tracked on offense
    
    # defensive averages with recency weighting
    avg_yards_allowed = calculate_weighted_average(yards_allowed_vals)
    avg_yards_per_play_allowed = calculate_weighted_average(yards_per_play_allowed_vals)
    avg_points_allowed = calculate_weighted_average(points_allowed_vals)
    avg_rushing_yards_allowed = calculate_weighted_average(rushing_allowed_vals)
    avg_passing_yards_allowed = calculate_weighted_average(passing_allowed_vals)
    avg_sacks_allowed = calculate_weighted_average(sacks_allowed_vals)
    
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
    
    # turnover differential (takeaways - giveaways)
    takeaways = avg_sacks_made  # proxy - ideally would track INTs + fumbles recovered
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
            'turnovers': avg_turnovers_committed,
            'rushing_yards': avg_rushing_yards,
            'passing_yards': avg_passing_yards,
            'sacks_made': avg_sacks_made
        },
        'defense': {
            'yards_allowed': avg_yards_allowed,
            'yards_per_play_allowed': avg_yards_per_play_allowed,
            'points_allowed': avg_points_allowed,
            'sacks_allowed': avg_sacks_allowed,
            'rushing_yards_allowed': avg_rushing_yards_allowed,
            'passing_yards_allowed': avg_passing_yards_allowed
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
    
    games = [g for g in teams_data[team] if not g.get('postseason', False)]
    
    if len(games) < 2:
        return {'bounce_back_score': 0, 'factors': [], 'has_bounce_back_potential': False}
    
    bounce_back_score = 0
    factors = []
    
    # only consider if team has recent losses
    recent_games = games[-3:] if len(games) >= 3 else games
    recent_losses = [g for g in recent_games if g['result'] == 'L']
    
    if len(recent_losses) < 2:  # need at least 2 recent losses to consider bounce-back
        return {'bounce_back_score': 0, 'factors': [], 'has_bounce_back_potential': False}
    
    # 1. TURNOVER LUCK - bad TO margin
    last_game = games[-1]
    if last_game['result'] == 'L':
        last_game_to_margin = last_game['off_stats'].get('sacks', 0) - last_game['off_stats'].get('turnovers', 0)
        if last_game_to_margin <= -2:
            bounce_back_score += 1.5
            factors.append("Bad turnover luck in last game")
    
    # 2. 3RD DOWN EXTREMES in recent games
    if len(recent_games) >= 2:
        recent_3rd_down = sum(g['off_stats'].get('thirdDownRate', 0) for g in recent_games) / len(recent_games)
        if recent_3rd_down <= 0.25 and recent_3rd_down > 0:
            bounce_back_score += 1.0
            factors.append("Extreme 3rd down struggles (likely to improve)")
    
    # 3. UNDERLYING PERFORMANCE - played well but lost
    for loss_game in recent_losses:
        their_yards = loss_game['off_stats'].get('totalYards', 0)
        opp_yards = loss_game['def_stats'].get('totalYards', 0)
        
        if their_yards > opp_yards + 50:
            bounce_back_score += 1.5
            factors.append("Outgained opponent(s) but lost")
            break
        
        their_ypp = loss_game['off_stats'].get('yardsPerPlay', 0)
        opp_ypp = loss_game['def_stats'].get('yardsPerPlay', 0)
        
        if their_ypp > opp_ypp + 0.5:
            bounce_back_score += 1.0
            factors.append("Better efficiency metrics in loss")
            break
    
    # 4. CAPPED BLOWOUT MARGINS
    for loss_game in recent_losses:
        loss_margin = loss_game['score_against'] - loss_game['score_for']
        if loss_margin >= 20:
            bounce_back_score += 0.5
            factors.append("Blowout loss (less predictive)")
            break
    
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
        if not game.get('postseason', False):
            opp = game['opponent']
            opp_avg = calculate_team_averages(opp, teams_data, exclude_postseason=True)
            if opp_avg:
                opponent_win_rates.append(opp_avg['win_rate'])
    
    if not opponent_win_rates:
        return 0.5
    
    return sum(opponent_win_rates) / len(opponent_win_rates)


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
        tm_avg = calculate_team_averages(tm, teams_data, exclude_postseason=True)
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
    games = [g for g in teams_data[team] if not g.get('postseason', False)]
    
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
    print(f"    Rushing: {home_avg['offense']['rushing_yards']:.1f} yds/game | "
          f"Passing: {home_avg['offense']['passing_yards']:.1f} yds/game")
    print(f"  Defense: {home_avg['defense']['points_allowed']:.1f} pts allowed/game, "
          f"{home_avg['defense']['yards_per_play_allowed']:.1f} yds/play allowed, "
          f"{home_avg['offense']['sacks_made']:.1f} sacks/game")
    print(f"    vs Rush: {home_avg['defense']['rushing_yards_allowed']:.1f} yds/game | "
          f"vs Pass: {home_avg['defense']['passing_yards_allowed']:.1f} yds/game")
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
    print(f"    Rushing: {away_avg['offense']['rushing_yards']:.1f} yds/game | "
          f"Passing: {away_avg['offense']['passing_yards']:.1f} yds/game")
    print(f"  Defense: {away_avg['defense']['points_allowed']:.1f} pts allowed/game, "
          f"{away_avg['defense']['yards_per_play_allowed']:.1f} yds/play allowed, "
          f"{away_avg['offense']['sacks_made']:.1f} sacks/game")
    print(f"    vs Rush: {away_avg['defense']['rushing_yards_allowed']:.1f} yds/game | "
          f"vs Pass: {away_avg['defense']['passing_yards_allowed']:.1f} yds/game")
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
    
    home_points = 0
    away_points = 0
    
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
        home_points -= 2.0
        print(f"    >> {home_team} stat-padding vs WEAK defenses (-2.0)")
    
    if away_strength_adj['faced_tough_defenses'] and away_avg['offense']['points_scored'] > 22:
        away_points += 1.5
        print(f"    >> {away_team} scoring well vs ELITE defenses (+1.5)")
    elif away_strength_adj['faced_weak_defenses']:
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
        
        # Base home field advantage ranges from 1.5 to 4.0 based on actual splits (stronger in CFB)
        if home_advantage_strength > 0.25:  # Dominant home team
            hfa_points = 4.0
            print(f"\nHome Field Advantage: {home_team} has DOMINANT home advantage (+4.0)")
            print(f"  ({home_avg['splits']['home_win_rate']:.1%} home vs {home_avg['splits']['away_win_rate']:.1%} away)")
        elif home_advantage_strength > 0.15:  # Strong home team
            hfa_points = 3.5
            print(f"\nHome Field Advantage: {home_team} has STRONG home advantage (+3.5)")
            print(f"  ({home_avg['splits']['home_win_rate']:.1%} home vs {home_avg['splits']['away_win_rate']:.1%} away)")
        elif home_advantage_strength > 0.05:  # Moderate home team
            hfa_points = 3.0
            print(f"\nHome Field Advantage: {home_team} has moderate home advantage (+3.0)")
            print(f"  ({home_avg['splits']['home_win_rate']:.1%} home vs {home_avg['splits']['away_win_rate']:.1%} away)")
        elif home_advantage_strength < -0.10:  # Actually worse at home!
            hfa_points = 1.0
            print(f"\nHome Field Advantage: {home_team} minimal advantage (+1.0)")
            print(f"  WARNING: Team performs worse at home ({home_avg['splits']['home_win_rate']:.1%} home vs {home_avg['splits']['away_win_rate']:.1%} away)")
        else:  # Neutral home effect
            hfa_points = 2.5
            print(f"\nHome Field Advantage: {home_team} slight advantage (+2.5)")
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
    
    # NEW: Red Zone Efficiency (approximated by points per 100 yards)
    print(f"\nRed Zone Efficiency (Finishing Drives):")
    home_rz_eff = (home_avg['offense']['points_scored'] / (home_avg['offense']['total_yards'] / 100)) if home_avg['offense']['total_yards'] > 0 else 0
    away_rz_eff = (away_avg['offense']['points_scored'] / (away_avg['offense']['total_yards'] / 100)) if away_avg['offense']['total_yards'] > 0 else 0
    
    print(f"  {home_team}: {home_rz_eff:.2f} points per 100 yards")
    print(f"  {away_team}: {away_rz_eff:.2f} points per 100 yards")
    
    if home_rz_eff > away_rz_eff * 1.15:
        home_points += 1.5
        print(f"    >> {home_team} significantly better at finishing drives (+1.5)")
    elif home_rz_eff > away_rz_eff * 1.05:
        home_points += 0.75
        print(f"    >> {home_team} better at finishing drives (+0.75)")
    elif away_rz_eff > home_rz_eff * 1.15:
        away_points += 1.5
        print(f"    >> {away_team} significantly better at finishing drives (+1.5)")
    elif away_rz_eff > home_rz_eff * 1.05:
        away_points += 0.75
        print(f"    >> {away_team} better at finishing drives (+0.75)")
    
    # 8. UPDATED: Win Rate Factor (reduced weight) + Pythagorean Expectation
    print(f"\nWin Rate & Performance Indicators:")
    
    # Actual win rate factor (reduced from 5.0 to 3.0)
    home_win_pts = home_avg['win_rate'] * 3.0
    away_win_pts = away_avg['win_rate'] * 3.0
    home_points += home_win_pts
    away_points += away_win_pts
    
    print(f"  {home_team} Win Rate: +{home_win_pts:.1f} ({home_avg['wins']}-{home_avg['games_played'] - home_avg['wins']}, {home_avg['win_rate']:.1%})")
    print(f"  {away_team} Win Rate: +{away_win_pts:.1f} ({away_avg['wins']}-{away_avg['games_played'] - away_avg['wins']}, {away_avg['win_rate']:.1%})")
    
    # Pythagorean expectation - identifies over/underperforming teams
    home_pyth_diff = home_avg['win_rate'] - home_avg['pythagorean_win_rate']
    away_pyth_diff = away_avg['win_rate'] - away_avg['pythagorean_win_rate']
    
    print(f"\n  Pythagorean Analysis (regression candidates):")
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
    print("College Football Game Predictor - Advanced Analysis")
    print("=" * 100)
    print("\nReading CFB data with detailed stats...")
    
    # read and parse data
    teams_data = read_cfb_data()
    
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
    print("Enter team names (use full names as they appear in cfbData.txt)")
    print("Examples: 'Alabama Crimson Tide', 'Ohio State Buckeyes', 'Georgia Bulldogs', etc.\n")
    
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
