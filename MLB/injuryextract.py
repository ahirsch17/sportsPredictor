"""
MLB Injury Data Extractor
Fetches current injury reports from ESPN API
"""

import requests
import json
from datetime import datetime


def get_injury_data():
    """
    fetches current MLB injury data from ESPN API
    returns dict: {team_name: [injuries]}
    """
    injury_url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/injuries"
    
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


def detect_position_from_comment(player_name, comment):
    """
    attempts to detect player position from comments
    """
    comment_lower = comment.lower()
    
    # Starting Pitcher (most critical in MLB)
    if any(word in comment_lower for word in ['starting pitcher', 'sp ', 'starter', 'pitched', 'innings pitched', 'earned runs']):
        return 'SP'
    
    # Relief Pitcher / Closer
    if any(word in comment_lower for word in ['relief', 'reliever', 'closer', 'bullpen', 'save opportunity']):
        return 'RP'
    
    # Catcher
    if any(word in comment_lower for word in ['catcher', ' c ', 'behind the plate', 'catching']):
        return 'C'
    
    # First Base
    if any(word in comment_lower for word in ['first base', '1b ', 'first baseman']):
        return '1B'
    
    # Second Base
    if any(word in comment_lower for word in ['second base', '2b ', 'second baseman']):
        return '2B'
    
    # Third Base
    if any(word in comment_lower for word in ['third base', '3b ', 'third baseman']):
        return '3B'
    
    # Shortstop
    if any(word in comment_lower for word in ['shortstop', 'ss ']):
        return 'SS'
    
    # Outfield
    if any(word in comment_lower for word in ['outfield', 'of ', 'center field', 'cf ', 'left field', 'lf ', 'right field', 'rf ']):
        return 'OF'
    
    # Designated Hitter
    if any(word in comment_lower for word in ['designated hitter', 'dh ', ' dh,']):
        return 'DH'
    
    return 'UNKNOWN'


def calculate_injury_impact(team_name, injury_data):
    """
    calculates injury impact score for MLB team with position-based weighting
    returns dict with impact assessment
    """
    if not injury_data or team_name not in injury_data:
        return {
            'total_injuries': 0,
            'key_injuries': 0,
            'impact_score': 0,
            'injury_list': [],
            'sp_injured': False,
            'closer_injured': False
        }
    
    team_injuries = injury_data[team_name]
    
    # Position-based impact weights for MLB
    position_weights = {
        'SP': 12.0,      # Starting Pitcher - MOST CRITICAL in MLB
        'RP': 3.0,       # Relief Pitcher / Closer - Important for late innings
        'C': 3.5,        # Catcher - Defensive anchor, game caller
        'SS': 3.0,       # Shortstop - Key defensive position
        '1B': 2.5,       # First Base - Power hitter typically
        '2B': 2.5,       # Second Base
        '3B': 2.5,       # Third Base
        'OF': 2.0,       # Outfielder
        'DH': 2.0,       # Designated Hitter
        'UNKNOWN': 1.0   # Unknown/Bench players
    }
    
    # Status multipliers
    status_multipliers = {
        'out': 1.0,          # Definitely missing
        '60-day il': 1.0,    # MLB's 60-day injured list (long-term)
        '15-day il': 0.8,    # MLB's 15-day injured list (short-term)
        '10-day il': 0.7,    # MLB's 10-day injured list (very short)
        'day-to-day': 0.3,   # Game-time decision
        'active': 0.0        # Playing normally
    }
    
    # categorize injuries by status (EXCLUDE ACTIVE PLAYERS)
    actual_injuries = [i for i in team_injuries if i['status'].lower() != 'active']
    out = [i for i in actual_injuries if any(x in i['status'].lower() for x in ['out', '60-day', '15-day', '10-day'])]
    dtd = [i for i in actual_injuries if 'day-to-day' in i['status'].lower()]
    
    # calculate position-weighted impact score
    impact_score = 0
    key_injuries = []
    sp_injured = False
    closer_injured = False
    
    for injury in actual_injuries:
        player = injury['player_name']
        status = injury['status'].lower()
        comment = injury.get('detail', '')
        
        # Detect position
        position = detect_position_from_comment(player, comment)
        
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
        
        # Track pitcher injuries specifically (most important in baseball)
        if position == 'SP' and status_mult > 0.5:
            sp_injured = True
        if position == 'RP' and 'closer' in comment.lower() and status_mult > 0.5:
            closer_injured = True
        
        # Add to key injuries list if significant impact
        if player_impact >= 2.0:  # Threshold for "key" injury
            key_injuries.append(f"{player} ({position}, {injury['status']})")
    
    return {
        'total_injuries': len(actual_injuries),
        'out': len(out),
        'day_to_day': len(dtd),
        'key_injuries': len(key_injuries),
        'impact_score': impact_score,
        'injury_list': key_injuries,
        'sp_injured': sp_injured,
        'closer_injured': closer_injured
    }


def write_injury_report(injury_data):
    """
    writes injury data to file for reference
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open('injuries_current.txt', 'w', encoding='utf-8') as f:
        f.write(f"MLB Injury Report - Updated: {timestamp}\n")
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
    print("MLB Injury Data Extractor")
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
            if impact['sp_injured']:
                print(f"    ⚠️  Starting Pitcher injured!")
        
        # write to file
        print()
        write_injury_report(injury_data)
    else:
        print("Failed to retrieve injury data")


if __name__ == "__main__":
    main()

