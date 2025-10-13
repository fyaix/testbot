import sqlite3
import logging
import time
import random
from config import DB_PATH

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path=DB_PATH):
        """Initializes the database connection."""
        try:
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            self.init_db()
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise

    def init_db(self):
        """Creates all necessary tables if they don't exist."""
        with self.conn:
            # User Profiles Table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                gender TEXT,
                age INTEGER,
                bio TEXT,
                photo_id TEXT,
                language TEXT,
                pro_expires_at INTEGER,
                is_banned INTEGER DEFAULT 0,
                banned_until INTEGER DEFAULT 0,
                hobbies TEXT,
                points INTEGER DEFAULT 0
            )''')

            # Reports Table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER,
                reported_id INTEGER,
                reason TEXT,
                timestamp INTEGER
            )''')

            # Block List Table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS block_list (
                user_id INTEGER,
                blocked_id INTEGER,
                PRIMARY KEY(user_id, blocked_id)
            )''')

            # Chat Queue (can be removed if find_partner is efficient enough)
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_queue (
                user_id INTEGER PRIMARY KEY,
                gender_pref TEXT,
                hobby_pref TEXT,
                age_min INTEGER,
                age_max INTEGER,
                is_pro INTEGER DEFAULT 0
            )''')

            # Chat Sessions Table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                user_id INTEGER PRIMARY KEY,
                partner_id INTEGER,
                started_at INTEGER,
                secret_mode INTEGER DEFAULT 0
            )''')

            # Group Chats Table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY AUTOINCREMENT,
                members TEXT,
                started_at INTEGER
            )''')

            # Quiz Winners Table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS quiz_winners (
                quiz_id INTEGER,
                user_id INTEGER,
                prize TEXT
            )''')

            # Feedback Table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                partner_id INTEGER,
                rating INTEGER,
                comment TEXT,
                timestamp INTEGER
            )''')

            # Polls Table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS polls (
                poll_id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT,
                options TEXT,
                responses TEXT,
                created_at INTEGER
            )''')

            # Active Quizzes Table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_quizzes (
                quiz_id INTEGER PRIMARY KEY,
                question TEXT,
                answer TEXT,
                winners TEXT,
                created_at INTEGER
            )''')

            # Create indexes for faster queries
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_profiles_gender ON user_profiles(gender)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_profiles_age ON user_profiles(age)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_profiles_banned ON user_profiles(is_banned)")

        logger.info("Database initialized successfully.")

    def execute(self, query, params=()):
        """A helper to execute a query and commit."""
        with self.conn:
            self.cursor.execute(query, params)

    def fetchone(self, query, params=()):
        """A helper to execute a query and fetch one result."""
        with self.conn:
            self.cursor.execute(query, params)
            return self.cursor.fetchone()

    def fetchall(self, query, params=()):
        """A helper to execute a query and fetch all results."""
        with self.conn:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()

    def is_pro(self, user_id):
        """Checks if a user has an active pro subscription."""
        row = self.fetchone("SELECT pro_expires_at FROM user_profiles WHERE user_id=?", (user_id,))
        return bool(row and row[0] and row[0] > int(time.time()))

    def get_profile(self, user_id):
        """Retrieves a user's profile data as a dictionary."""
        row = self.fetchone("SELECT gender, age, bio, photo_id, hobbies, points FROM user_profiles WHERE user_id=?", (user_id,))
        if row:
            data = dict(zip(["gender", "age", "bio", "photo_id", "hobbies", "points"], row))
            data["hobbies"] = data["hobbies"].split(",") if data.get("hobbies") else []
            return data
        return {}

    def is_profile_complete(self, user_id):
        """Checks if a user has filled out all essential profile fields."""
        profile = self.get_profile(user_id)
        return all([profile.get("gender"), profile.get("age"), profile.get("bio"), profile.get("photo_id")])

    def is_in_chat(self, user_id):
        """Checks if a user is currently in a chat session."""
        return self.fetchone("SELECT partner_id FROM sessions WHERE user_id=?", (user_id,)) is not None

    def is_blocked(self, user_id, target_id):
        """Checks if user_id has blocked target_id."""
        return self.fetchone("SELECT 1 FROM block_list WHERE user_id=? AND blocked_id=?", (user_id, target_id)) is not None

    def add_session(self, user_id, partner_id, secret_mode=False):
        """Creates a new chat session for both users."""
        now = int(time.time())
        self.execute("INSERT OR REPLACE INTO sessions (user_id, partner_id, started_at, secret_mode) VALUES (?,?,?,?)", (user_id, partner_id, now, int(secret_mode)))
        self.execute("INSERT OR REPLACE INTO sessions (user_id, partner_id, started_at, secret_mode) VALUES (?,?,?,?)", (partner_id, user_id, now, int(secret_mode)))

    def end_session(self, user_id):
        """Ends a chat session and returns the partner's ID."""
        row = self.fetchone("SELECT partner_id FROM sessions WHERE user_id=?", (user_id,))
        if row:
            partner_id = row[0]
            self.execute("DELETE FROM sessions WHERE user_id IN (?, ?)", (user_id, partner_id))
            return partner_id
        return None

    def find_partner(self, user_id, gender_pref=None, hobby_pref=None, age_min=None, age_max=None):
        """Finds a suitable partner based on preferences."""
        blocked_ids_rows = self.fetchall("SELECT blocked_id FROM block_list WHERE user_id=?", (user_id,))
        blocked_ids = {row[0] for row in blocked_ids_rows}

        query = """
            SELECT u.user_id, u.hobbies
            FROM user_profiles u
            LEFT JOIN sessions s ON u.user_id = s.user_id
            WHERE u.user_id != ? AND s.user_id IS NULL AND u.is_banned = 0
        """
        params = [user_id]

        if gender_pref:
            query += " AND u.gender=?"
            params.append(gender_pref)
        if age_min and age_max:
            query += " AND u.age BETWEEN ? AND ?"
            params.extend([age_min, age_max])

        potential_partners = self.fetchall(query, tuple(params))

        # Filter out blocked users
        valid_partners = [p for p in potential_partners if p[0] not in blocked_ids]

        if not valid_partners:
            return None

        # Prioritize by hobby if specified
        if hobby_pref:
            for pid, hobbies_str in valid_partners:
                hobbies = hobbies_str.split(',') if hobbies_str else []
                if hobby_pref in hobbies:
                    return pid

        # Fallback to random choice from valid partners
        return random.choice(valid_partners)[0] if valid_partners else None

    def update_user_profile(self, user_id, data):
        """Updates a user's profile with the given data dictionary."""
        # Ensure hobbies are stored as a comma-separated string
        if 'hobbies' in data and isinstance(data['hobbies'], list):
            data['hobbies'] = ','.join(data['hobbies'])
            
        query = "UPDATE user_profiles SET "
        query += ", ".join([f"{key}=?" for key in data.keys()])
        query += " WHERE user_id=?"

        params = list(data.values())
        params.append(user_id)

        self.execute(query, tuple(params))

    def ensure_user_exists(self, user_id, username):
        """Ensures a user exists in the database, creating them if not."""
        row = self.fetchone("SELECT user_id FROM user_profiles WHERE user_id=?", (user_id,))
        if not row:
            self.execute("INSERT INTO user_profiles (user_id, username) VALUES (?,?)", (user_id, username))
        else:
            self.execute("UPDATE user_profiles SET username=? WHERE user_id=?", (username, user_id))

    def add_report(self, reporter_id, reported_id, reason):
        """Adds a report to the database."""
        self.execute("INSERT INTO reports (reporter_id, reported_id, reason, timestamp) VALUES (?,?,?,?)",
                     (reporter_id, reported_id, reason, int(time.time())))

    def ban_user(self, user_id, duration_seconds):
        """Bans a user for a specific duration."""
        banned_until = int(time.time()) + duration_seconds
        self.execute("UPDATE user_profiles SET is_banned=1, banned_until=? WHERE user_id=?", (banned_until, user_id))

    def unban_user(self, user_id):
        """Unbans a user."""
        self.execute("UPDATE user_profiles SET is_banned=0, banned_until=0 WHERE user_id=?", (user_id,))

    def check_ban_status(self, user_id):
        """Checks if a user is currently banned and returns the expiry timestamp."""
        row = self.fetchone("SELECT is_banned, banned_until FROM user_profiles WHERE user_id=?", (user_id,))
        if row and row[0] and row[1] > int(time.time()):
            return row[1]  # Return expiry time
        elif row and row[0]: # Ban expired
            self.unban_user(user_id)
        return None

    def add_quiz_winner(self, quiz_id, user_id, prize="pending"):
        """Records a quiz winner."""
        self.execute("INSERT INTO quiz_winners (quiz_id, user_id, prize) VALUES (?,?,?)", (quiz_id, user_id, prize))

    def grant_pro_for_quiz(self, user_id, quiz_id, days=1):
        """Grants pro status as a quiz reward."""
        expires_at = int(time.time()) + days * 86400
        self.execute("UPDATE user_profiles SET pro_expires_at=? WHERE user_id=?", (expires_at, user_id))
        self.execute("UPDATE quiz_winners SET prize='pro' WHERE quiz_id=? AND user_id=?", (quiz_id, user_id))

    def grant_points_for_quiz(self, user_id, quiz_id, points=1):
        """Grants points as a quiz reward."""
        self.execute("UPDATE user_profiles SET points=points+? WHERE user_id=?", (points, user_id))
        self.execute("UPDATE quiz_winners SET prize='point' WHERE quiz_id=? AND user_id=?", (quiz_id, user_id))

    def redeem_points_for_pro(self, user_id, points_needed, days):
        """Redeems points for pro subscription."""
        current_points = self.get_profile(user_id).get('points', 0)
        if current_points >= points_needed:
            expires_at = int(time.time()) + days * 86400
            self.execute("UPDATE user_profiles SET pro_expires_at=?, points=points-? WHERE user_id=?", (expires_at, points_needed, user_id))
            return True
        return False

    def create_quiz(self, quiz_id, question, answer):
        """Creates a new active quiz in the database."""
        self.execute("INSERT INTO active_quizzes (quiz_id, question, answer, winners, created_at) VALUES (?, ?, ?, ?, ?)",
                     (quiz_id, question, answer, "", int(time.time())))

    def get_quiz(self, quiz_id):
        """Retrieves quiz data from the database."""
        row = self.fetchone("SELECT question, answer, winners FROM active_quizzes WHERE quiz_id=?", (quiz_id,))
        if row:
            return {"question": row[0], "answer": row[1], "winners": row[2].split(',') if row[2] else []}
        return None

    def add_winner_to_quiz(self, quiz_id, user_id):
        """Adds a winner to a quiz and updates the database."""
        quiz = self.get_quiz(quiz_id)
        if quiz:
            winners = quiz['winners']
            if str(user_id) not in winners:
                winners.append(str(user_id))
                self.execute("UPDATE active_quizzes SET winners=? WHERE quiz_id=?", (','.join(winners), quiz_id))
                return True
        return False

    def grant_pro(self, user_id, days):
        """Grants or extends a user's pro subscription."""
        # Check current expiry
        current_expiry = self.fetchone("SELECT pro_expires_at FROM user_profiles WHERE user_id=?", (user_id,))
        start_time = int(time.time())
        if current_expiry and current_expiry[0] and current_expiry[0] > start_time:
            start_time = current_expiry[0]

        new_expiry = start_time + days * 86400
        self.execute("UPDATE user_profiles SET pro_expires_at=? WHERE user_id=?", (new_expiry, user_id))

    def get_all_user_ids(self):
        """Fetches all user IDs from the database."""
        return [row[0] for row in self.fetchall("SELECT user_id FROM user_profiles")]

    def get_stats(self):
        """Gathers various statistics from the database."""
        stats = {}
        stats['total_users'] = self.fetchone("SELECT COUNT(*) FROM user_profiles")[0]
        stats['active_chats'] = self.fetchone("SELECT COUNT(*)/2 FROM sessions")[0]
        stats['pro_users'] = self.fetchone("SELECT COUNT(*) FROM user_profiles WHERE pro_expires_at > ?", (int(time.time()),))[0]
        stats['reports_24h'] = self.fetchone("SELECT COUNT(*) FROM reports WHERE timestamp > ?", (int(time.time()) - 86400,))[0]
        return stats

# Create a single instance of the database to be used across the bot
db_instance = Database()