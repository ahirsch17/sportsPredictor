"""
MLB Weather Data Integration
Uses free weather API to get current conditions for game predictions
"""

import requests
import json


# MLB Stadium Locations (for weather lookup)
STADIUM_LOCATIONS = {
    'Arizona Diamondbacks': {'city': 'Phoenix', 'state': 'AZ', 'lat': 33.4452, 'lon': -112.0667},
    'Atlanta Braves': {'city': 'Atlanta', 'state': 'GA', 'lat': 33.8908, 'lon': -84.4679},
    'Baltimore Orioles': {'city': 'Baltimore', 'state': 'MD', 'lat': 39.2838, 'lon': -76.6217},
    'Boston Red Sox': {'city': 'Boston', 'state': 'MA', 'lat': 42.3467, 'lon': -71.0972},
    'Chicago Cubs': {'city': 'Chicago', 'state': 'IL', 'lat': 41.9484, 'lon': -87.6553},
    'Chicago White Sox': {'city': 'Chicago', 'state': 'IL', 'lat': 41.8299, 'lon': -87.6338},
    'Cincinnati Reds': {'city': 'Cincinnati', 'state': 'OH', 'lat': 39.0974, 'lon': -84.5067},
    'Cleveland Guardians': {'city': 'Cleveland', 'state': 'OH', 'lat': 41.4962, 'lon': -81.6852},
    'Colorado Rockies': {'city': 'Denver', 'state': 'CO', 'lat': 39.7559, 'lon': -104.9942},
    'Detroit Tigers': {'city': 'Detroit', 'state': 'MI', 'lat': 42.3390, 'lon': -83.0485},
    'Houston Astros': {'city': 'Houston', 'state': 'TX', 'lat': 29.7573, 'lon': -95.3555},
    'Kansas City Royals': {'city': 'Kansas City', 'state': 'MO', 'lat': 39.0517, 'lon': -94.4803},
    'Los Angeles Angels': {'city': 'Anaheim', 'state': 'CA', 'lat': 33.8003, 'lon': -117.8827},
    'Los Angeles Dodgers': {'city': 'Los Angeles', 'state': 'CA', 'lat': 34.0739, 'lon': -118.2400},
    'Miami Marlins': {'city': 'Miami', 'state': 'FL', 'lat': 25.7781, 'lon': -80.2197},
    'Milwaukee Brewers': {'city': 'Milwaukee', 'state': 'WI', 'lat': 43.0280, 'lon': -87.9712},
    'Minnesota Twins': {'city': 'Minneapolis', 'state': 'MN', 'lat': 44.9817, 'lon': -93.2778},
    'New York Mets': {'city': 'New York', 'state': 'NY', 'lat': 40.7571, 'lon': -73.8458},
    'New York Yankees': {'city': 'New York', 'state': 'NY', 'lat': 40.8296, 'lon': -73.9262},
    'Oakland Athletics': {'city': 'Oakland', 'state': 'CA', 'lat': 37.7516, 'lon': -122.2005},
    'Philadelphia Phillies': {'city': 'Philadelphia', 'state': 'PA', 'lat': 39.9061, 'lon': -75.1665},
    'Pittsburgh Pirates': {'city': 'Pittsburgh', 'state': 'PA', 'lat': 40.4469, 'lon': -80.0057},
    'San Diego Padres': {'city': 'San Diego', 'state': 'CA', 'lat': 32.7073, 'lon': -117.1566},
    'San Francisco Giants': {'city': 'San Francisco', 'state': 'CA', 'lat': 37.7786, 'lon': -122.3893},
    'Seattle Mariners': {'city': 'Seattle', 'state': 'WA', 'lat': 47.5914, 'lon': -122.3325},
    'St. Louis Cardinals': {'city': 'St. Louis', 'state': 'MO', 'lat': 38.6226, 'lon': -90.1928},
    'Tampa Bay Rays': {'city': 'St. Petersburg', 'state': 'FL', 'lat': 27.7682, 'lon': -82.6534},
    'Texas Rangers': {'city': 'Arlington', 'state': 'TX', 'lat': 32.7473, 'lon': -97.0833},
    'Toronto Blue Jays': {'city': 'Toronto', 'state': 'ON', 'lat': 43.6414, 'lon': -79.3894},
    'Washington Nationals': {'city': 'Washington', 'state': 'DC', 'lat': 38.8730, 'lon': -77.0074}
}


def get_weather_data(team_name):
    """
    Gets current weather for team's stadium using free weather API
    Uses wttr.in - no API key required
    """
    location = STADIUM_LOCATIONS.get(team_name)
    
    if not location:
        return None
    
    try:
        # Using wttr.in free weather API (JSON format)
        url = f"https://wttr.in/{location['city']},{location['state']}?format=j1"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        current = data['current_condition'][0]
        
        weather_info = {
            'temp_f': int(current['temp_F']),
            'temp_c': int(current['temp_C']),
            'wind_speed_mph': int(current['windspeedMiles']),
            'wind_dir': current['winddir16Point'],
            'humidity': int(current['humidity']),
            'precipitation': float(current.get('precipMM', 0)),
            'condition': current['weatherDesc'][0]['value'],
            'location': f"{location['city']}, {location['state']}"
        }
        
        return weather_info
        
    except Exception as e:
        print(f"  Could not fetch weather: {e}")
        return None


def calculate_weather_impact(weather_data, park_info):
    """
    Calculates weather impact on game scoring
    Returns: impact score (-3.0 to +3.0)
    """
    if not weather_data:
        return 0.0
    
    impact = 0.0
    notes = []
    
    # Temperature effects (hot = more offense)
    temp = weather_data['temp_f']
    if temp >= 85:
        impact += 1.5
        notes.append("Hot weather favors offense")
    elif temp >= 75:
        impact += 0.5
        notes.append("Warm weather slightly favors offense")
    elif temp <= 50:
        impact -= 1.0
        notes.append("Cold weather reduces offense")
    
    # Wind effects (most important!)
    wind_speed = weather_data['wind_speed_mph']
    wind_dir = weather_data['wind_dir']
    
    if wind_speed >= 20:
        # Strong wind - direction matters
        if 'Out' in wind_dir or 'S' in wind_dir:  # Blowing out
            impact += 2.0
            notes.append(f"Strong wind ({wind_speed} mph) blowing OUT - big offense boost!")
        else:  # Blowing in
            impact -= 2.0
            notes.append(f"Strong wind ({wind_speed} mph) blowing IN - offense reduced")
    elif wind_speed >= 12:
        if 'Out' in wind_dir or 'S' in wind_dir:
            impact += 1.0
            notes.append(f"Moderate wind blowing out")
        else:
            impact -= 1.0
            notes.append(f"Moderate wind blowing in")
    
    # Humidity (high humidity = ball carries better)
    humidity = weather_data['humidity']
    if humidity >= 70:
        impact += 0.5
        notes.append("High humidity helps ball carry")
    
    # Rain/precipitation (reduces offense)
    if weather_data['precipitation'] > 0:
        impact -= 1.0
        notes.append("Rain expected - reduces offense")
    
    # Dome overrides all weather
    if park_info.get('roof') == 'dome':
        impact = 0.0
        notes = ["Indoor dome - weather irrelevant"]
    
    return impact, notes


def get_weather_summary(home_team):
    """
    Gets complete weather analysis for a team
    """
    from park_factors import get_park_factor
    
    weather = get_weather_data(home_team)
    
    if not weather:
        return {
            'weather': None,
            'impact': 0.0,
            'notes': ["Weather data unavailable"]
        }
    
    park = get_park_factor(home_team)
    impact, notes = calculate_weather_impact(weather, park)
    
    return {
        'weather': weather,
        'impact': impact,
        'notes': notes
    }


if __name__ == "__main__":
    print("MLB Weather Data Test\n")
    
    # Test a few teams
    test_teams = ['Colorado Rockies', 'Chicago Cubs', 'Tampa Bay Rays']
    
    for team in test_teams:
        print(f"{team}:")
        summary = get_weather_summary(team)
        
        if summary['weather']:
            w = summary['weather']
            print(f"  Location: {w['location']}")
            print(f"  Temp: {w['temp_f']}°F")
            print(f"  Wind: {w['wind_speed_mph']} mph {w['wind_dir']}")
            print(f"  Condition: {w['condition']}")
            print(f"  Impact Score: {summary['impact']:+.1f}")
            print(f"  Notes: {', '.join(summary['notes'])}")
        else:
            print(f"  Weather unavailable")
        print()

