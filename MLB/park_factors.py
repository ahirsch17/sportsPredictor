"""
MLB Park Factors Database
Based on MLB park statistics and historical data
"""

# Park factors: 100 = neutral, >100 = hitter-friendly, <100 = pitcher-friendly
PARK_FACTORS = {
    'Arizona Diamondbacks': {
        'name': 'Chase Field',
        'run_factor': 102,
        'hr_factor': 106,
        'altitude': 1086,  # feet
        'roof': 'retractable'
    },
    'Atlanta Braves': {
        'name': 'Truist Park',
        'run_factor': 99,
        'hr_factor': 98,
        'altitude': 1050,
        'roof': 'open'
    },
    'Baltimore Orioles': {
        'name': 'Oriole Park at Camden Yards',
        'run_factor': 104,
        'hr_factor': 109,
        'altitude': 33,
        'roof': 'open'
    },
    'Boston Red Sox': {
        'name': 'Fenway Park',
        'run_factor': 103,
        'hr_factor': 101,
        'altitude': 20,
        'roof': 'open',
        'notes': 'Green Monster in left field'
    },
    'Chicago Cubs': {
        'name': 'Wrigley Field',
        'run_factor': 107,
        'hr_factor': 110,
        'altitude': 595,
        'roof': 'open',
        'notes': 'Wind plays huge factor'
    },
    'Chicago White Sox': {
        'name': 'Guaranteed Rate Field',
        'run_factor': 101,
        'hr_factor': 103,
        'altitude': 595,
        'roof': 'open'
    },
    'Cincinnati Reds': {
        'name': 'Great American Ball Park',
        'run_factor': 106,
        'hr_factor': 112,
        'altitude': 550,
        'roof': 'open',
        'notes': 'Very hitter-friendly'
    },
    'Cleveland Guardians': {
        'name': 'Progressive Field',
        'run_factor': 98,
        'hr_factor': 95,
        'altitude': 653,
        'roof': 'open'
    },
    'Colorado Rockies': {
        'name': 'Coors Field',
        'run_factor': 115,
        'hr_factor': 124,
        'altitude': 5200,  # HIGHEST IN MLB
        'roof': 'open',
        'notes': 'EXTREME hitter park due to altitude'
    },
    'Detroit Tigers': {
        'name': 'Comerica Park',
        'run_factor': 96,
        'hr_factor': 92,
        'altitude': 585,
        'roof': 'open',
        'notes': 'Pitcher-friendly, large outfield'
    },
    'Houston Astros': {
        'name': 'Minute Maid Park',
        'run_factor': 101,
        'hr_factor': 100,
        'altitude': 43,
        'roof': 'retractable'
    },
    'Kansas City Royals': {
        'name': 'Kauffman Stadium',
        'run_factor': 99,
        'hr_factor': 97,
        'altitude': 910,
        'roof': 'open'
    },
    'Los Angeles Angels': {
        'name': 'Angel Stadium',
        'run_factor': 98,
        'hr_factor': 97,
        'altitude': 160,
        'roof': 'open'
    },
    'Los Angeles Dodgers': {
        'name': 'Dodger Stadium',
        'run_factor': 97,
        'hr_factor': 96,
        'altitude': 340,
        'roof': 'open',
        'notes': 'Pitcher-friendly'
    },
    'Miami Marlins': {
        'name': 'loanDepot park',
        'run_factor': 95,
        'hr_factor': 94,
        'altitude': 10,
        'roof': 'retractable',
        'notes': 'Pitcher-friendly'
    },
    'Milwaukee Brewers': {
        'name': 'American Family Field',
        'run_factor': 101,
        'hr_factor': 100,
        'altitude': 635,
        'roof': 'retractable'
    },
    'Minnesota Twins': {
        'name': 'Target Field',
        'run_factor': 100,
        'hr_factor': 101,
        'altitude': 840,
        'roof': 'open'
    },
    'New York Mets': {
        'name': 'Citi Field',
        'run_factor': 97,
        'hr_factor': 95,
        'altitude': 14,
        'roof': 'open',
        'notes': 'Pitcher-friendly'
    },
    'New York Yankees': {
        'name': 'Yankee Stadium',
        'run_factor': 103,
        'hr_factor': 108,
        'altitude': 55,
        'roof': 'open',
        'notes': 'Short right field porch'
    },
    'Oakland Athletics': {
        'name': 'Oakland Coliseum',
        'run_factor': 97,
        'hr_factor': 96,
        'altitude': 25,
        'roof': 'open',
        'notes': 'Large foul territory'
    },
    'Philadelphia Phillies': {
        'name': 'Citizens Bank Park',
        'run_factor': 104,
        'hr_factor': 107,
        'altitude': 39,
        'roof': 'open'
    },
    'Pittsburgh Pirates': {
        'name': 'PNC Park',
        'run_factor': 98,
        'hr_factor': 97,
        'altitude': 730,
        'roof': 'open'
    },
    'San Diego Padres': {
        'name': 'Petco Park',
        'run_factor': 94,
        'hr_factor': 93,
        'altitude': 20,
        'roof': 'open',
        'notes': 'Very pitcher-friendly'
    },
    'San Francisco Giants': {
        'name': 'Oracle Park',
        'run_factor': 92,
        'hr_factor': 88,
        'altitude': 10,
        'roof': 'open',
        'notes': 'MOST pitcher-friendly, wind from bay'
    },
    'Seattle Mariners': {
        'name': 'T-Mobile Park',
        'run_factor': 97,
        'hr_factor': 95,
        'altitude': 10,
        'roof': 'retractable'
    },
    'St. Louis Cardinals': {
        'name': 'Busch Stadium',
        'run_factor': 100,
        'hr_factor': 100,
        'altitude': 465,
        'roof': 'open'
    },
    'Tampa Bay Rays': {
        'name': 'Tropicana Field',
        'run_factor': 96,
        'hr_factor': 97,
        'altitude': 12,
        'roof': 'dome'
    },
    'Texas Rangers': {
        'name': 'Globe Life Field',
        'run_factor': 105,
        'hr_factor': 108,
        'altitude': 551,
        'roof': 'retractable',
        'notes': 'New stadium, hitter-friendly'
    },
    'Toronto Blue Jays': {
        'name': 'Rogers Centre',
        'run_factor': 101,
        'hr_factor': 102,
        'altitude': 300,
        'roof': 'retractable'
    },
    'Washington Nationals': {
        'name': 'Nationals Park',
        'run_factor': 99,
        'hr_factor': 100,
        'altitude': 25,
        'roof': 'open'
    }
}


def get_park_factor(team_name):
    """
    Gets park factor for a team
    """
    return PARK_FACTORS.get(team_name, {
        'name': 'Unknown',
        'run_factor': 100,
        'hr_factor': 100,
        'altitude': 0,
        'roof': 'open'
    })


def calculate_park_adjustment(home_team, stat_type='run'):
    """
    Calculates adjustment multiplier for park effects
    Returns: multiplier (e.g., 1.15 for Coors, 0.92 for Oracle)
    """
    park = get_park_factor(home_team)
    
    if stat_type == 'run':
        factor = park['run_factor']
    elif stat_type == 'hr':
        factor = park['hr_factor']
    else:
        factor = 100
    
    # Convert to multiplier (100 = 1.0x)
    multiplier = factor / 100.0
    return multiplier


def get_park_impact_score(home_team):
    """
    Gets impact score for prediction adjustments
    Returns: -5.0 to +5.0 (negative = pitcher park, positive = hitter park)
    """
    park = get_park_factor(home_team)
    run_factor = park['run_factor']
    
    # Extreme parks get bigger adjustments
    if run_factor >= 115:  # Coors
        return 5.0
    elif run_factor >= 106:  # Very hitter-friendly
        return 3.0
    elif run_factor >= 103:  # Hitter-friendly
        return 1.5
    elif run_factor <= 92:  # Oracle, Petco (very pitcher-friendly)
        return -3.0
    elif run_factor <= 96:  # Pitcher-friendly
        return -1.5
    else:
        return 0.0  # Neutral park


if __name__ == "__main__":
    print("MLB Park Factors Database\n")
    print("Most Hitter-Friendly Parks:")
    sorted_parks = sorted(PARK_FACTORS.items(), key=lambda x: x[1]['run_factor'], reverse=True)
    for i, (team, park) in enumerate(sorted_parks[:5]):
        print(f"  {i+1}. {team}: {park['name']} (Factor: {park['run_factor']}, Altitude: {park['altitude']}ft)")
    
    print("\nMost Pitcher-Friendly Parks:")
    for i, (team, park) in enumerate(sorted_parks[-5:]):
        print(f"  {i+1}. {team}: {park['name']} (Factor: {park['run_factor']})")

