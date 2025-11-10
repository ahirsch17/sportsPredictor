"""
NFL Game Predictor - Machine Learning Approach
Uses XGBoost with matchup-level features and proper probability calibration
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import log_loss, accuracy_score, brier_score_loss
import xgboost as xgb
from predictor import read_nfl_data, calculate_team_averages, classify_offensive_style
from injuryextract import get_injury_data, calculate_injury_impact

# Import injury module
try:
    from injuryextract import get_injury_data, calculate_injury_impact
    INJURIES_AVAILABLE = True
except ImportError:
    INJURIES_AVAILABLE = False


def create_matchup_features(home_team, away_team, home_avg, away_avg, teams_data=None, injury_data=None):
    """
    Creates matchup-level features (differences/ratios between teams)
    This is more predictive than absolute team stats
    """
    features = {}
    
    # Get games for recent stats calculation
    home_games = teams_data.get(home_team, []) if teams_data else []
    away_games = teams_data.get(away_team, []) if teams_data else []
    
    # === OFFENSIVE VS DEFENSIVE MATCHUPS (ratios) ===
    # Research shows: Weight offense 1.6x, defense 1.0x
    
    # === EPA PROXY (35% of model weight: Off 22%, Def 13%) ===
    features['off_epa_diff'] = home_avg['offense']['epa_proxy'] - away_avg['offense']['epa_proxy']
    features['off_epa_diff_weighted'] = (home_avg['offense']['epa_proxy'] - away_avg['offense']['epa_proxy']) * 1.6  # Offense weighted 1.6x
    features['def_epa_diff'] = away_avg['defense']['yards_per_play_allowed'] - home_avg['defense']['yards_per_play_allowed']  # Lower is better
    
    # Overall efficiency matchup
    features['home_off_vs_away_def_ypp'] = home_avg['offense']['yards_per_play'] / (away_avg['defense']['yards_per_play_allowed'] + 0.1)
    features['away_off_vs_home_def_ypp'] = away_avg['offense']['yards_per_play'] / (home_avg['defense']['yards_per_play_allowed'] + 0.1)
    
    # === EXPLOSIVE PLAYS (15% weight: Pass 10%, Run 5%) ===
    features['explosive_pass_diff'] = home_avg['offense']['explosive_pass_rate'] - away_avg['offense']['explosive_pass_rate']
    features['explosive_run_diff'] = home_avg['offense']['explosive_run_rate'] - away_avg['offense']['explosive_run_rate']
    
    # Matchup: offense explosive rate vs defense explosive allowed
    features['home_explosive_pass_vs_away_d'] = home_avg['offense']['explosive_pass_rate'] - away_avg['defense']['explosive_pass_allowed']
    features['away_explosive_pass_vs_home_d'] = away_avg['offense']['explosive_pass_rate'] - home_avg['defense']['explosive_pass_allowed']
    features['home_explosive_run_vs_away_d'] = home_avg['offense']['explosive_run_rate'] - away_avg['defense']['explosive_run_allowed']
    features['away_explosive_run_vs_home_d'] = away_avg['offense']['explosive_run_rate'] - home_avg['defense']['explosive_run_allowed']
    
    # Run game matchup (CRITICAL - some teams can't stop the run)
    features['home_rush_vs_away_rush_d'] = home_avg['offense']['rushing_yards'] / (away_avg['defense']['rushing_yards_allowed'] + 0.1)
    features['away_rush_vs_home_rush_d'] = away_avg['offense']['rushing_yards'] / (home_avg['defense']['rushing_yards_allowed'] + 0.1)
    features['home_rush_eff_vs_away_rush_d_eff'] = home_avg['offense']['rushing_avg'] / (away_avg['defense']['rushing_avg_allowed'] + 0.1)
    features['away_rush_eff_vs_home_rush_d_eff'] = away_avg['offense']['rushing_avg'] / (home_avg['defense']['rushing_avg_allowed'] + 0.1)
    
    # Pass game matchup
    features['home_pass_vs_away_pass_d'] = home_avg['offense']['passing_yards'] / (away_avg['defense']['passing_yards_allowed'] + 0.1)
    features['away_pass_vs_home_pass_d'] = away_avg['offense']['passing_yards'] / (home_avg['defense']['passing_yards_allowed'] + 0.1)
    features['home_comp_vs_away_comp_d'] = home_avg['offense']['completion_rate'] - away_avg['defense']['completion_allowed']
    features['away_comp_vs_home_comp_d'] = away_avg['offense']['completion_rate'] - home_avg['defense']['completion_allowed']
    
    # === PRIORITY 1: QB PERFORMANCE (weighted 2x via multiple features) ===
    features['qb_ypa_diff'] = home_avg['offense']['yards_per_attempt'] - away_avg['offense']['yards_per_attempt']
    features['qb_td_int_ratio_diff'] = home_avg['offense']['td_int_ratio'] - away_avg['offense']['td_int_ratio']
    features['qb_sack_rate_diff'] = away_avg['offense']['sack_rate'] - home_avg['offense']['sack_rate']  # Lower is better
    features['qb_completion_diff'] = home_avg['offense']['completion_rate'] - away_avg['offense']['completion_rate']
    
    # QB composite score (higher weight)
    home_qb_score = (home_avg['offense']['yards_per_attempt'] * 0.3 + 
                     home_avg['offense']['completion_rate'] * 0.3 +
                     home_avg['offense']['td_int_ratio'] * 0.2 -
                     home_avg['offense']['sack_rate'] * 0.2)
    away_qb_score = (away_avg['offense']['yards_per_attempt'] * 0.3 + 
                     away_avg['offense']['completion_rate'] * 0.3 +
                     away_avg['offense']['td_int_ratio'] * 0.2 -
                     away_avg['offense']['sack_rate'] * 0.2)
    features['qb_composite_diff'] = home_qb_score - away_qb_score
    
    # Red Zone matchup (CRITICAL - finishing drives wins games)
    features['home_rz_vs_away_rz_d'] = home_avg['offense']['red_zone_rate'] - away_avg['defense']['red_zone_allowed']
    features['away_rz_vs_home_rz_d'] = away_avg['offense']['red_zone_rate'] - home_avg['defense']['red_zone_allowed']
    
    # Scoring efficiency matchup
    features['home_pts_vs_away_pts_d'] = home_avg['offense']['points_scored'] / (away_avg['defense']['points_allowed'] + 0.1)
    features['away_pts_vs_home_pts_d'] = away_avg['offense']['points_scored'] / (home_avg['defense']['points_allowed'] + 0.1)
    
    # === PRIORITY 3: RED ZONE EFFICIENCY (high priority - double weight) ===
    features['red_zone_diff'] = home_avg['offense']['red_zone_rate'] - away_avg['offense']['red_zone_rate']
    features['red_zone_diff_weighted'] = (home_avg['offense']['red_zone_rate'] - away_avg['offense']['red_zone_rate']) * 2.0
    
    # === PRIORITY 4: THIRD DOWN CONVERSIONS (high priority) ===
    features['third_down_diff'] = home_avg['offense']['third_down_rate'] - away_avg['offense']['third_down_rate']
    # Matchup-specific: offense 3rd down vs defense 3rd down allowed
    features['home_3rd_vs_away_3rd_d'] = home_avg['offense']['third_down_rate'] - away_avg['defense']['third_down_allowed']
    features['away_3rd_vs_home_3rd_d'] = away_avg['offense']['third_down_rate'] - home_avg['defense']['third_down_allowed']
    
    # === PRIORITY 5: RUSHING EFFICIENCY (moderate - use YPC not volume) ===
    # Already covered above with rush_eff features
    
    # === PRIORITY 6: PASSING DEFENSE (moderate-high) ===
    # QB rating allowed proxy: completion % allowed + YPP allowed
    home_pass_d_quality = (1 - home_avg['defense']['completion_allowed']) + (6.0 - home_avg['defense']['yards_per_play_allowed'])
    away_pass_d_quality = (1 - away_avg['defense']['completion_allowed']) + (6.0 - away_avg['defense']['yards_per_play_allowed'])
    features['pass_defense_diff'] = home_pass_d_quality - away_pass_d_quality
    
    # === DIFFERENTIAL FEATURES (home - away) ===
    features['win_rate_diff'] = home_avg['win_rate'] - away_avg['win_rate']
    features['recent_form_diff'] = home_avg['recent_form']['win_rate'] - away_avg['recent_form']['win_rate']
    features['points_scored_diff'] = home_avg['offense']['points_scored'] - away_avg['offense']['points_scored']
    features['points_allowed_diff'] = away_avg['defense']['points_allowed'] - home_avg['defense']['points_allowed']  # Lower is better
    
    # Efficiency differentials
    features['ypp_diff'] = home_avg['offense']['yards_per_play'] - away_avg['offense']['yards_per_play']
    
    # === PRIORITY 2: TURNOVER MARGIN (VERY predictive - weight 2x) ===
    features['turnover_margin_diff'] = home_avg['turnover_margin'] - away_avg['turnover_margin']
    features['turnover_margin_diff_weighted'] = (home_avg['turnover_margin'] - away_avg['turnover_margin']) * 2.0  # Double weight
    features['int_thrown_diff'] = away_avg['offense']['interceptions_thrown'] - home_avg['offense']['interceptions_thrown']  # Lower is better
    features['int_forced_diff'] = home_avg['defense']['interceptions_forced'] - away_avg['defense']['interceptions_forced']
    
    # Recent turnover margin (last 3 games - higher priority)
    if home_games and away_games:
        home_recent_games = [g for g in home_games if not g.get('preseason', False)][-3:]
        away_recent_games = [g for g in away_games if not g.get('preseason', False)][-3:]
        
        home_recent_to_margin = sum(
            g['off_stats'].get('sacks', 0) - g['off_stats'].get('turnovers', 0) 
            for g in home_recent_games
        ) / max(len(home_recent_games), 1)
        
        away_recent_to_margin = sum(
            g['off_stats'].get('sacks', 0) - g['off_stats'].get('turnovers', 0) 
            for g in away_recent_games
        ) / max(len(away_recent_games), 1)
        
        features['recent_turnover_margin_diff'] = home_recent_to_margin - away_recent_to_margin
    else:
        features['recent_turnover_margin_diff'] = 0
    
    # Sack differential (pass rush pressure)
    home_sack_diff = home_avg['offense']['sacks_made'] - home_avg['defense']['sacks_allowed']
    away_sack_diff = away_avg['offense']['sacks_made'] - away_avg['defense']['sacks_allowed']
    features['sack_diff'] = home_sack_diff - away_sack_diff
    
    # Penalty discipline (fewer penalties = better)
    features['penalty_diff'] = away_avg['offense']['penalties'] - home_avg['offense']['penalties']
    
    # === HOME/AWAY CONTEXT ===
    features['home_field_advantage'] = home_avg['splits']['home_advantage']
    features['home_at_home_winrate'] = home_avg['splits']['home_win_rate']
    features['away_on_road_winrate'] = away_avg['splits']['away_win_rate']
    features['location_matchup'] = home_avg['splits']['home_win_rate'] - away_avg['splits']['away_win_rate']
    
    # === CLOSE GAME PERFORMANCE (clutch factor) ===
    if home_avg['close_games']['total'] >= 2 and away_avg['close_games']['total'] >= 2:
        features['close_game_diff'] = home_avg['close_games']['win_rate'] - away_avg['close_games']['win_rate']
    else:
        features['close_game_diff'] = 0
    
    # === PYTHAGOREAN EXPECTATION (luck detection) ===
    features['home_pyth_diff'] = home_avg['win_rate'] - home_avg['pythagorean_win_rate']
    features['away_pyth_diff'] = away_avg['win_rate'] - away_avg['pythagorean_win_rate']
    features['pyth_luck_diff'] = features['home_pyth_diff'] - features['away_pyth_diff']
    
    # === QB RATING MATCHUP (QB vs Secondary) ===
    # ACTUAL QB rating vs opponent's pass defense quality
    features['qb_rating_diff'] = home_avg['offense'].get('qb_rating', 85) - away_avg['offense'].get('qb_rating', 85)
    features['home_qb_rating'] = home_avg['offense'].get('qb_rating', 85)
    features['away_qb_rating'] = away_avg['offense'].get('qb_rating', 85)
    
    # Opponent QB rating allowed (defense quality vs QBs)
    # Lower opponent QB rating = better defense
    features['qb_defense_matchup'] = away_avg['offense'].get('qb_rating', 85) - home_avg['offense'].get('qb_rating', 85)
    
    # === DRIVE EFFICIENCY (Points per possession) ===
    # Better than raw points - accounts for pace
    home_drives = home_avg['offense']['total_yards'] / (home_avg['offense']['yards_per_play'] * 12)  # Estimate drives
    away_drives = away_avg['offense']['total_yards'] / (away_avg['offense']['yards_per_play'] * 12)
    
    home_pts_per_drive = home_avg['offense']['points_scored'] / max(home_drives, 8)
    away_pts_per_drive = away_avg['offense']['points_scored'] / max(away_drives, 8)
    
    features['points_per_drive_diff'] = home_pts_per_drive - away_pts_per_drive
    
    # === CONSISTENCY METRICS (Variance = Risk) ===
    # Calculate standard deviation of recent performance
    home_recent_scores = [g['score_for'] for g in home_games[-5:]] if home_games else [0]
    away_recent_scores = [g['score_for'] for g in away_games[-5:]] if away_games else [0]
    
    import statistics
    home_score_std = statistics.stdev(home_recent_scores) if len(home_recent_scores) > 1 else 0
    away_score_std = statistics.stdev(away_recent_scores) if len(away_recent_scores) > 1 else 0
    
    # Lower variance = more consistent = better for prediction
    features['home_consistency'] = 1 / (home_score_std + 5)  # Higher is better
    features['away_consistency'] = 1 / (away_score_std + 5)
    features['consistency_diff'] = features['home_consistency'] - features['away_consistency']
    
    # === SITUATIONAL SUCCESS (3rd/4th Down MATCHUPS) ===
    # Home offense 3rd down vs away defense 3rd down
    features['third_down_matchup'] = home_avg['offense']['third_down_rate'] - away_avg['defense']['third_down_allowed']
    features['away_third_down_matchup'] = away_avg['offense']['third_down_rate'] - home_avg['defense']['third_down_allowed']
    
    # 4th down aggressiveness (teams that go for it more often)
    features['fourth_down_diff'] = home_avg['offense']['fourth_down_rate'] - away_avg['offense']['fourth_down_rate']
    
    # === SCORING MARGIN DISTRIBUTION (Blowout vs Close) ===
    # Teams that win big vs teams that squeak by
    home_wins = [g for g in home_games if g['result'] == 'W']
    away_wins = [g for g in away_games if g['result'] == 'W']
    
    home_avg_win_margin = sum([g['point_diff'] for g in home_wins]) / len(home_wins) if home_wins else 0
    away_avg_win_margin = sum([g['point_diff'] for g in away_wins]) / len(away_wins) if away_wins else 0
    
    features['avg_win_margin_diff'] = home_avg_win_margin - away_avg_win_margin
    
    # Blowout ability (% of wins by 14+ points)
    home_blowouts = sum([1 for g in home_wins if g['point_diff'] >= 14]) / max(len(home_wins), 1)
    away_blowouts = sum([1 for g in away_wins if g['point_diff'] >= 14]) / max(len(away_wins), 1)
    
    features['blowout_rate_diff'] = home_blowouts - away_blowouts
    
    # === PRIORITY 8: RECENT MOMENTUM (weighted 1.25x to capture evolving teams) ===
    features['recent_form_diff'] = home_avg['recent_form']['win_rate'] - away_avg['recent_form']['win_rate']
    features['recent_form_diff_weighted'] = (home_avg['recent_form']['win_rate'] - away_avg['recent_form']['win_rate']) * 1.25
    features['home_recent_pts_scored'] = home_avg['recent_form']['points_scored']
    features['away_recent_pts_scored'] = away_avg['recent_form']['points_scored']
    features['home_recent_pts_allowed'] = home_avg['recent_form']['points_allowed']
    features['away_recent_pts_allowed'] = away_avg['recent_form']['points_allowed']
    features['recent_scoring_diff'] = (home_avg['recent_form']['points_scored'] - home_avg['recent_form']['points_allowed']) - \
                                       (away_avg['recent_form']['points_scored'] - away_avg['recent_form']['points_allowed'])
    
    # === INJURY IMPACT ===
    if injury_data:
        home_injury = calculate_injury_impact(home_team, injury_data)
        away_injury = calculate_injury_impact(away_team, injury_data)
        
        features['injury_impact_diff'] = away_injury['impact_score'] - home_injury['impact_score']
        features['home_qb_injured'] = 1 if home_injury['qb_injured'] else 0
        features['away_qb_injured'] = 1 if away_injury['qb_injured'] else 0
    else:
        features['injury_impact_diff'] = 0
        features['home_qb_injured'] = 0
        features['away_qb_injured'] = 0
    
    # === REMOVE REDUNDANT FEATURES ===
    # Don't include: total_yards (use ypp instead), individual team stats (use differentials)
    
    return features


def build_training_dataset(teams_data, injury_data=None):
    """
    Builds training dataset from historical games
    Each game becomes TWO samples (home perspective and away perspective)
    """
    X = []
    y = []
    game_info = []
    
    processed_games = set()
    
    for team in teams_data.keys():
        team_avg = calculate_team_averages(team, teams_data, regular_only=True)
        if not team_avg or team_avg['games_played'] < 3:
            continue
        
        games = [g for g in teams_data[team] if not g['preseason']]
        
        for game in games:
            opponent = game['opponent']
            
            # Create unique game ID to avoid duplicates
            teams_sorted = tuple(sorted([team, opponent]))
            game_id = f"{teams_sorted[0]}_{teams_sorted[1]}"
            
            if game_id in processed_games:
                continue
            
            processed_games.add(game_id)
            
            opp_avg = calculate_team_averages(opponent, teams_data, regular_only=True)
            if not opp_avg or opp_avg['games_played'] < 3:
                continue
            
            # Determine who was home/away
            if game['location'] == 'home':
                home_team = team
                away_team = opponent
                home_avg_data = team_avg
                away_avg_data = opp_avg
                home_won = 1 if game['result'] == 'W' else 0
            else:
                home_team = opponent
                away_team = team
                home_avg_data = opp_avg
                away_avg_data = team_avg
                home_won = 1 if game['result'] == 'L' else 0  # We lost, so opponent (home) won
            
            # Create features for this matchup
            features = create_matchup_features(home_team, away_team, home_avg_data, away_avg_data, teams_data, injury_data)
            
            X.append(list(features.values()))
            y.append(home_won)
            game_info.append({
                'home_team': home_team,
                'away_team': away_team,
                'features': features
            })
    
    feature_names = list(game_info[0]['features'].keys()) if game_info else []
    
    return np.array(X), np.array(y), feature_names, game_info


def train_model(X, y, feature_names):
    """
    Trains XGBoost model with proper validation and calibration
    """
    # Split data for validation
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # XGBoost parameters - optimized for football prediction
    # Prioritizes high-importance features (QB, turnover, red zone)
    params = {
        'max_depth': 5,  # Slightly deeper for complex interactions
        'learning_rate': 0.03,  # Slower learning for better generalization
        'n_estimators': 200,  # More trees for stability
        'min_child_weight': 2,  # Less aggressive regularization
        'gamma': 0.05,  # Less pruning - allow important features
        'subsample': 0.85,  # Use 85% of data per tree
        'colsample_bytree': 0.75,  # Reduce feature sampling to focus on important ones
        'reg_alpha': 0.05,  # Reduced L1 - let important features shine
        'reg_lambda': 0.5,  # Reduced L2 regularization
        'scale_pos_weight': 1,  # Balanced classes
        'random_state': 42,
        'eval_metric': 'logloss',
        'importance_type': 'gain'  # Use gain for feature importance (better for interpretation)
    }
    
    # Train base model
    model = xgb.XGBClassifier(**params)
    model.fit(X_train, y_train)
    
    # Get predictions on test set
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Evaluate base model
    accuracy = accuracy_score(y_test, y_pred)
    logloss = log_loss(y_test, y_pred_proba)
    brier = brier_score_loss(y_test, y_pred_proba)
    
    print(f"\n{'=' * 100}")
    print(f"MODEL PERFORMANCE")
    print(f"{'=' * 100}")
    print(f"Training set: {len(X_train)} games")
    print(f"Test set: {len(X_test)} games")
    print(f"Accuracy: {accuracy:.1%}")
    print(f"Log Loss: {logloss:.3f} (lower is better)")
    print(f"Brier Score: {brier:.3f} (lower is better, perfect = 0.0)")
    
    # Cross-validation score
    cv_scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')
    print(f"Cross-Validation Accuracy: {cv_scores.mean():.1%} (+/- {cv_scores.std() * 2:.1%})")
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(f"\nTop 15 Most Important Features:")
    for idx, row in feature_importance.head(15).iterrows():
        print(f"  {row['feature']:40s} {row['importance']:.4f}")
    
    # Calibrate probabilities using isotonic regression
    print(f"\nCalibrating probabilities...")
    calibrated_model = CalibratedClassifierCV(model, method='isotonic', cv=5)
    calibrated_model.fit(X_train, y_train)
    
    # Evaluate calibrated model
    y_pred_calib = calibrated_model.predict_proba(X_test)[:, 1]
    logloss_calib = log_loss(y_test, y_pred_calib)
    brier_calib = brier_score_loss(y_test, y_pred_calib)
    
    print(f"After Calibration:")
    print(f"  Log Loss: {logloss_calib:.3f} (improved: {logloss - logloss_calib:+.3f})")
    print(f"  Brier Score: {brier_calib:.3f} (improved: {brier - brier_calib:+.3f})")
    
    return calibrated_model, feature_importance


def detect_qb_change(team, teams_data):
    """
    Detects if a team has recently changed QBs by comparing recent games
    Returns adjustment factor (0.0 = no change, 0.15 = major QB change)
    """
    games = teams_data.get(team, [])
    if len(games) < 2:
        return 0.0
    
    # Get last 3 games (most recent games first, reverse order)
    recent_games = [g for g in games if not g.get('preseason', False)][-3:]
    if len(recent_games) < 2:
        return 0.0
    
    # Method 1: Check QB performance variance (large changes suggest QB switch)
    qb_ratings = []
    for game in recent_games:
        qb_stats = game.get('qb_stats', {})
        if qb_stats and 'rating' in qb_stats:
            qb_ratings.append(qb_stats['rating'])
    
    # If QB ratings vary wildly (like 40 to 100), likely QB change
    if len(qb_ratings) >= 2:
        rating_diff = max(qb_ratings) - min(qb_ratings)
        if rating_diff > 40:  # Huge variance (starter vs backup)
            return 0.12
    
    # Method 2: Check for dramatic YPA drops (backup QBs typically worse)
    qb_ypa = []
    for game in recent_games:
        qb_stats = game.get('qb_stats', {})
        if qb_stats and 'ypa' in qb_stats:
            qb_ypa.append(qb_stats['ypa'])
    
    if len(qb_ypa) >= 2:
        ypa_diff = max(qb_ypa) - min(qb_ypa)
        if ypa_diff > 3.0:  # Big drop in yards per attempt (5.0 -> 2.0)
            return 0.10
    
    # Method 3: Check for missing QB stats (new QB might not have stats parsed yet)
    games_with_qb = sum(1 for g in recent_games if g.get('qb_stats'))
    if games_with_qb < len(recent_games) and len(recent_games) >= 2:
        # Some games missing QB stats - might indicate QB change
        return 0.08
    
    return 0.0


def calculate_uncertainty_adjustment(home_avg, away_avg, features_dict, teams_data):
    """
    Calculates uncertainty adjustment to reduce overconfidence
    Returns multiplier (0.0-1.0) that pulls probability toward 50%
    """
    uncertainty = 0.0
    
    # 1. Team consistency (variance in recent performance)
    home_games = teams_data.get(home_avg.get('team_name', ''), [])
    away_games = teams_data.get(away_avg.get('team_name', ''), [])
    
    if home_games and away_games:
        home_recent_scores = [g['score_for'] for g in home_games[-5:] if 'score_for' in g]
        away_recent_scores = [g['score_for'] for g in away_games[-5:] if 'score_for' in g]
        
        if len(home_recent_scores) > 1 and len(away_recent_scores) > 1:
            import statistics
            home_std = statistics.stdev(home_recent_scores)
            away_std = statistics.stdev(away_recent_scores)
            
            # High variance = more uncertainty
            avg_std = (home_std + away_std) / 2
            if avg_std > 15:
                uncertainty += 0.10
            elif avg_std > 10:
                uncertainty += 0.06
    
    # 2. Recent form volatility (teams on losing/winning streaks can regress)
    home_recent_form = home_avg.get('recent_form', {}).get('win_rate', 0.5)
    away_recent_form = away_avg.get('recent_form', {}).get('win_rate', 0.5)
    
    # Extreme recent form (very high or very low) is less sustainable
    form_diff = abs(home_recent_form - away_recent_form)
    if form_diff > 0.7:  # One team 3-0, other 0-3
        uncertainty += 0.08
    elif form_diff > 0.5:  # One team 2-1, other 0-3
        uncertainty += 0.05
    
    # 3. Feature extremeness (if features are extreme, model might be overconfident)
    extreme_features = 0
    for fname, fval in features_dict.items():
        if 'diff' in fname or 'vs' in fname:
            # Check if feature value is very extreme
            if abs(fval) > 10:  # Very large difference
                extreme_features += 1
    
    if extreme_features > 5:
        uncertainty += 0.08
    elif extreme_features > 3:
        uncertainty += 0.05
    
    # 4. Record mismatch (big favorites can lose)
    win_rate_diff = abs(home_avg.get('win_rate', 0.5) - away_avg.get('win_rate', 0.5))
    if win_rate_diff > 0.4:  # One team 8-0, other 2-6
        uncertainty += 0.06
    
    return min(uncertainty, 0.25)  # Cap at 25% uncertainty


def apply_probability_calibration(home_win_prob, uncertainty_adjustment, qb_change_adjustment):
    """
    Applies post-processing calibration to make probabilities more realistic
    """
    # Start with raw probability
    calibrated_prob = home_win_prob
    
    # Apply uncertainty adjustment (pulls toward 50%)
    # More uncertainty = pull harder toward center
    if uncertainty_adjustment > 0:
        pull_factor = uncertainty_adjustment * 2  # Scale uncertainty
        calibrated_prob = calibrated_prob * (1 - pull_factor) + 0.5 * pull_factor
    
    # Apply QB change adjustment (adds uncertainty for QB changes)
    if qb_change_adjustment > 0:
        calibrated_prob = calibrated_prob * (1 - qb_change_adjustment) + 0.5 * qb_change_adjustment
    
    # Cap probabilities at realistic bounds (nothing is 100% certain in NFL)
    MIN_PROB = 0.05  # Even worst team has ~5% chance
    MAX_PROB = 0.95  # Even best team has ~5% chance of losing
    
    calibrated_prob = max(MIN_PROB, min(MAX_PROB, calibrated_prob))
    
    return calibrated_prob


def predict_game_ml(home_team, away_team, teams_data, model, feature_names, injury_data=None):
    """
    Predicts game outcome using trained ML model with improved calibration
    """
    home_avg = calculate_team_averages(home_team, teams_data, regular_only=True)
    away_avg = calculate_team_averages(away_team, teams_data, regular_only=True)
    
    if not home_avg or not away_avg:
        print("Insufficient data for one or both teams")
        return None
    
    # Store team names for QB detection
    if 'team_name' not in home_avg:
        home_avg['team_name'] = home_team
    if 'team_name' not in away_avg:
        away_avg['team_name'] = away_team
    
    # Create features for this matchup
    features_dict = create_matchup_features(home_team, away_team, home_avg, away_avg, teams_data, injury_data)
    
    # Convert to array in same order as training
    X = np.array([features_dict[fname] for fname in feature_names]).reshape(1, -1)
    
    # Get raw prediction from model
    raw_home_win_prob = model.predict_proba(X)[0, 1]
    
    # Detect QB changes (adds uncertainty)
    home_qb_change = detect_qb_change(home_team, teams_data)
    away_qb_change = detect_qb_change(away_team, teams_data)
    qb_change_adjustment = (home_qb_change + away_qb_change) / 2
    
    if home_qb_change > 0 or away_qb_change > 0:
        print(f"\n⚠️  QB CHANGE DETECTED:")
        if home_qb_change > 0:
            print(f"   {home_team} has changed QBs recently (uncertainty +{home_qb_change*100:.0f}%)")
        if away_qb_change > 0:
            print(f"   {away_team} has changed QBs recently (uncertainty +{away_qb_change*100:.0f}%)")
    
    # Calculate uncertainty adjustment
    uncertainty_adj = calculate_uncertainty_adjustment(home_avg, away_avg, features_dict, teams_data)
    
    if uncertainty_adj > 0:
        print(f"\n📊 UNCERTAINTY FACTORS: {uncertainty_adj*100:.0f}% adjustment (team volatility/upset potential)")
    
    # Apply calibration
    home_win_prob = apply_probability_calibration(raw_home_win_prob, uncertainty_adj, qb_change_adjustment)
    away_win_prob = 1 - home_win_prob
    
    # Display team styles
    home_style = classify_offensive_style(home_avg)
    away_style = classify_offensive_style(away_avg)
    
    print(f"\n{'=' * 100}")
    print(f"MACHINE LEARNING PREDICTION: {home_team} vs {away_team}")
    print(f"{'=' * 100}\n")
    
    print(f"{home_team} (Home):")
    print(f"  Record: {home_avg['wins']}-{home_avg['games_played'] - home_avg['wins']} "
          f"({home_avg['win_rate']:.1%})")
    print(f"  Offensive Style: {home_style.upper().replace('_', ' ')}")
    print(f"  Points: {home_avg['offense']['points_scored']:.1f}/game (allowed: {home_avg['defense']['points_allowed']:.1f})")
    print(f"  Recent Form: {home_avg['recent_form']['wins']}-{home_avg['recent_form']['games'] - home_avg['recent_form']['wins']} last 3")
    
    print(f"\n{away_team} (Away):")
    print(f"  Record: {away_avg['wins']}-{away_avg['games_played'] - away_avg['wins']} "
          f"({away_avg['win_rate']:.1%})")
    print(f"  Offensive Style: {away_style.upper().replace('_', ' ')}")
    print(f"  Points: {away_avg['offense']['points_scored']:.1f}/game (allowed: {away_avg['defense']['points_allowed']:.1f})")
    print(f"  Recent Form: {away_avg['recent_form']['wins']}-{away_avg['recent_form']['games'] - away_avg['recent_form']['wins']} last 3")
    
    print(f"\n{'=' * 100}")
    print(f"Key Matchup Advantages:")
    print(f"{'=' * 100}")
    
    # Show top matchup edges
    top_features = []
    for fname, fval in features_dict.items():
        if 'vs' in fname or 'diff' in fname:
            # Determine which team benefits
            if 'home' in fname and fval > 0:
                top_features.append((fname, fval, home_team))
            elif 'away' in fname and fval > 0:
                top_features.append((fname, fval, away_team))
            elif 'diff' in fname:
                if fval > 0:
                    top_features.append((fname, fval, home_team))
                else:
                    top_features.append((fname, abs(fval), away_team))
    
    # Sort by magnitude
    top_features.sort(key=lambda x: abs(x[1]), reverse=True)
    
    for fname, fval, beneficiary in top_features[:8]:
        clean_name = fname.replace('_', ' ').replace('home', home_team).replace('away', away_team)
        print(f"  {clean_name}: {fval:+.3f} (favors {beneficiary})")
    
    print(f"\n{'=' * 100}")
    print(f"FINAL PREDICTION")
    print(f"{'=' * 100}\n")
    
    print(f"{home_team} Win Probability: {home_win_prob:.1%}")
    print(f"{away_team} Win Probability: {away_win_prob:.1%}\n")
    
    if home_win_prob > 0.5:
        print(f"PREDICTION: {home_team} wins")
        print(f"Confidence: {home_win_prob:.1%}")
        
        # Confidence interpretation
        if home_win_prob > 0.70:
            print(f"Strength: STRONG favorite")
        elif home_win_prob > 0.60:
            print(f"Strength: Moderate favorite")
        else:
            print(f"Strength: Slight favorite")
    else:
        print(f"PREDICTION: {away_team} wins")
        print(f"Confidence: {away_win_prob:.1%}")
        
        if away_win_prob > 0.70:
            print(f"Strength: STRONG favorite")
        elif away_win_prob > 0.60:
            print(f"Strength: Moderate favorite")
        else:
            print(f"Strength: Slight favorite")
    
    print(f"{'=' * 100}\n")
    
    return {
        'home_win_prob': home_win_prob,
        'away_win_prob': away_win_prob,
        'predicted_winner': home_team if home_win_prob > 0.5 else away_team,
        'features': features_dict
    }


def main():
    """
    Train model and make predictions
    """
    print("=" * 100)
    print("NFL ML Predictor - XGBoost with Calibrated Probabilities")
    print("=" * 100)
    
    # Load data
    print("\nLoading NFL game data...")
    teams_data = read_nfl_data()
    
    if not teams_data:
        print("Failed to load data")
        return
    
    print(f"Loaded {len(teams_data)} teams")
    
    # Load injury data
    injury_data = None
    if INJURIES_AVAILABLE:
        print("Loading injury data...")
        injury_data = get_injury_data()
        if injury_data:
            print(f"Injury data loaded for {len(injury_data)} teams")
    
    # Build training dataset
    print("\nBuilding training dataset from historical matchups...")
    X, y, feature_names, game_info = build_training_dataset(teams_data, injury_data)
    
    print(f"Created {len(X)} training samples from historical games")
    print(f"Features: {len(feature_names)}")
    print(f"Home wins: {sum(y)} ({sum(y)/len(y):.1%})")
    print(f"Away wins: {len(y) - sum(y)} ({(len(y) - sum(y))/len(y):.1%})")
    
    # Train model
    print("\nTraining XGBoost model...")
    model, feature_importance = train_model(X, y, feature_names)
    
    # Interactive prediction
    print(f"\n{'=' * 100}")
    print("MAKE A PREDICTION")
    print(f"{'=' * 100}\n")
    
    print("Enter team names (use full names as they appear in nflData.txt)")
    home_team = input("Enter HOME team: ").strip()
    away_team = input("Enter AWAY team: ").strip()
    
    # Make prediction
    prediction = predict_game_ml(home_team, away_team, teams_data, model, feature_names, injury_data)
    
    if prediction:
        print(f"\nModel-based prediction complete!")
    
    return model, feature_importance


if __name__ == "__main__":
    main()

