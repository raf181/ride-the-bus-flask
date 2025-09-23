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
import time
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


@app.route('/')
def landing():
    """Landing page - redirect to login if not authenticated."""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    # Check for daily bonus
    bonus = user_manager.claim_daily_bonus(user['id'])
    if bonus > 0:
        flash(f'Daily bonus claimed: ${bonus:.2f}!', 'success')
    
    return render_template('casino_landing.html', user=user)


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
@login_required
def game():
    """Main game interface."""
    user = get_current_user()
    game_id = session.get('game_id')
    
    if not game_id or game_id not in active_games:
        return redirect(url_for('landing'))
    
    game_state = active_games[game_id]
    engine = CasinoRideTheBus()
    strategy = engine.get_strategy_recommendation(game_state)
    
    return render_template('casino_game.html', 
                         game=game_state, 
                         strategy=strategy,
                         user=user)


@app.route('/start_game', methods=['POST'])
@login_required
def start_game():
    """Start a new game with specified bet amount."""
    user = get_current_user()
    bet_amount = float(request.form.get('bet_amount', 10.0))
    
    if bet_amount <= 0:
        flash('Invalid bet amount.', 'error')
        return redirect(url_for('landing'))
    
    if bet_amount > user['bankroll']:
        flash('Insufficient funds!', 'error')
        return redirect(url_for('landing'))
    
    # Deduct bet from user's bankroll
    user_manager.update_bankroll(user['id'], user['bankroll'] - bet_amount)
    
    engine = CasinoRideTheBus()
    game_state = engine.start_new_game(bet_amount)
    
    active_games[game_state.game_id] = game_state
    session['game_id'] = game_state.game_id
    
    return redirect(url_for('game'))


@app.route('/make_guess', methods=['POST'])
@login_required
def make_guess():
    """Make a guess for the current round."""
    user = get_current_user()
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
        
        # If game is finished, record the result
        if game_state.status.value in ['won', 'lost']:
            profit_loss = game_state.current_winnings - game_state.initial_bet
            user_manager.record_game(
                user_id=user['id'],
                bet_amount=game_state.initial_bet,
                final_winnings=game_state.current_winnings,
                profit_loss=profit_loss,
                rounds_completed=len(game_state.cards_drawn),
                cashed_out=(game_state.status.value == 'won')
            )
            
            # Add winnings to user's bankroll
            if game_state.current_winnings > 0:
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
@login_required
def cash_out():
    """Cash out current winnings."""
    user = get_current_user()
    game_id = session.get('game_id')
    
    if not game_id or game_id not in active_games:
        return jsonify({'error': 'No active game'}), 400
    
    game_state = active_games[game_id]
    engine = CasinoRideTheBus()
    
    try:
        winnings = engine.cash_out(game_state)
        
        # Record the game
        profit_loss = winnings - game_state.initial_bet
        user_manager.record_game(
            user_id=user['id'],
            bet_amount=game_state.initial_bet,
            final_winnings=winnings,
            profit_loss=profit_loss,
            rounds_completed=len(game_state.cards_drawn),
            cashed_out=True
        )
        
        # Add winnings to user's bankroll
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
@login_required
def new_game():
    """Start a fresh game (clear session)."""
    session.pop('game_id', None)
    return redirect(url_for('landing'))


@app.route('/strategy')
@login_required
def get_strategy():
    """Get strategy recommendation for current game state."""
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


@app.route('/add_funds', methods=['POST'])
@login_required
def add_funds():
    """Add funds to user account (demo purposes)."""
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