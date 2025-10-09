"""
College Football Injury Data Extractor
Note: College injury reports are less standardized than NFL
This module provides a framework for manual injury tracking
"""

import json
from datetime import datetime


def get_injury_data():
    """
    reads injury data from injuries_current.txt
    returns dict of team injuries
    """
    injuries = {}
    
    try:
        with open('injuries_current.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_team = None
        for line in lines:
            line = line.strip()
            
            # team header
            if line and not line.startswith('-') and not line.startswith('Player'):
                current_team = line
                if current_team not in injuries:
                    injuries[current_team] = []
            
            # injury entry: "Player Name - Position - Status"
            elif line and '-' in line and current_team:
                parts = [p.strip() for p in line.split('-')]
                if len(parts) >= 3:
                    injuries[current_team].append({
                        'player': parts[0],
                        'position': parts[1],
                        'status': parts[2]
                    })
        
        return injuries
        
    except FileNotFoundError:
        return {}


def calculate_injury_impact(team, injury_data):
    """
    calculates injury impact for a college team
    """
    if not injury_data or team not in injury_data:
        return None
    
    team_injuries = injury_data[team]
    
    if not team_injuries:
        return None
    
    # position weights (college football specific)
    position_weights = {
        'QB': 5.0,      # Quarterback is critical
        'RB': 2.5,      # Running back
        'WR': 2.0,      # Wide receiver
        'TE': 1.5,      # Tight end
        'OL': 2.0,      # Offensive line
        'DL': 2.5,      # Defensive line
        'LB': 2.0,      # Linebacker
        'CB': 2.0,      # Cornerback
        'S': 1.5,       # Safety
        'K': 0.5,       # Kicker
        'P': 0.3        # Punter
    }
    
    # status weights
    status_weights = {
        'OUT': 1.0,
        'DOUBTFUL': 0.75,
        'QUESTIONABLE': 0.4,
        'PROBABLE': 0.1
    }
    
    impact_score = 0
    out_count = 0
    doubtful_count = 0
    questionable_count = 0
    qb_injured = False
    injury_list = []
    
    for injury in team_injuries:
        player = injury['player']
        position = injury['position'].upper()
        status = injury['status'].upper()
        
        # get weights
        pos_weight = position_weights.get(position, 1.0)
        status_weight = status_weights.get(status, 0.5)
        
        # calculate impact
        impact_score += pos_weight * status_weight
        
        # track counts
        if 'OUT' in status or 'IR' in status:
            out_count += 1
            injury_list.append(f"{player} ({position})")
        elif 'DOUBT' in status:
            doubtful_count += 1
            injury_list.append(f"{player} ({position})")
        elif 'QUESTION' in status:
            questionable_count += 1
        
        # QB injury flag
        if position == 'QB' and status in ['OUT', 'DOUBTFUL', 'IR']:
            qb_injured = True
    
    return {
        'total_injuries': len(team_injuries),
        'out': out_count,
        'doubtful': doubtful_count,
        'questionable': questionable_count,
        'impact_score': impact_score,
        'qb_injured': qb_injured,
        'injury_list': injury_list
    }


if __name__ == "__main__":
    print("College Football Injury Data")
    print("=" * 80)
    print("\nThis module tracks injuries manually.")
    print("Format for injuries_current.txt:")
    print("\nTeam Name")
    print("Player Name - Position - Status")
    print("Player Name - Position - Status")
    print("\nExample:")
    print("\nAlabama Crimson Tide")
    print("John Doe - QB - OUT")
    print("Jane Smith - WR - QUESTIONABLE")
    print("\n" + "=" * 80)

