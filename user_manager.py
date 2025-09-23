"""
User management system for Casino Ride the Bus
Handles user registration, authentication, bankroll management, and game history
"""
import sqlite3
import hashlib
import secrets
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass


@dataclass
class User:
    id: int
    username: str
    email: str
    bankroll: float
    total_wagered: float
    total_won: float
    games_played: int
    games_won: int
    created_at: str
    last_login: str


@dataclass
class GameRecord:
    id: int
    user_id: int
    game_id: str
    bet_amount: float
    final_winnings: float
    rounds_completed: int
    result: str  # 'won', 'lost', 'cashed_out'
    profit_loss: float
    created_at: str


class UserManager:
    """Manages user accounts, authentication, and game records"""
    
    def __init__(self, db_path: str = "casino_users.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                bankroll REAL DEFAULT 1000.0,
                total_wagered REAL DEFAULT 0.0,
                total_won REAL DEFAULT 0.0,
                games_played INTEGER DEFAULT 0,
                games_won INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_login TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Game records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                game_id TEXT NOT NULL,
                bet_amount REAL NOT NULL,
                final_winnings REAL NOT NULL,
                rounds_completed INTEGER NOT NULL,
                result TEXT NOT NULL,
                profit_loss REAL NOT NULL,
                cards_drawn TEXT,
                strategy_used TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # User sessions table (for login management)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Daily bonuses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_bonuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                bonus_amount REAL NOT NULL,
                claimed_date TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password: str) -> tuple[str, str]:
        """Hash password with salt"""
        salt = secrets.token_hex(32)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return password_hash, salt
    
    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """Verify password against hash"""
        return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
    
    def register_user(self, username: str, email: str, password: str, starting_bankroll: float = 1000.0) -> tuple[bool, str]:
        """Register a new user"""
        if len(username) < 3:
            return False, "Username must be at least 3 characters"
        if len(password) < 6:
            return False, "Password must be at least 6 characters"
        if "@" not in email:
            return False, "Invalid email address"
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if username or email already exists
            cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
            if cursor.fetchone():
                return False, "Username or email already exists"
            
            password_hash, salt = self.hash_password(password)
            
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, salt, bankroll)
                VALUES (?, ?, ?, ?, ?)
            """, (username, email, password_hash, salt, starting_bankroll))
            
            conn.commit()
            conn.close()
            return True, "Account created successfully"
            
        except Exception as e:
            return False, f"Registration failed: {str(e)}"
    
    def login_user(self, username: str, password: str) -> tuple[Optional[User], str]:
        """Authenticate user and return user object"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, username, email, password_hash, salt, bankroll, 
                       total_wagered, total_won, games_played, games_won, created_at
                FROM users WHERE username = ?
            """, (username,))
            
            row = cursor.fetchone()
            if not row:
                return None, "Username not found"
            
            user_id, username, email, password_hash, salt, bankroll, total_wagered, total_won, games_played, games_won, created_at = row
            
            if not self.verify_password(password, password_hash, salt):
                return None, "Invalid password"
            
            # Update last login
            cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
            conn.commit()
            
            user = User(
                id=user_id,
                username=username,
                email=email,
                bankroll=bankroll,
                total_wagered=total_wagered,
                total_won=total_won,
                games_played=games_played,
                games_won=games_won,
                created_at=created_at,
                last_login=datetime.now().isoformat()
            )
            
            conn.close()
            return user, "Login successful"
            
        except Exception as e:
            return None, f"Login failed: {str(e)}"
    
    def create_session(self, user_id: int) -> str:
        """Create a new user session"""
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now().replace(hour=23, minute=59, second=59).isoformat()  # Expires at end of day
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_sessions (session_id, user_id, expires_at)
            VALUES (?, ?, ?)
        """, (session_id, user_id, expires_at))
        
        conn.commit()
        conn.close()
        return session_id
    
    def get_user_by_session(self, session_id: str) -> Optional[User]:
        """Get user by session ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT u.id, u.username, u.email, u.bankroll, u.total_wagered, 
                       u.total_won, u.games_played, u.games_won, u.created_at, u.last_login
                FROM users u
                JOIN user_sessions s ON u.id = s.user_id
                WHERE s.session_id = ? AND s.expires_at > CURRENT_TIMESTAMP
            """, (session_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            user = User(*row)
            conn.close()
            return user
            
        except Exception:
            return None
    
    def update_bankroll(self, user_id: int, new_bankroll: float) -> bool:
        """Update user's bankroll"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("UPDATE users SET bankroll = ? WHERE id = ?", (new_bankroll, user_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception:
            return False
    
    def record_game(self, user_id: int, game_id: str, bet_amount: float, 
                   final_winnings: float, rounds_completed: int, result: str, 
                   cards_drawn: List = None, strategy_used: str = None) -> bool:
        """Record a completed game"""
        try:
            profit_loss = final_winnings - bet_amount
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert game record
            cursor.execute("""
                INSERT INTO game_records 
                (user_id, game_id, bet_amount, final_winnings, rounds_completed, 
                 result, profit_loss, cards_drawn, strategy_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, game_id, bet_amount, final_winnings, rounds_completed, 
                  result, profit_loss, str(cards_drawn) if cards_drawn else '', strategy_used or ''))
            
            # Update user statistics
            cursor.execute("""
                UPDATE users SET 
                    total_wagered = total_wagered + ?,
                    total_won = total_won + ?,
                    games_played = games_played + 1,
                    games_won = games_won + ?
                WHERE id = ?
            """, (bet_amount, final_winnings, 1 if result == 'won' else 0, user_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error recording game: {e}")
            return False
    
    def get_user_game_history(self, user_id: int, limit: int = 50) -> List[GameRecord]:
        """Get user's game history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, user_id, game_id, bet_amount, final_winnings, 
                       rounds_completed, result, profit_loss, created_at
                FROM game_records 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit))
            
            records = []
            for row in cursor.fetchall():
                records.append(GameRecord(*row))
            
            conn.close()
            return records
            
        except Exception:
            return []
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Get comprehensive user statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Basic stats
            cursor.execute("""
                SELECT bankroll, total_wagered, total_won, games_played, games_won
                FROM users WHERE id = ?
            """, (user_id,))
            
            user_stats = cursor.fetchone()
            if not user_stats:
                return {}
            
            bankroll, total_wagered, total_won, games_played, games_won = user_stats
            
            # Recent performance
            cursor.execute("""
                SELECT result, COUNT(*) as count
                FROM game_records 
                WHERE user_id = ? AND created_at > datetime('now', '-7 days')
                GROUP BY result
            """, (user_id,))
            
            recent_results = dict(cursor.fetchall())
            
            # Best and worst sessions
            cursor.execute("""
                SELECT MAX(profit_loss) as best_win, MIN(profit_loss) as worst_loss
                FROM game_records WHERE user_id = ?
            """, (user_id,))
            
            win_loss = cursor.fetchone()
            best_win, worst_loss = win_loss if win_loss else (0, 0)
            
            # Calculate derived stats
            win_rate = (games_won / games_played * 100) if games_played > 0 else 0
            net_profit = total_won - total_wagered
            rtp = (total_won / total_wagered * 100) if total_wagered > 0 else 0
            
            conn.close()
            
            return {
                'bankroll': bankroll,
                'total_wagered': total_wagered,
                'total_won': total_won,
                'net_profit': net_profit,
                'games_played': games_played,
                'games_won': games_won,
                'win_rate': win_rate,
                'rtp': rtp,
                'best_win': best_win or 0,
                'worst_loss': worst_loss or 0,
                'recent_results': recent_results
            }
            
        except Exception:
            return {}
    
    def claim_daily_bonus(self, user_id: int) -> float:
        """Simplified daily bonus for app.py compatibility"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if already claimed today
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT id FROM daily_bonuses 
                WHERE user_id = ? AND claimed_date = ?
            """, (user_id, today))
            
            if cursor.fetchone():
                return 0  # Already claimed
            
            # Calculate bonus (base $50 + random $0-50)
            import random
            bonus_amount = 50 + random.randint(0, 50)
            
            # Add bonus to bankroll
            cursor.execute("""
                UPDATE users SET bankroll = bankroll + ? WHERE id = ?
            """, (bonus_amount, user_id))
            
            # Record bonus claim
            cursor.execute("""
                INSERT INTO daily_bonuses (user_id, bonus_amount, claimed_date)
                VALUES (?, ?, ?)
            """, (user_id, bonus_amount, today))
            
            conn.commit()
            conn.close()
            
            return bonus_amount
            
        except Exception:
            return 0
    
    def add_funds(self, user_id: int, amount: float) -> bool:
        """Add funds to user's bankroll (for testing/admin purposes)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users SET bankroll = bankroll + ? WHERE id = ?
            """, (amount, user_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception:
            return False
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top players by net profit"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT username, bankroll, total_won - total_wagered as net_profit,
                       games_played, games_won,
                       ROUND(CAST(games_won AS FLOAT) / games_played * 100, 1) as win_rate
                FROM users 
                WHERE games_played > 0
                ORDER BY net_profit DESC 
                LIMIT ?
            """, (limit,))
            
            leaderboard = []
            for row in cursor.fetchall():
                username, bankroll, net_profit, games_played, games_won, win_rate = row
                leaderboard.append({
                    'username': username,
                    'bankroll': bankroll,
                    'net_profit': net_profit,
                    'games_played': games_played,
                    'games_won': games_won,
                    'win_rate': win_rate
                })
            
            conn.close()
            return leaderboard
            
        except Exception:
            return []
    
    # Alias methods for compatibility with app.py
    def create_user(self, username: str, email: str, password: str, starting_bankroll: float = 1000.0) -> tuple[bool, str]:
        """Alias for register_user"""
        return self.register_user(username, email, password, starting_bankroll)
    
    def authenticate_user(self, username: str, password: str) -> bool:
        """Authenticate user and return True/False"""
        user, message = self.login_user(username, password)
        return user is not None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username, returning dict format"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, username, email, bankroll, total_wagered, total_won, 
                       games_played, games_won, created_at, last_login
                FROM users WHERE username = ?
            """, (username,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            conn.close()
            return {
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'bankroll': row[3],
                'total_wagered': row[4],
                'total_won': row[5],
                'games_played': row[6],
                'games_won': row[7],
                'created_at': row[8],
                'last_login': row[9]
            }
            
        except Exception:
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID, returning dict format"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, username, email, bankroll, total_wagered, total_won, 
                       games_played, games_won, created_at, last_login
                FROM users WHERE id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            conn.close()
            return {
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'bankroll': row[3],
                'total_wagered': row[4],
                'total_won': row[5],
                'games_played': row[6],
                'games_won': row[7],
                'created_at': row[8],
                'last_login': row[9]
            }
            
        except Exception:
            return None
    
    def get_user_statistics(self, user_id: int) -> Dict:
        """Alias for get_user_stats"""
        return self.get_user_stats(user_id)
    
    def get_game_history(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get user's game history, returning dict format"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, user_id, game_id, bet_amount, final_winnings, 
                       rounds_completed, result, profit_loss, created_at
                FROM game_records 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit))
            
            records = []
            for row in cursor.fetchall():
                records.append({
                    'id': row[0],
                    'user_id': row[1],
                    'game_id': row[2],
                    'bet_amount': row[3],
                    'final_winnings': row[4],
                    'rounds_completed': row[5],
                    'result': row[6],
                    'profit_loss': row[7],
                    'created_at': row[8]
                })
            
            conn.close()
            return records
            
        except Exception:
            return []