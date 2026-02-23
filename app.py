"""
PrimeScore Backend Application
Implements all Functional Requirements (FR1-FR10) and Non-Functional Requirements (NFR1-NFR5)
"""

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import requests
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app, supports_credentials=True)

# Database configuration
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'database': os.environ.get('DB_NAME', 'primescore'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'password'),
    'port': os.environ.get('DB_PORT', '5432')
}

# Football Data API configuration
FOOTBALL_API_KEY = os.environ.get('FOOTBALL_API_KEY', 'your-api-key-here')
FOOTBALL_API_BASE = 'https://api.football-data.org/v4'

def get_db_connection():
    """Get database connection with error handling"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def call_football_api(endpoint, params=None):
    """Make API calls to Football Data API with error handling (NFR2)"""
    headers = {'X-Auth-Token': FOOTBALL_API_KEY}
    try:
        response = requests.get(
            f"{FOOTBALL_API_BASE}/{endpoint}",
            headers=headers,
            params=params,
            timeout=5  # NFR1: Fast response times
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        return None


# ============================================================================
# FR10: Registration, Login and First-time Dashboard
# ============================================================================

@app.route('/api/register', methods=['POST'])
def register():
    """Register new user (FR10)"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    # Validate password strength
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Check if username exists
        cursor.execute('SELECT user_id FROM users WHERE username = %s', (username,))
        if cursor.fetchone():
            return jsonify({'error': 'Username already exists'}), 409
        
        # Create user
        hashed_password = generate_password_hash(password)
        cursor.execute(
            'INSERT INTO users (username, password_hash, created_at) VALUES (%s, %s, %s) RETURNING user_id',
            (username, hashed_password, datetime.now())
        )
        user_id = cursor.fetchone()[0]
        
        conn.commit()
        
        return jsonify({
            'message': 'Registration successful',
            'user_id': user_id
        }), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/login', methods=['POST'])
def login():
    """User login (FR10)"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            'SELECT user_id, username, password_hash FROM users WHERE username = %s',
            (username,)
        )
        user = cursor.fetchone()
        
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Set session
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        
        # Check if first-time user (no favourites)
        cursor.execute(
            'SELECT COUNT(*) as count FROM user_favourites WHERE user_id = %s',
            (user['user_id'],)
        )
        has_favourites = cursor.fetchone()['count'] > 0
        
        return jsonify({
            'message': 'Login successful',
            'user_id': user['user_id'],
            'username': user['username'],
            'first_time_user': not has_favourites
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/logout', methods=['POST'])
def logout():
    """User logout"""
    session.clear()
    return jsonify({'message': 'Logout successful'}), 200


# ============================================================================
# FR1 & FR3: Personalized Home Screen
# ============================================================================

@app.route('/api/home-screen', methods=['GET'])
def get_home_screen():
    """Get personalized home screen content (FR1, UR1, UR3)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    conn = get_db_connection()
    
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get user's favourite teams and leagues
        cursor.execute('''
            SELECT favourite_teams, favourite_players, favourite_leagues
            FROM user_favourites
            WHERE user_id = %s
        ''', (user_id,))
        
        favourites = cursor.fetchone()
        
        if not favourites or not any([
            favourites.get('favourite_teams'),
            favourites.get('favourite_leagues')
        ]):
            # First-time user: return generic content (FR10)
            return get_generic_home_screen()
        
        # Get personalized content based on favourites
        home_data = {
            'live_matches': [],
            'recent_results': [],
            'upcoming_fixtures': [],
            'league_tables': []
        }
        
        # Fetch live matches for favourite teams (FR3, FR4)
        if favourites['favourite_teams']:
            for team_id in favourites['favourite_teams'][:5]:  # Limit to 5 teams
                matches = call_football_api(f'teams/{team_id}/matches', {
                    'status': 'LIVE,SCHEDULED,FINISHED',
                    'limit': 10
                })
                if matches and 'matches' in matches:
                    for match in matches['matches']:
                        if match['status'] == 'IN_PLAY' or match['status'] == 'PAUSED':
                            home_data['live_matches'].append(format_match_data(match))
                        elif match['status'] == 'FINISHED':
                            home_data['recent_results'].append(format_match_data(match))
                        elif match['status'] == 'SCHEDULED':
                            home_data['upcoming_fixtures'].append(format_match_data(match))
        
        # Fetch league tables for favourite leagues (FR6)
        if favourites['favourite_leagues']:
            for league_id in favourites['favourite_leagues'][:3]:  # Limit to 3 leagues
                standings = call_football_api(f'competitions/{league_id}/standings')
                if standings:
                    home_data['league_tables'].append(standings)
        
        return jsonify(home_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


def get_generic_home_screen():
    """Get generic home screen for first-time users (FR10)"""
    try:
        # Get popular leagues standings
        popular_leagues = ['PL', 'CL', 'BL1', 'SA', 'PD']  # Premier League, Champions League, etc.
        
        home_data = {
            'live_matches': [],
            'recent_results': [],
            'upcoming_fixtures': [],
            'league_tables': [],
            'message': 'Welcome! Select your favourite teams and leagues to personalize your experience.'
        }
        
        # Get today's matches
        matches = call_football_api('matches', {
            'dateFrom': datetime.now().strftime('%Y-%m-%d'),
            'dateTo': datetime.now().strftime('%Y-%m-%d')
        })
        
        if matches and 'matches' in matches:
            for match in matches['matches'][:10]:  # Limit results
                if match['status'] in ['IN_PLAY', 'PAUSED']:
                    home_data['live_matches'].append(format_match_data(match))
                elif match['status'] == 'FINISHED':
                    home_data['recent_results'].append(format_match_data(match))
                elif match['status'] == 'SCHEDULED':
                    home_data['upcoming_fixtures'].append(format_match_data(match))
        
        # Get league tables for popular leagues
        for league in popular_leagues[:2]:  # Limit to 2 for performance
            standings = call_football_api(f'competitions/{league}/standings')
            if standings:
                home_data['league_tables'].append(standings)
        
        return jsonify(home_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def format_match_data(match):
    """Format match data for consistent response (NFR4: Usability)"""
    return {
        'match_id': match.get('id'),
        'home_team': match.get('homeTeam', {}).get('name'),
        'away_team': match.get('awayTeam', {}).get('name'),
        'home_score': match.get('score', {}).get('fullTime', {}).get('home'),
        'away_score': match.get('score', {}).get('fullTime', {}).get('away'),
        'status': match.get('status'),
        'match_date': match.get('utcDate'),
        'competition': match.get('competition', {}).get('name')
    }


# ============================================================================
# FR2: Favourite Teams and Players Management
# ============================================================================

@app.route('/api/favourites', methods=['GET'])
def get_favourites():
    """Get user's favourites (FR2)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    conn = get_db_connection()
    
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            SELECT favourite_teams, favourite_players, favourite_leagues, updated_at
            FROM user_favourites
            WHERE user_id = %s
        ''', (user_id,))
        
        favourites = cursor.fetchone()
        
        if not favourites:
            return jsonify({
                'favourite_teams': [],
                'favourite_players': [],
                'favourite_leagues': []
            }), 200
        
        return jsonify({
            'favourite_teams': favourites['favourite_teams'] or [],
            'favourite_players': favourites['favourite_players'] or [],
            'favourite_leagues': favourites['favourite_leagues'] or [],
            'last_updated': favourites['updated_at'].isoformat() if favourites['updated_at'] else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/favourites', methods=['POST'])
def update_favourites():
    """Update user's favourites with validation (FR2, UR2)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    user_id = session['user_id']
    
    favourite_teams = data.get('favourite_teams', [])
    favourite_players = data.get('favourite_players', [])
    favourite_leagues = data.get('favourite_leagues', [])
    
    # Validate limits (FR2)
    if len(favourite_teams) > 5:
        return jsonify({'error': 'Maximum 5 favourite teams allowed'}), 400
    if len(favourite_players) > 25:
        return jsonify({'error': 'Maximum 25 favourite players allowed'}), 400
    if len(favourite_leagues) > 3:
        return jsonify({'error': 'Maximum 3 favourite leagues allowed'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Upsert favourites
        cursor.execute('''
            INSERT INTO user_favourites (user_id, favourite_teams, favourite_players, favourite_leagues, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id)
            DO UPDATE SET
                favourite_teams = EXCLUDED.favourite_teams,
                favourite_players = EXCLUDED.favourite_players,
                favourite_leagues = EXCLUDED.favourite_leagues,
                updated_at = EXCLUDED.updated_at
        ''', (user_id, favourite_teams, favourite_players, favourite_leagues, datetime.now()))
        
        conn.commit()
        
        return jsonify({'message': 'Favourites updated successfully'}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# ============================================================================
# FR3: Live Match Information
# ============================================================================

@app.route('/api/matches/live', methods=['GET'])
def get_live_matches():
    """Get live match information (FR3, UR4, UR11)"""
    try:
        # Fetch live matches from API
        matches = call_football_api('matches', {'status': 'LIVE'})
        
        if not matches or 'matches' not in matches:
            return jsonify({'matches': []}), 200
        
        live_matches = []
        for match in matches['matches']:
            live_data = {
                'match_id': match['id'],
                'home_team': match['homeTeam']['name'],
                'away_team': match['awayTeam']['name'],
                'home_score': match['score']['fullTime']['home'] or 0,
                'away_score': match['score']['fullTime']['away'] or 0,
                'status': match['status'],
                'minute': match.get('minute'),
                'competition': match['competition']['name'],
                'events': []
            }
            
            # Add match events (goals, cards, substitutions)
            if 'goals' in match:
                for goal in match.get('goals', []):
                    live_data['events'].append({
                        'type': 'goal',
                        'minute': goal.get('minute'),
                        'player': goal.get('scorer', {}).get('name'),
                        'team': goal.get('team', {}).get('name')
                    })
            
            if 'bookings' in match:
                for booking in match.get('bookings', []):
                    live_data['events'].append({
                        'type': 'card',
                        'card_type': booking.get('card'),
                        'minute': booking.get('minute'),
                        'player': booking.get('player', {}).get('name'),
                        'team': booking.get('team', {}).get('name')
                    })
            
            if 'substitutions' in match:
                for sub in match.get('substitutions', []):
                    live_data['events'].append({
                        'type': 'substitution',
                        'minute': sub.get('minute'),
                        'player_in': sub.get('playerIn', {}).get('name'),
                        'player_out': sub.get('playerOut', {}).get('name'),
                        'team': sub.get('team', {}).get('name')
                    })
            
            # Sort events by minute
            live_data['events'].sort(key=lambda x: x.get('minute', 0))
            
            live_matches.append(live_data)
        
        return jsonify({'matches': live_matches}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/matches/<int:match_id>', methods=['GET'])
def get_match_details(match_id):
    """Get detailed match information (FR3, FR7)"""
    try:
        match = call_football_api(f'matches/{match_id}')
        
        if not match:
            return jsonify({'error': 'Match not found'}), 404
        
        match_details = {
            'match_id': match['id'],
            'home_team': match['homeTeam']['name'],
            'away_team': match['awayTeam']['name'],
            'home_score': match['score']['fullTime']['home'],
            'away_score': match['score']['fullTime']['away'],
            'status': match['status'],
            'date': match['utcDate'],
            'venue': match.get('venue'),
            'referee': match.get('referees', [{}])[0].get('name') if match.get('referees') else None,
            'competition': match['competition']['name'],
            'statistics': {
                'possession': {
                    'home': match.get('homeTeam', {}).get('possession'),
                    'away': match.get('awayTeam', {}).get('possession')
                },
                'shots': {
                    'home': match.get('homeTeam', {}).get('shots'),
                    'away': match.get('awayTeam', {}).get('shots')
                },
                'shots_on_target': {
                    'home': match.get('homeTeam', {}).get('shotsOnTarget'),
                    'away': match.get('awayTeam', {}).get('shotsOnTarget')
                },
                'corners': {
                    'home': match.get('homeTeam', {}).get('corners'),
                    'away': match.get('awayTeam', {}).get('corners')
                },
                'fouls': {
                    'home': match.get('homeTeam', {}).get('fouls'),
                    'away': match.get('awayTeam', {}).get('fouls')
                }
            }
        }
        
        return jsonify(match_details), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# FR4: Fixture Viewing
# ============================================================================

@app.route('/api/fixtures', methods=['GET'])
def get_fixtures():
    """Get upcoming fixtures (FR4, UR5)"""
    try:
        # Get query parameters
        team_id = request.args.get('team_id')
        league_id = request.args.get('league_id')
        date_from = request.args.get('date_from', datetime.now().strftime('%Y-%m-%d'))
        date_to = request.args.get('date_to', (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d'))
        
        params = {
            'dateFrom': date_from,
            'dateTo': date_to,
            'status': 'SCHEDULED'
        }
        
        # Fetch fixtures based on filters
        if team_id:
            fixtures = call_football_api(f'teams/{team_id}/matches', params)
        elif league_id:
            fixtures = call_football_api(f'competitions/{league_id}/matches', params)
        else:
            fixtures = call_football_api('matches', params)
        
        if not fixtures or 'matches' not in fixtures:
            return jsonify({'fixtures': []}), 200
        
        formatted_fixtures = []
        for match in fixtures['matches']:
            formatted_fixtures.append({
                'match_id': match['id'],
                'home_team': match['homeTeam']['name'],
                'away_team': match['awayTeam']['name'],
                'date': match['utcDate'],
                'competition': match['competition']['name'],
                'venue': match.get('venue')
            })
        
        return jsonify({'fixtures': formatted_fixtures}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# FR5: Results Viewing
# ============================================================================

@app.route('/api/results', methods=['GET'])
def get_results():
    """Get completed match results (FR5, UR6)"""
    try:
        # Get query parameters
        team_id = request.args.get('team_id')
        league_id = request.args.get('league_id')
        date_from = request.args.get('date_from', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
        date_to = request.args.get('date_to', datetime.now().strftime('%Y-%m-%d'))
        
        params = {
            'dateFrom': date_from,
            'dateTo': date_to,
            'status': 'FINISHED'
        }
        
        # Fetch results based on filters
        if team_id:
            results = call_football_api(f'teams/{team_id}/matches', params)
        elif league_id:
            results = call_football_api(f'competitions/{league_id}/matches', params)
        else:
            results = call_football_api('matches', params)
        
        if not results or 'matches' not in results:
            return jsonify({'results': []}), 200
        
        formatted_results = []
        for match in results['matches']:
            formatted_results.append({
                'match_id': match['id'],
                'home_team': match['homeTeam']['name'],
                'away_team': match['awayTeam']['name'],
                'home_score': match['score']['fullTime']['home'],
                'away_score': match['score']['fullTime']['away'],
                'date': match['utcDate'],
                'competition': match['competition']['name']
            })
        
        return jsonify({'results': formatted_results}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# FR6: League Tables and Standings
# ============================================================================

@app.route('/api/leagues/<league_id>/standings', methods=['GET'])
def get_league_standings(league_id):
    """Get league table and standings (FR6, UR7)"""
    try:
        standings = call_football_api(f'competitions/{league_id}/standings')
        
        if not standings or 'standings' not in standings:
            return jsonify({'error': 'Standings not found'}), 404
        
        # Format standings data
        league_table = {
            'competition': standings['competition']['name'],
            'season': standings['season']['startDate'][:4],
            'standings': []
        }
        
        # Get the main standings (usually first in array)
        main_standings = standings['standings'][0]['table']
        
        for team in main_standings:
            league_table['standings'].append({
                'position': team['position'],
                'team': team['team']['name'],
                'played': team['playedGames'],
                'won': team['won'],
                'drawn': team['draw'],
                'lost': team['lost'],
                'goals_for': team['goalsFor'],
                'goals_against': team['goalsAgainst'],
                'goal_difference': team['goalDifference'],
                'points': team['points']
            })
        
        return jsonify(league_table), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# FR7: Statistics Viewing
# ============================================================================

@app.route('/api/teams/<int:team_id>/statistics', methods=['GET'])
def get_team_statistics(team_id):
    """Get team statistics (FR7, UR8)"""
    try:
        team = call_football_api(f'teams/{team_id}')
        
        if not team:
            return jsonify({'error': 'Team not found'}), 404
        
        # Get recent matches for statistics
        matches = call_football_api(f'teams/{team_id}/matches', {
            'status': 'FINISHED',
            'limit': 10
        })
        
        # Calculate statistics
        stats = {
            'team_name': team['name'],
            'matches_played': 0,
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'goals_scored': 0,
            'goals_conceded': 0,
            'clean_sheets': 0,
            'recent_form': []
        }
        
        if matches and 'matches' in matches:
            for match in matches['matches']:
                stats['matches_played'] += 1
                
                home_team = match['homeTeam']['id'] == team_id
                home_score = match['score']['fullTime']['home'] or 0
                away_score = match['score']['fullTime']['away'] or 0
                
                if home_team:
                    stats['goals_scored'] += home_score
                    stats['goals_conceded'] += away_score
                    
                    if home_score > away_score:
                        stats['wins'] += 1
                        stats['recent_form'].append('W')
                    elif home_score < away_score:
                        stats['losses'] += 1
                        stats['recent_form'].append('L')
                    else:
                        stats['draws'] += 1
                        stats['recent_form'].append('D')
                    
                    if away_score == 0:
                        stats['clean_sheets'] += 1
                else:
                    stats['goals_scored'] += away_score
                    stats['goals_conceded'] += home_score
                    
                    if away_score > home_score:
                        stats['wins'] += 1
                        stats['recent_form'].append('W')
                    elif away_score < home_score:
                        stats['losses'] += 1
                        stats['recent_form'].append('L')
                    else:
                        stats['draws'] += 1
                        stats['recent_form'].append('D')
                    
                    if home_score == 0:
                        stats['clean_sheets'] += 1
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/players/<int:player_id>/statistics', methods=['GET'])
def get_player_statistics(player_id):
    """Get player statistics (FR7, UR8)"""
    try:
        # Note: This is a simplified version. Real implementation would need
        # more comprehensive player stats from API or database
        player = call_football_api(f'persons/{player_id}')
        
        if not player:
            return jsonify({'error': 'Player not found'}), 404
        
        player_stats = {
            'player_name': player['name'],
            'nationality': player['nationality'],
            'position': player['position'],
            'date_of_birth': player['dateOfBirth'],
            'statistics': {
                'goals': player.get('goals', 0),
                'assists': player.get('assists', 0),
                'appearances': player.get('appearances', 0),
                'yellow_cards': player.get('yellowCards', 0),
                'red_cards': player.get('redCards', 0)
            }
        }
        
        return jsonify(player_stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# FR8: Team and Player Comparison
# ============================================================================

@app.route('/api/compare/teams', methods=['POST'])
def compare_teams():
    """Compare two teams (FR8, UR9)"""
    data = request.json
    team_a_id = data.get('team_a_id')
    team_b_id = data.get('team_b_id')
    
    if not team_a_id or not team_b_id:
        return jsonify({'error': 'Both team IDs required'}), 400
    
    if team_a_id == team_b_id:
        return jsonify({'error': 'Cannot compare the same team'}), 400
    
    try:
        # Get statistics for both teams
        team_a_stats = get_team_statistics(team_a_id)
        team_b_stats = get_team_statistics(team_b_id)
        
        if team_a_stats[1] != 200 or team_b_stats[1] != 200:
            return jsonify({'error': 'Could not fetch team statistics'}), 404
        
        comparison = {
            'team_a': team_a_stats[0].json,
            'team_b': team_b_stats[0].json,
            'comparison_date': datetime.now().isoformat()
        }
        
        return jsonify(comparison), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/compare/players', methods=['POST'])
def compare_players():
    """Compare two players (FR8, UR9)"""
    data = request.json
    player_a_id = data.get('player_a_id')
    player_b_id = data.get('player_b_id')
    
    if not player_a_id or not player_b_id:
        return jsonify({'error': 'Both player IDs required'}), 400
    
    if player_a_id == player_b_id:
        return jsonify({'error': 'Cannot compare the same player'}), 400
    
    try:
        # Get statistics for both players
        player_a_stats = get_player_statistics(player_a_id)
        player_b_stats = get_player_statistics(player_b_id)
        
        if player_a_stats[1] != 200 or player_b_stats[1] != 200:
            return jsonify({'error': 'Could not fetch player statistics'}), 404
        
        comparison = {
            'player_a': player_a_stats[0].json,
            'player_b': player_b_stats[0].json,
            'comparison_date': datetime.now().isoformat()
        }
        
        return jsonify(comparison), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# FR9: Notification Settings
# ============================================================================

@app.route('/api/notifications/settings', methods=['GET'])
def get_notification_settings():
    """Get user's notification settings (FR9, UR10)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user_id']
    conn = get_db_connection()
    
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            SELECT goals_notifications, match_start_notifications, match_end_notifications
            FROM notification_settings
            WHERE user_id = %s
        ''', (user_id,))
        
        settings = cursor.fetchone()
        
        if not settings:
            # Return default settings
            return jsonify({
                'goals_notifications': False,
                'match_start_notifications': False,
                'match_end_notifications': False
            }), 200
        
        return jsonify(settings), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/notifications/settings', methods=['POST'])
def update_notification_settings():
    """Update notification settings (FR9, UR10)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    user_id = session['user_id']
    
    goals_notifications = data.get('goals_notifications', False)
    match_start_notifications = data.get('match_start_notifications', False)
    match_end_notifications = data.get('match_end_notifications', False)
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Upsert notification settings
        cursor.execute('''
            INSERT INTO notification_settings 
            (user_id, goals_notifications, match_start_notifications, match_end_notifications, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id)
            DO UPDATE SET
                goals_notifications = EXCLUDED.goals_notifications,
                match_start_notifications = EXCLUDED.match_start_notifications,
                match_end_notifications = EXCLUDED.match_end_notifications,
                updated_at = EXCLUDED.updated_at
        ''', (user_id, goals_notifications, match_start_notifications, match_end_notifications, datetime.now()))
        
        conn.commit()
        
        return jsonify({'message': 'Notification settings updated successfully'}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# ============================================================================
# Utility Routes
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint (NFR3: Availability)"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200


@app.route('/api/search', methods=['GET'])
def search():
    """Search for teams, players, or competitions"""
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'all')  # all, teams, players, competitions
    
    if not query or len(query) < 2:
        return jsonify({'error': 'Query too short'}), 400
    
    try:
        results = {'teams': [], 'players': [], 'competitions': []}
        
        if search_type in ['all', 'teams']:
            teams = call_football_api('teams', {'name': query})
            if teams and 'teams' in teams:
                results['teams'] = [{'id': t['id'], 'name': t['name']} for t in teams['teams'][:10]]
        
        if search_type in ['all', 'competitions']:
            competitions = call_football_api('competitions')
            if competitions and 'competitions' in competitions:
                filtered = [c for c in competitions['competitions'] if query.lower() in c['name'].lower()]
                results['competitions'] = [{'id': c['id'], 'name': c['name']} for c in filtered[:10]]
        
        return jsonify(results), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # NFR3: Availability - Run on all interfaces for accessibility
    app.run(host='0.0.0.0', port=5000, debug=True)
