"""
Casino Ride the Bus - Flask web application with user system
A 4-round betting game with user accounts, persistent bankroll, and game history
"""
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
import uuid
from typing import Dict, Optional
from functools import wraps

from casino_game import CasinoRideTheBus, GameState, Round
from user_manager import UserManager


app = Flask(__name__)
app.config['SECRET_KEY'] = 'casino-ride-the-bus-secret-key'

# Initialize user manager
user_manager = UserManager()

# In-memory storage for active games
active_games: Dict[str, GameState] = {}


def login_required(f):
    """Decorator to require user login for protected routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Get current user from session."""
    if 'user_id' in session:
        return user_manager.get_user_by_id(session['user_id'])
    return None

def get_current_user_or_guest():
    """Get current user or create/return guest user."""
    user = get_current_user()
    if user:
        return user, False  # (user, is_guest)
    
    # Create or get guest session
    if 'guest_id' not in session:
        session['guest_id'] = str(uuid.uuid4())
        session['guest_bankroll'] = 1000.0  # Starting guest bankroll
    
    guest_user = {
        'id': session['guest_id'],
        'username': 'Guest',
        'email': 'guest@casino.com',
        'bankroll': session.get('guest_bankroll', 1000.0),
        'total_wagered': 0.0,
        'total_won': 0.0,
        'games_played': 0,
        'games_won': 0,
        'created_at': 'Guest Session',
        'last_login': 'Current Session'
    }
    
    return guest_user, True  # (guest_user, is_guest)


@app.route('/')
def landing():
    """Landing page - now accessible to both guests and users."""
    # Use get_current_user_or_guest to handle both logged-in users and guest sessions
    user, is_guest = get_current_user_or_guest()
    
    if user and not is_guest:
        # Check for daily bonus for registered users only
        bonus = user_manager.claim_daily_bonus(user['id'])
        if bonus > 0:
            flash(f'Daily bonus claimed: ${bonus:.2f}!', 'success')
    
    # Show landing page to everyone (guests and registered users)
    # Note: user might be None for first-time visitors
    return render_template('casino_landing.html', user=user, is_guest=is_guest)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if user_manager.authenticate_user(username, password):
            user = user_manager.get_user_by_username(username)
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('landing'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        success, message = user_manager.create_user(username, email, password)
        if success:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
    
    return render_template('register.html')


@app.route('/logout')
def logout():
    """Log out current user."""
    username = session.get('username', 'User')
    session.clear()
    flash(f'Goodbye, {username}!', 'info')
    return redirect(url_for('login'))


@app.route('/profile')
@login_required
def profile():
    """User profile and statistics page."""
    user = get_current_user()
    stats = user_manager.get_user_statistics(user['id'])
    recent_games = user_manager.get_game_history(user['id'], limit=10)
    leaderboard = user_manager.get_leaderboard()
    
    return render_template('profile.html', 
                         user=user, 
                         stats=stats, 
                         recent_games=recent_games,
                         leaderboard=leaderboard)


@app.route('/game')
def game():
    """Main game interface - accessible to guests and users."""
    user, is_guest = get_current_user_or_guest()
    game_id = session.get('game_id')
    
    if not game_id or game_id not in active_games:
        return redirect(url_for('landing'))
    
    game_state = active_games[game_id]
    engine = CasinoRideTheBus()
    strategy = engine.get_strategy_recommendation(game_state)
    
    return render_template('casino_game.html', 
                         game=game_state, 
                         strategy=strategy,
                         user=user,
                         is_guest=is_guest)


@app.route('/start_game', methods=['POST'])
def start_game():
    """Start a new game with specified bet amount - accessible to guests and users."""
    user, is_guest = get_current_user_or_guest()
    bet_amount = float(request.form.get('bet_amount', 10.0))
    
    if bet_amount <= 0:
        flash('Invalid bet amount.', 'error')
        return redirect(url_for('landing'))
    
    if bet_amount > user['bankroll']:
        flash('Insufficient funds!', 'error')
        return redirect(url_for('landing'))
    
    # Deduct bet from bankroll
    if is_guest:
        session['guest_bankroll'] = user['bankroll'] - bet_amount
    else:
        user_manager.update_bankroll(user['id'], user['bankroll'] - bet_amount)
    
    engine = CasinoRideTheBus()
    game_state = engine.start_new_game(bet_amount)
    
    active_games[game_state.game_id] = game_state
    session['game_id'] = game_state.game_id
    
    return redirect(url_for('game'))


@app.route('/make_guess', methods=['POST'])
def make_guess():
    """Make a guess for the current round - accessible to guests and users."""
    user, is_guest = get_current_user_or_guest()
    game_id = session.get('game_id')
    
    if not game_id or game_id not in active_games:
        return jsonify({'error': 'No active game'}), 400
    
    guess = request.json.get('guess')
    if not guess:
        return jsonify({'error': 'No guess provided'}), 400
    
    game_state = active_games[game_id]
    engine = CasinoRideTheBus()
    
    try:
        is_correct, card, winnings = engine.make_guess(game_state, guess)
        
        # If game is finished, handle results
        if game_state.status.value in ['won', 'lost']:
            if not is_guest:
                # Record game for registered users only
                user_manager.record_game(
                    user_id=user['id'],
                    game_id=game_state.game_id,
                    bet_amount=game_state.bet_amount,
                    final_winnings=game_state.current_winnings,
                    rounds_completed=len(game_state.cards_drawn),
                    result=game_state.status.value
                )
            
            # Add winnings to bankroll
            if game_state.current_winnings > 0:
                if is_guest:
                    session['guest_bankroll'] = session.get('guest_bankroll', 1000.0) + game_state.current_winnings
                else:
                    current_user = user_manager.get_user_by_id(user['id'])
                    user_manager.update_bankroll(
                        user['id'], 
                        current_user['bankroll'] + game_state.current_winnings
                    )
        
        return jsonify({
            'success': True,
            'correct': is_correct,
            'card': str(card),
            'card_rank': card.rank.name,
            'card_suit': card.suit.value,
            'card_color': card.color.value,
            'winnings': winnings,
            'status': game_state.status.value,
            'round': game_state.current_round.value if game_state.status.value == 'active' else None
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/cash_out', methods=['POST'])
def cash_out():
    """Cash out current winnings - accessible to guests and users."""
    user, is_guest = get_current_user_or_guest()
    game_id = session.get('game_id')
    
    if not game_id or game_id not in active_games:
        return jsonify({'error': 'No active game'}), 400
    
    game_state = active_games[game_id]
    engine = CasinoRideTheBus()
    
    try:
        winnings = engine.cash_out(game_state)
        
        # Record the game for registered users only
        if not is_guest:
            user_manager.record_game(
                user_id=user['id'],
                game_id=game_state.game_id,
                bet_amount=game_state.bet_amount,
                final_winnings=winnings,
                rounds_completed=len(game_state.cards_drawn),
                result='cashed_out'
            )
        
        # Add winnings to bankroll
        if is_guest:
            session['guest_bankroll'] = session.get('guest_bankroll', 1000.0) + winnings
        else:
            current_user = user_manager.get_user_by_id(user['id'])
            user_manager.update_bankroll(user['id'], current_user['bankroll'] + winnings)
        
        return jsonify({
            'success': True,
            'winnings': winnings,
            'status': game_state.status.value
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/new_game', methods=['POST'])
def new_game():
    """Start a fresh game (clear session) - accessible to guests and users."""
    session.pop('game_id', None)
    return redirect(url_for('landing'))


@app.route('/strategy')
def get_strategy():
    """Get strategy recommendation for current game state - accessible to guests and users."""
    game_id = session.get('game_id')
    if not game_id or game_id not in active_games:
        return jsonify({'error': 'No active game'}), 400
    
    game_state = active_games[game_id]
    engine = CasinoRideTheBus()
    strategy = engine.get_strategy_recommendation(game_state)
    
    return jsonify({
        'action': strategy.action,
        'confidence': strategy.confidence,
        'reasoning': strategy.reasoning,
        'expected_value': strategy.expected_value,
        'probability': strategy.probability
    })


@app.route('/play_as_guest', methods=['POST'])
def play_as_guest():
    """Start a guest session."""
    # Clear any existing user session
    session.pop('user_id', None)
    session.pop('username', None)
    
    # Initialize guest session
    session['guest_id'] = str(uuid.uuid4())
    session['guest_bankroll'] = 1000.0
    
    flash('Playing as guest! You start with $1000. Register to save your progress.', 'info')
    return redirect(url_for('landing'))


@app.route('/add_funds', methods=['POST'])
@login_required
def add_funds():
    """Add funds to user account (demo purposes) - only for registered users."""
    user = get_current_user()
    amount = float(request.form.get('amount', 0))
    
    if amount > 0 and amount <= 1000:  # Limit for demo
        current_user = user_manager.get_user_by_id(user['id'])
        user_manager.update_bankroll(user['id'], current_user['bankroll'] + amount)
        flash(f'Added ${amount:.2f} to your account!', 'success')
    else:
        flash('Invalid amount. Maximum $1000 per transaction.', 'error')
    
    return redirect(url_for('landing'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)