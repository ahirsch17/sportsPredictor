"""
College Football Batch Predictor
Automatically predicts all games for a specific week
"""

import requests
import json
from predictor import read_cfb_data, advanced_prediction


def get_upcoming_games(week_num, season_type='regular', year=2024):
    """
    gets all games scheduled for a specific CFB week
    """
    base_api_url = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
    
    if season_type == 'postseason':
        season_type_num = 3
    else:
        season_type_num = 2
    
    params = {
        'seasontype': season_type_num,
        'week': week_num,
        'year': year,
        'groups': 80  # FBS only
    }
    
    try:
        response = requests.get(base_api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        games = []
        
        if 'events' in data:
            for event in data['events']:
                competitions = event.get('competitions', [])
                
                if competitions:
                    competition = competitions[0]
                    competitors = competition.get('competitors', [])
                    
                    if len(competitors) >= 2:
                        home_team = None
                        away_team = None
                        
                        for competitor in competitors:
                            team = competitor.get('team', {})
                            team_name = team.get('displayName', '')
                            home_away = competitor.get('homeAway', '')
                            
                            if home_away == 'home':
                                home_team = team_name
                            else:
                                away_team = team_name
                        
                        if home_team and away_team:
                            venue = competition.get('venue', {})
                            is_neutral = venue.get('neutral', False)
                            
                            games.append({
                                'home_team': home_team,
                                'away_team': away_team,
                                'is_neutral': is_neutral
                            })
        
        return games
        
    except Exception as e:
        print(f"Error getting games: {e}")
        return []


def batch_predict_week(week_num, season_type='regular'):
    """
    predicts all CFB games for a specific week
    """
    print("=" * 100)
    print(f"CFB BATCH PREDICTOR - {'POSTSEASON' if season_type == 'postseason' else 'WEEK'} {week_num}")
    print("=" * 100)
    print("\nLoading CFB data...")
    
    teams_data = read_cfb_data()
    
    if not teams_data:
        print("ERROR: Could not load CFB data. Run dataextract.py first.")
        return
    
    print(f"Data loaded! {len(teams_data)} teams found.\n")
    
    print(f"Fetching games for Week {week_num}...")
    games = get_upcoming_games(week_num, season_type)
    
    if not games:
        print(f"No games found for Week {week_num}")
        return
    
    print(f"Found {len(games)} games to predict\n")
    
    predictions = []
    failed_games = []
    
    for i, game in enumerate(games, 1):
        print(f"\n{'=' * 100}")
        print(f"GAME {i}/{len(games)}: {game['away_team']} @ {game['home_team']}")
        if game['is_neutral']:
            print("(NEUTRAL SITE - Bowl Game)")
        print(f"{'=' * 100}")
        
        try:
            result = advanced_prediction(
                game['home_team'], 
                game['away_team'], 
                teams_data, 
                game['is_neutral']
            )
            
            if result:
                home_points = result['home_points']
                away_points = result['away_points']
                
                if home_points > away_points:
                    diff = home_points - away_points
                    confidence = min(diff / 6 * 100, 95)
                    winner = game['home_team']
                elif away_points > home_points:
                    diff = away_points - home_points
                    confidence = min(diff / 6 * 100, 95)
                    winner = game['away_team']
                else:
                    confidence = 50
                    winner = "TIE"
                
                predictions.append({
                    'home_team': game['home_team'],
                    'away_team': game['away_team'],
                    'home_points': home_points,
                    'away_points': away_points,
                    'winner': winner,
                    'confidence': confidence,
                    'is_neutral': game['is_neutral'],
                    'status': 'predicted'
                })
            else:
                print(f"  Could not predict (missing team data)")
                failed_games.append({
                    'home_team': game['home_team'],
                    'away_team': game['away_team'],
                    'is_neutral': game['is_neutral'],
                    'reason': 'Missing team data'
                })
        
        except Exception as e:
            print(f"  Error: {e}")
            failed_games.append({
                'home_team': game['home_team'],
                'away_team': game['away_team'],
                'is_neutral': game['is_neutral'],
                'reason': str(e)
            })
            continue
    
    # summary
    print("\n\n")
    print("=" * 100)
    print(f"PREDICTIONS SUMMARY - WEEK {week_num}")
    print(f"Successfully predicted: {len(predictions)}/{len(games)} games")
    print("=" * 100)
    print()
    
    # sort by confidence (highest first)
    predictions.sort(key=lambda x: x['confidence'], reverse=True)
    
    for i, pred in enumerate(predictions, 1):
        home_marker = ">>>" if pred['winner'] == pred['home_team'] else "   "
        away_marker = ">>>" if pred['winner'] == pred['away_team'] else "   "
        neutral = " [NEUTRAL]" if pred['is_neutral'] else ""
        
        print(f"Game {i}:{neutral}")
        print(f"  {away_marker} {pred['away_team']}")
        print(f"  @")
        print(f"  {home_marker} {pred['home_team']}")
        print(f"  PREDICTION: {pred['winner']} wins ({pred['confidence']:.0f}% confidence)")
        print(f"  Points: {pred['home_points']:.1f} - {pred['away_points']:.1f}")
        print()
    
    # show failed predictions
    if failed_games:
        print("=" * 100)
        print(f"GAMES THAT COULD NOT BE PREDICTED ({len(failed_games)}):")
        print("=" * 100)
        for i, failed in enumerate(failed_games, 1):
            neutral_marker = " [NEUTRAL]" if failed['is_neutral'] else ""
            print(f"{i}. {failed['away_team']} @ {failed['home_team']}{neutral_marker}")
            print(f"   Reason: {failed['reason']}")
            print()
    
    print("=" * 100)
    
    # save to file
    filename = f'predictions_week_{week_num}.txt'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"CFB PREDICTIONS - WEEK {week_num}\n")
        f.write(f"Successfully predicted: {len(predictions)}/{len(games)} games\n")
        f.write("=" * 100 + "\n\n")
        
        for i, pred in enumerate(predictions, 1):
            f.write(f"Game {i}: {pred['away_team']} @ {pred['home_team']}")
            if pred['is_neutral']:
                f.write(" [NEUTRAL SITE]")
            f.write("\n")
            f.write(f"  PREDICTION: {pred['winner']} wins\n")
            f.write(f"  Confidence: {pred['confidence']:.0f}%\n")
            f.write(f"  Points: {pred['home_team']} {pred['home_points']:.1f} - {pred['away_points']:.1f} {pred['away_team']}\n\n")
        
        if failed_games:
            f.write("\n" + "=" * 100 + "\n")
            f.write(f"GAMES THAT COULD NOT BE PREDICTED ({len(failed_games)}):\n")
            f.write("=" * 100 + "\n\n")
            for i, failed in enumerate(failed_games, 1):
                f.write(f"{i}. {failed['away_team']} @ {failed['home_team']}")
                if failed['is_neutral']:
                    f.write(" [NEUTRAL SITE]")
                f.write(f"\n   Reason: {failed['reason']}\n\n")
    
    print(f"\nPredictions saved to {filename}")
    
    # show high confidence picks
    high_conf = [p for p in predictions if p['confidence'] >= 70]
    if high_conf:
        print(f"\n{'=' * 100}")
        print(f"HIGH CONFIDENCE PICKS (≥70%):")
        print(f"{'=' * 100}")
        for pred in high_conf:
            print(f"  {pred['winner']} over {pred['home_team'] if pred['winner'] == pred['away_team'] else pred['away_team']} ({pred['confidence']:.0f}%)")
        print()


def main():
    """
    main function
    """
    print("CFB Batch Predictor")
    print("=" * 100)
    print()
    
    try:
        week_num = int(input("Enter week number (0-15): ").strip())
        if week_num < 0 or week_num > 15:
            print("Invalid week number.")
            return
    except ValueError:
        print("Invalid input.")
        return
    
    season_type = input("Season type (regular/postseason) [default: regular]: ").strip().lower()
    if not season_type:
        season_type = 'regular'
    
    batch_predict_week(week_num, season_type)


if __name__ == "__main__":
    main()

