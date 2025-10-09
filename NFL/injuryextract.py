"""
NFL Injury Data Extractor
Fetches current injury reports from ESPN API
"""

import requests
import json
from datetime import datetime


def get_injury_data():
    """
    fetches current NFL injury data from ESPN API
    returns dict: {team_name: [injuries]}
    """
    injury_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries"
    
    try:
        response = requests.get(injury_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        injury_data = {}
        
        if 'injuries' in data:
            for team_data in data['injuries']:
                team_name = team_data.get('displayName', 'Unknown')
                injuries = team_data.get('injuries', [])
                
                # parse injury details
                team_injuries = []
                for injury in injuries:
                    athlete = injury.get('athlete', {})
                    
                    injury_info = {
                        'player_name': athlete.get('displayName', 'Unknown'),
                        'status': injury.get('status', 'Unknown'),
                        'detail': injury.get('shortComment', ''),
                        'date': injury.get('date', '')
                    }
                    
                    team_injuries.append(injury_info)
                
                injury_data[team_name] = team_injuries
        
        return injury_data
        
    except Exception as e:
        print(f"Error fetching injury data: {e}")
        return None


def detect_position_from_name_and_comment(player_name, comment):
    """
    attempts to detect player position from name patterns and comments
    """
    name_lower = player_name.lower()
    comment_lower = comment.lower()
    
    # QB detection (most critical)
    if any(word in comment_lower for word in ['quarterback', 'qb ', ' qb,', 'passing', 'threw for', 'completed']):
        return 'QB'
    
    # RB detection
    if any(word in comment_lower for word in ['running back', 'rb ', 'carried', 'rushing', 'carries for']):
        return 'RB'
    
    # WR detection  
    if any(word in comment_lower for word in ['receiver', 'wr ', 'caught', 'receptions', 'targets', 'receiving']):
        return 'WR'
    
    # TE detection
    if any(word in comment_lower for word in ['tight end', 'te ']):
        return 'TE'
    
    # Defensive positions
    if any(word in comment_lower for word in ['linebacker', 'lb ', 'tackles']):
        return 'LB'
    if any(word in comment_lower for word in ['cornerback', 'cb ', 'coverage', 'pass defense']):
        return 'CB'
    if any(word in comment_lower for word in ['safety', 'ss ', 'fs ']):
        return 'S'
    if any(word in comment_lower for word in ['defensive end', 'de ', 'edge', 'sacks']):
        return 'DE'
    if any(word in comment_lower for word in ['defensive tackle', 'dt ']):
        return 'DT'
    
    # O-line
    if any(word in comment_lower for word in ['offensive line', 'ol ', 'guard', 'tackle', 'center']):
        return 'OL'
    
    return 'UNKNOWN'


def calculate_injury_impact(team_name, injury_data):
    """
    calculates injury impact score for a team with position-based weighting
    returns dict with impact assessment
    """
    if not injury_data or team_name not in injury_data:
        return {
            'total_injuries': 0,
            'key_injuries': 0,
            'impact_score': 0,
            'injury_list': [],
            'qb_injured': False
        }
    
    team_injuries = injury_data[team_name]
    
    # Position-based impact weights (when player is OUT/IR)
    position_weights = {
        'QB': 10.0,      # Critical - most important position
        'WR': 2.5,       # Key offensive weapons
        'RB': 2.0,       # Important for offense
        'TE': 2.0,       # Important for offense
        'OL': 2.5,       # Critical for QB protection
        'DE': 2.0,       # Key pass rushers
        'CB': 2.0,       # Key coverage
        'LB': 1.5,       # Solid contributors
        'S': 1.5,        # Solid contributors
        'DT': 1.5,       # Solid contributors
        'UNKNOWN': 1.0   # Default for unknown positions
    }
    
    # Status multipliers
    status_multipliers = {
        'out': 1.0,          # Definitely missing
        'ir': 1.0,           # Season-ending
        'injured reserve': 1.0,
        'doubtful': 0.6,     # 75% chance of missing
        'questionable': 0.2, # 50% chance, may be limited
        'active': 0.0        # NOT injured! Playing normally
    }
    
    # categorize injuries by status (EXCLUDE ACTIVE PLAYERS)
    actual_injuries = [i for i in team_injuries if i['status'].lower() != 'active']
    out = [i for i in actual_injuries if i['status'].lower() in ['out', 'ir', 'injured reserve']]
    doubtful = [i for i in actual_injuries if 'doubtful' in i['status'].lower()]
    questionable = [i for i in actual_injuries if 'questionable' in i['status'].lower()]
    
    # calculate position-weighted impact score
    impact_score = 0
    key_injuries = []
    qb_injured = False
    
    for injury in actual_injuries:
        player = injury['player_name']
        status = injury['status'].lower()
        comment = injury.get('detail', '')
        
        # Detect position
        position = detect_position_from_name_and_comment(player, comment)
        
        # Get weights
        pos_weight = position_weights.get(position, 1.0)
        status_mult = 0.0
        for key, mult in status_multipliers.items():
            if key in status:
                status_mult = mult
                break
        
        # Calculate this player's impact
        player_impact = pos_weight * status_mult
        impact_score += player_impact
        
        # Track QB injuries specifically
        if position == 'QB' and status_mult > 0.5:
            qb_injured = True
        
        # Add to key injuries list if significant impact
        if player_impact >= 2.0:  # Threshold for "key" injury
            key_injuries.append(f"{player} ({position}, {injury['status']})")
    
    return {
        'total_injuries': len(actual_injuries),  # Only count real injuries, not active
        'out': len(out),
        'doubtful': len(doubtful),
        'questionable': len(questionable),
        'key_injuries': len(key_injuries),
        'impact_score': impact_score,
        'injury_list': key_injuries,
        'qb_injured': qb_injured
    }


def write_injury_report(injury_data):
    """
    writes injury data to file for reference
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open('injuries_current.txt', 'w', encoding='utf-8') as f:
        f.write(f"NFL Injury Report - Updated: {timestamp}\n")
        f.write("=" * 100 + "\n\n")
        
        if not injury_data:
            f.write("No injury data available.\n")
            return
        
        for team_name in sorted(injury_data.keys()):
            injuries = injury_data[team_name]
            
            if not injuries:
                continue
            
            f.write(f"\n{team_name} ({len(injuries)} injuries)\n")
            f.write("-" * 80 + "\n")
            
            for injury in injuries:
                f.write(f"  {injury['player_name']}\n")
                f.write(f"    Status: {injury['status']}\n")
                if injury['detail']:
                    f.write(f"    Detail: {injury['detail']}\n")
                f.write("\n")
        
        f.write(f"\n{'=' * 100}\n")
        f.write(f"Total teams with injuries: {len(injury_data)}\n")
    
    print(f"Injury report written to injuries_current.txt")


def main():
    """
    main execution function
    """
    print("NFL Injury Data Extractor")
    print("=" * 100)
    
    print("\nFetching current injury data from ESPN API...")
    injury_data = get_injury_data()
    
    if injury_data:
        print(f"Successfully retrieved injury data for {len(injury_data)} teams\n")
        
        # show summary
        total_injuries = sum(len(injuries) for injuries in injury_data.values())
        print(f"Total injuries across league: {total_injuries}\n")
        
        # show teams with most injuries
        teams_by_injuries = sorted(injury_data.items(), key=lambda x: len(x[1]), reverse=True)
        print("Teams with most injuries:")
        for team, injuries in teams_by_injuries[:5]:
            impact = calculate_injury_impact(team, injury_data)
            print(f"  {team}: {len(injuries)} injuries (Impact Score: {impact['impact_score']:.1f})")
        
        # write to file
        print()
        write_injury_report(injury_data)
    else:
        print("Failed to retrieve injury data")


if __name__ == "__main__":
    main()

