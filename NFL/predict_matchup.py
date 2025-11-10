"""
Quick matchup prediction script
"""

from predictor import read_nfl_data, advanced_prediction
from injuryextract import get_injury_data
import sys

# Team setup
home_team = "Cincinnati Bengals"
away_team = "Chicago Bears"
is_neutral = False

print("Loading NFL data...")
teams_data = read_nfl_data()

if teams_data is None:
    print("Failed to load data. Exiting.")
    sys.exit(1)

print(f"Data loaded: {len(teams_data)} teams")

# Fetch injury data
print("Fetching injury data...")
try:
    injury_data = get_injury_data()
    if injury_data:
        total_injuries = sum(len(injuries) for injuries in injury_data.values())
        print(f"Injury data loaded: {total_injuries} total injuries")
    else:
        injury_data = None
        print("Could not fetch injury data")
except Exception as e:
    injury_data = None
    print(f"Error loading injury data: {e}")

print(f"\n{'=' * 100}")
print(f"GAME PREDICTION: {away_team} @ {home_team}")
print(f"{'=' * 100}\n")

# Get prediction
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
        print(f"Confidence: {confidence:.1f}%")
    elif away_points > home_points:
        diff = away_points - home_points
        confidence = min(diff / 6 * 100, 95)
        print(f"PREDICTION: {away_team} wins")
        print(f"Confidence: {confidence:.1f}%")
    else:
        print("PREDICTION: Too close to call")
        print("Confidence: 50.0% (toss-up)")
    
    print(f"\n{'=' * 100}")
else:
    print("ERROR: Could not generate prediction")


