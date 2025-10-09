"""
MLB Pitcher Statistics Tracker
Tracks starting pitcher and bullpen performance
"""

import requests
import json


def get_pitcher_stats(pitcher_id):
    """
    Gets detailed stats for a pitcher from ESPN API
    """
    try:
        url = f"https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/seasons/2024/athletes/{pitcher_id}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Get statistics link
        if 'statistics' in data:
            stats_url = data['statistics']['$ref']
            stats_response = requests.get(stats_url, timeout=5)
            stats_response.raise_for_status()
            stats_data = stats_response.json()
            
            # Extract pitching stats
            for split in stats_data.get('splits', {}).get('categories', []):
                if split.get('name') == 'pitching':
                    stats = {}
                    for stat in split.get('stats', []):
                        stats[stat['name']] = stat.get('value', 0)
                    
                    return {
                        'era': float(stats.get('earnedRunAverage', 0)),
                        'whip': float(stats.get('walksAndHitsPerInningPitched', 0)),
                        'wins': int(stats.get('wins', 0)),
                        'losses': int(stats.get('losses', 0)),
                        'innings': float(stats.get('inningsPitched', 0)),
                        'strikeouts': int(stats.get('strikeouts', 0)),
                        'walks': int(stats.get('walks', 0)),
                        'hits_allowed': int(stats.get('hits', 0)),
                        'hr_allowed': int(stats.get('homeRunsAllowed', 0))
                    }
        
        return None
        
    except Exception as e:
        return None


def calculate_pitcher_quality_score(pitcher_stats):
    """
    Calculates pitcher quality score (0-100 scale)
    Higher = better pitcher
    """
    if not pitcher_stats:
        return 50  # Average
    
    score = 50  # Start at average
    
    # ERA (most important)
    era = pitcher_stats.get('era', 4.50)
    if era < 2.50:
        score += 20  # Ace
    elif era < 3.50:
        score += 10  # Very good
    elif era < 4.00:
        score += 5   # Good
    elif era > 5.50:
        score -= 15  # Poor
    elif era > 4.50:
        score -= 5   # Below average
    
    # WHIP (walks + hits per inning)
    whip = pitcher_stats.get('whip', 1.30)
    if whip < 1.00:
        score += 15  # Elite
    elif whip < 1.20:
        score += 8   # Excellent
    elif whip > 1.50:
        score -= 10  # Poor
    elif whip > 1.40:
        score -= 5   # Below average
    
    # Win-Loss record
    wins = pitcher_stats.get('wins', 0)
    losses = pitcher_stats.get('losses', 0)
    if wins + losses > 0:
        win_pct = wins / (wins + losses)
        if win_pct > 0.650:
            score += 10
        elif win_pct > 0.550:
            score += 5
        elif win_pct < 0.350:
            score -= 10
        elif win_pct < 0.450:
            score -= 5
    
    # Strikeout rate
    innings = pitcher_stats.get('innings', 1)
    k_per_9 = (pitcher_stats.get('strikeouts', 0) / innings) * 9 if innings > 0 else 0
    if k_per_9 > 10.0:
        score += 8   # Dominant
    elif k_per_9 > 8.5:
        score += 4   # Good
    elif k_per_9 < 6.0:
        score -= 5   # Below average
    
    # Clamp to 0-100
    return max(0, min(100, score))


def get_bullpen_stats(team_name, teams_data):
    """
    Calculate bullpen quality from relief pitcher performance
    This would need game-by-game relief pitcher data
    For now, estimate from late-inning runs allowed
    """
    if team_name not in teams_data:
        return {'quality_score': 50, 'era': 4.00}
    
    # Placeholder - would track relief pitchers specifically
    games = teams_data[team_name]
    
    # Estimate bullpen performance from overall pitching
    runs_allowed = []
    for game in games:
        runs_allowed.append(game['runs_against'])
    
    if runs_allowed:
        avg_runs_allowed = sum(runs_allowed) / len(runs_allowed)
        
        # Estimate bullpen ERA (typically ~0.5 higher than team ERA)
        bullpen_era = avg_runs_allowed + 0.5
        
        # Convert to quality score
        if bullpen_era < 3.00:
            quality_score = 80
        elif bullpen_era < 3.50:
            quality_score = 70
        elif bullpen_era < 4.00:
            quality_score = 60
        elif bullpen_era < 4.50:
            quality_score = 50
        elif bullpen_era < 5.00:
            quality_score = 40
        else:
            quality_score = 30
        
        return {
            'quality_score': quality_score,
            'era': bullpen_era
        }
    
    return {'quality_score': 50, 'era': 4.00}


def compare_pitchers(home_pitcher_stats, away_pitcher_stats):
    """
    Compares two starting pitchers and returns advantage
    Returns: points to award to home team (negative = away team advantage)
    """
    home_score = calculate_pitcher_quality_score(home_pitcher_stats)
    away_score = calculate_pitcher_quality_score(away_pitcher_stats)
    
    difference = home_score - away_score
    
    # Convert score difference to prediction points
    # Pitching matchup is CRITICAL in baseball
    if difference >= 30:
        return 5.0, "Home pitcher significantly better (ace vs weak)"
    elif difference >= 20:
        return 3.5, "Home pitcher much better"
    elif difference >= 10:
        return 2.0, "Home pitcher better"
    elif difference >= 5:
        return 1.0, "Home pitcher slightly better"
    elif difference <= -30:
        return -5.0, "Away pitcher significantly better (ace vs weak)"
    elif difference <= -20:
        return -3.5, "Away pitcher much better"
    elif difference <= -10:
        return -2.0, "Away pitcher better"
    elif difference <= -5:
        return -1.0, "Away pitcher slightly better"
    else:
        return 0.0, "Pitchers evenly matched"


# Sample pitcher data for testing (would come from API in production)
SAMPLE_PITCHERS = {
    'Gerrit Cole': {
        'era': 2.63,
        'whip': 1.03,
        'wins': 15,
        'losses': 4,
        'innings': 187.1,
        'strikeouts': 222,
        'walks': 41,
        'hits_allowed': 148,
        'hr_allowed': 18
    },
    'Average Pitcher': {
        'era': 4.20,
        'whip': 1.35,
        'wins': 9,
        'losses': 9,
        'innings': 150.0,
        'strikeouts': 130,
        'walks': 55,
        'hits_allowed': 155,
        'hr_allowed': 22
    },
    'Weak Pitcher': {
        'era': 5.85,
        'whip': 1.62,
        'wins': 4,
        'losses': 12,
        'innings': 120.0,
        'strikeouts': 85,
        'walks': 62,
        'hits_allowed': 145,
        'hr_allowed': 28
    }
}


if __name__ == "__main__":
    print("MLB Pitcher Quality Scores\n")
    
    for name, stats in SAMPLE_PITCHERS.items():
        score = calculate_pitcher_quality_score(stats)
        print(f"{name}:")
        print(f"  ERA: {stats['era']:.2f}, WHIP: {stats['whip']:.2f}")
        print(f"  Quality Score: {score}/100")
        print()
    
    print("\nMatchup Examples:")
    points, desc = compare_pitchers(SAMPLE_PITCHERS['Gerrit Cole'], SAMPLE_PITCHERS['Weak Pitcher'])
    print(f"Ace vs Weak: {points:+.1f} points ({desc})")
    
    points, desc = compare_pitchers(SAMPLE_PITCHERS['Average Pitcher'], SAMPLE_PITCHERS['Average Pitcher'])
    print(f"Even matchup: {points:+.1f} points ({desc})")

