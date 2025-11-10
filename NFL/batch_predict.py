"""
NFL Batch Predictor
Automatically predicts all games for the upcoming week using ML model
"""

import requests
import json
import numpy as np
from datetime import datetime
from predictor import read_nfl_data, advanced_prediction, calculate_team_averages
from ml_predictor import build_training_dataset, train_model, create_matchup_features, classify_offensive_style, predict_game_ml

# Import injury data
try:
    from injuryextract import get_injury_data, calculate_injury_impact
    INJURIES_AVAILABLE = True
except ImportError:
    INJURIES_AVAILABLE = False


def get_upcoming_games(week_num, season_type='regular', year=2024):
    """
    gets all games scheduled for a specific week (completed or not)
    """
    base_api_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    
    season_type_num = 1 if season_type == 'preseason' else 2
    
    params = {
        'seasontype': season_type_num,
        'week': week_num,
        'year': year
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
                            # check if it's at neutral site
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


def batch_predict_week(week_num, season_type='regular', use_ml=True):
    """
    predicts all games for a specific week using ML model
    """
    print("=" * 100)
    print(f"NFL BATCH PREDICTOR ({'ML MODEL' if use_ml else 'HEURISTIC'}) - {season_type.upper()} WEEK {week_num}")
    print("=" * 100)
    print("\nLoading NFL data...")
    
    # load team data
    teams_data = read_nfl_data()
    
    if not teams_data:
        print("ERROR: Could not load NFL data. Run dataextract.py first.")
        return {
            'predictions': [],
            'failed_games': [],
            'error': 'NFL data unavailable. Run dataextract.py first.'
        }
    
    print(f"Data loaded! {len(teams_data)} teams found.\n")
    
    # load injury data
    injury_data = None
    if INJURIES_AVAILABLE:
        print("Loading injury data...")
        injury_data = get_injury_data()
        if injury_data:
            print(f"Injury data loaded for {len(injury_data)} teams\n")
    
    # Train ML model if using ML mode
    model = None
    feature_names = None
    if use_ml:
        print("Training ML model on historical data...")
        X, y, feature_names, game_info = build_training_dataset(teams_data, injury_data)
        model, feature_importance = train_model(X, y, feature_names)
        print()
    
    # get upcoming games
    print(f"Fetching games for Week {week_num}...")
    games = get_upcoming_games(week_num, season_type)
    
    if not games:
        print(f"No games found for Week {week_num}")
        return {
            'predictions': [],
            'failed_games': [],
            'error': f'No games found for week {week_num} ({season_type})'
        }
    
    print(f"Found {len(games)} games to predict\n")
    
    # predict each game
    predictions = []
    failed_games = []
    
    for i, game in enumerate(games, 1):
        print(f"\n{'=' * 100}")
        print(f"GAME {i}/{len(games)}: {game['away_team']} @ {game['home_team']}")
        if game['is_neutral']:
            print("(NEUTRAL SITE)")
        print(f"{'=' * 100}")
        
        try:
            if use_ml and model is not None:
                # ML prediction
                home_avg = calculate_team_averages(game['home_team'], teams_data, regular_only=True)
                away_avg = calculate_team_averages(game['away_team'], teams_data, regular_only=True)
                
                if not home_avg or not away_avg:
                    print(f"  Insufficient data for ML prediction")
                    failed_games.append({
                        'home_team': game['home_team'],
                        'away_team': game['away_team'],
                        'is_neutral': game['is_neutral'],
                        'reason': 'Insufficient data'
                    })
                    continue
                
                # Use improved prediction function with calibration
                prediction_result = predict_game_ml(
                    game['home_team'], 
                    game['away_team'], 
                    teams_data, 
                    model, 
                    feature_names, 
                    injury_data
                )
                
                if not prediction_result:
                    failed_games.append({
                        'home_team': game['home_team'],
                        'away_team': game['away_team'],
                        'is_neutral': game['is_neutral'],
                        'reason': 'Prediction failed'
                    })
                    continue
                
                home_win_prob = prediction_result['home_win_prob']
                away_win_prob = prediction_result['away_win_prob']
                
                # Determine winner
                if home_win_prob > 0.5:
                    winner = game['home_team']
                    confidence = home_win_prob * 100
                else:
                    winner = game['away_team']
                    confidence = away_win_prob * 100
                
                # Display styles
                home_style = classify_offensive_style(home_avg)
                away_style = classify_offensive_style(away_avg)
                
                print(f"  {game['home_team']}: {home_avg['wins']}-{home_avg['games_played'] - home_avg['wins']} ({home_style})")
                print(f"  {game['away_team']}: {away_avg['wins']}-{away_avg['games_played'] - away_avg['wins']} ({away_style})")
                print(f"  → {winner} wins ({confidence:.1f}% confidence)")
                
                predictions.append({
                    'home_team': game['home_team'],
                    'away_team': game['away_team'],
                    'home_win_prob': home_win_prob,
                    'away_win_prob': away_win_prob,
                    'winner': winner,
                    'confidence': confidence,
                    'is_neutral': game['is_neutral'],
                    'status': 'predicted'
                })
            else:
                # Heuristic prediction (old method)
                result = advanced_prediction(
                    game['home_team'], 
                    game['away_team'], 
                    teams_data, 
                    game['is_neutral'],
                    injury_data
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
                        diff = 0
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
                    print(f"  Could not predict this game (missing team data)")
                    failed_games.append({
                        'home_team': game['home_team'],
                        'away_team': game['away_team'],
                        'is_neutral': game['is_neutral'],
                        'reason': 'Missing team data'
                    })
        
        except Exception as e:
            print(f"  Error predicting game: {e}")
            failed_games.append({
                'home_team': game['home_team'],
                'away_team': game['away_team'],
                'is_neutral': game['is_neutral'],
                'reason': str(e)
            })
            continue
    
    # output summary
    print("\n\n")
    print("=" * 100)
    print(f"PREDICTIONS SUMMARY - WEEK {week_num}")
    print(f"Successfully predicted: {len(predictions)}/{len(games)} games")
    print("=" * 100)
    print()
    
    for i, pred in enumerate(predictions, 1):
        home_marker = "  " if pred['winner'] != pred['home_team'] else ">>>"
        away_marker = "  " if pred['winner'] != pred['away_team'] else ">>>"
        neutral_marker = " [NEUTRAL]" if pred['is_neutral'] else ""
        
        # Determine confidence level label
        conf = pred['confidence']
        if conf > 85:
            conf_label = "LOCK"
        elif conf > 70:
            conf_label = "CONFIDENT"
        elif conf > 60:
            conf_label = "LEAN"
        else:
            conf_label = "TOSS-UP"
        
        print(f"Game {i}:{neutral_marker}")
        print(f"  {away_marker} {pred['away_team']}")
        print(f"  @")
        print(f"  {home_marker} {pred['home_team']}")
        print(f"  PREDICTION: {pred['winner']} wins ({conf:.1f}% | {conf_label})")
        
        if 'home_points' in pred:  # Heuristic mode
            print(f"  Score: {pred['home_team']} {pred['home_points']:.1f} - {pred['away_points']:.1f} {pred['away_team']}")
        else:  # ML mode
            print(f"  Probabilities: {pred['home_team']} {pred.get('home_win_prob', 0)*100:.1f}% | {pred['away_team']} {pred.get('away_win_prob', 0)*100:.1f}%")
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
    with open(f'predictions_week_{week_num}.txt', 'w', encoding='utf-8') as f:
        f.write(f"NFL PREDICTIONS - WEEK {week_num}\n")
        f.write(f"Successfully predicted: {len(predictions)}/{len(games)} games\n")
        f.write("=" * 100 + "\n\n")
        
        for i, pred in enumerate(predictions, 1):
            f.write(f"Game {i}: {pred['away_team']} @ {pred['home_team']}")
            if pred['is_neutral']:
                f.write(" [NEUTRAL SITE]")
            f.write("\n")
            f.write(f"  PREDICTION: {pred['winner']} wins\n")
            f.write(f"  Confidence: {pred['confidence']:.1f}%\n")
            
            if 'home_points' in pred:  # Heuristic mode
                f.write(f"  Points: {pred['home_team']} {pred['home_points']:.1f} - {pred['away_points']:.1f} {pred['away_team']}\n\n")
            else:  # ML mode
                f.write(f"  Probabilities: {pred['home_team']} {pred.get('home_win_prob', 0)*100:.1f}% | {pred['away_team']} {pred.get('away_win_prob', 0)*100:.1f}%\n\n")
        
        if failed_games:
            f.write("\n" + "=" * 100 + "\n")
            f.write(f"GAMES THAT COULD NOT BE PREDICTED ({len(failed_games)}):\n")
            f.write("=" * 100 + "\n\n")
            for i, failed in enumerate(failed_games, 1):
                f.write(f"{i}. {failed['away_team']} @ {failed['home_team']}")
                if failed['is_neutral']:
                    f.write(" [NEUTRAL SITE]")
                f.write(f"\n   Reason: {failed['reason']}\n\n")
    
    print(f"\nPredictions saved to predictions_week_{week_num}.txt")
    
    return {
        'predictions': predictions,
        'failed_games': failed_games,
        'summary': {
            'week': week_num,
            'season_type': season_type,
            'total_games': len(games),
            'predicted_games': len(predictions),
            'timestamp': datetime.now().isoformat()
        }
    }


def main():
    """
    main function - prompts user for week number
    """
    print("NFL Batch Predictor")
    print("=" * 100)
    print()
    
    try:
        week_num = int(input("Enter week number (1-18): ").strip())
        if week_num < 1 or week_num > 18:
            print("Invalid week number. Must be 1-18.")
            return
    except ValueError:
        print("Invalid input. Please enter a number.")
        return
    
    season_type = input("Season type (preseason/regular) [default: regular]: ").strip().lower()
    if not season_type:
        season_type = 'regular'
    
    # Always use ML model
    batch_predict_week(week_num, season_type, use_ml=True)


if __name__ == "__main__":
    main()

