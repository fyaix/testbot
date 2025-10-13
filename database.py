import sqlite3
from datetime import datetime, date, timedelta
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name='chatbot.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.migrate_tables()

    def create_tables(self):
        """Creates database tables if they don't exist."""
        # Tabel Users
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            status TEXT DEFAULT 'idle',
            partner_id INTEGER,
            is_premium BOOLEAN DEFAULT FALSE,
            premium_expires_at TIMESTAMP,
            daily_searches INTEGER DEFAULT 0,
            last_search_date DATE,
            gender TEXT,
            gender_preference TEXT DEFAULT 'any',
            interests TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """)
        
        # Tabel Sessions
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER,
            user2_id INTEGER,
            started_at TIMESTAMP,
            ended_at TIMESTAMP
        )
        """)
        
        # Tabel Reports
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER,
            reported_id INTEGER,
            reason TEXT,
            created_at TIMESTAMP
        )
        """)
        
        self.conn.commit()

    def migrate_tables(self):
        """Adds new columns to existing tables for backward compatibility."""
        columns_to_add = {
            'users': [
                ('is_premium', 'BOOLEAN DEFAULT FALSE'),
                ('premium_expires_at', 'TIMESTAMP'),
                ('daily_searches', 'INTEGER DEFAULT 0'),
                ('last_search_date', 'DATE'),
                ('gender', 'TEXT'),
                ('gender_preference', 'TEXT DEFAULT \'any\''),
                ('interests', 'TEXT')
            ]
        }
        for table, columns in columns_to_add.items():
            for column, col_type in columns:
                try:
                    self.cursor.execute(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}')
                    logger.info(f"Added column '{column}' to table '{table}'.")
                except sqlite3.OperationalError as e:
                    if f'duplicate column name: {column}' in str(e):
                        pass  # Column already exists, ignore
                    else:
                        raise

    def add_user(self, user_id, username):
        now = datetime.now()
        self.cursor.execute("""
        INSERT OR IGNORE INTO users (id, username, created_at, updated_at, last_search_date)
        VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, now, now, date.today()))
        self.conn.commit()

    def get_user(self, user_id):
        """Gets all data for a specific user."""
        self.cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        # Fetch column names to create a dict
        columns = [description[0] for description in self.cursor.description]
        user_data = self.cursor.fetchone()
        if user_data:
            return dict(zip(columns, user_data))
        return None

    def set_user_status(self, user_id, status, partner_id=None):
        self.cursor.execute("""
        UPDATE users SET status = ?, partner_id = ?, updated_at = ?
        WHERE id = ?
        """, (status, partner_id, datetime.now(), user_id))
        self.conn.commit()

    def get_user_status(self, user_id):
        self.cursor.execute("SELECT status, partner_id FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        if row:
            return {"status": row[0], "partner_id": row[1]}
        return None

    def get_searching_users(self, user_id, is_premium=False, gender_preference='any', user_gender=None, interests=None):
        """
        Finds available users for chatting.
        Premium users get priority and access to filters.
        """
        query = "SELECT id, interests FROM users WHERE status = 'searching' AND id != ?"
        params = [user_id]

        if is_premium:
            # --- Premium Filtering Logic ---
            if gender_preference != 'any' and user_gender:
                # Find users who match the preference and whose preference matches the current user
                query += " AND gender = ? AND (gender_preference = ? OR gender_preference = 'any')"
                params.extend([gender_preference, user_gender])

            # Interest matching will be handled in Python for simplicity

            # Premium users are matched with other premium users first, then with anyone
            query += " ORDER BY is_premium DESC, updated_at ASC"
        else:
            # --- Non-Premium Logic ---
            # Match with anyone, but prioritize those who don't have a strict gender preference
            query += " AND gender_preference = 'any'"
            query += " ORDER BY updated_at ASC"

        self.cursor.execute(query, params)
        potential_partners = self.cursor.fetchall()

        # --- Interest-based matching for premium users ---
        if is_premium and interests and potential_partners:
            user_interests = set(i.strip() for i in interests.split(','))

            scored_partners = []
            for partner_id, partner_interests_str in potential_partners:
                if not partner_interests_str:
                    score = 0
                else:
                    partner_interests = set(i.strip() for i in partner_interests_str.split(','))
                    common_interests = user_interests.intersection(partner_interests)
                    score = len(common_interests)
                scored_partners.append((partner_id, score))

            # Sort by score (desc) and then by time (asc)
            scored_partners.sort(key=lambda x: x[1], reverse=True)
            return [p[0] for p in scored_partners]

        return [p[0] for p in potential_partners]

    def create_session(self, user1_id, user2_id):
        """Creates a new chat session."""
        self.cursor.execute("""
        INSERT INTO sessions (user1_id, user2_id, started_at)
        VALUES (?, ?, ?)
        """, (user1_id, user2_id, datetime.now()))
        self.conn.commit()

    def end_chat(self, user_id):
        user_data = self.get_user_status(user_id)
        if not user_data or user_data['status'] != 'chatting':
            return None
        
        partner_id = user_data.get('partner_id')

        # Set both users to idle
        self.set_user_status(user_id, 'idle')
        if partner_id:
            self.set_user_status(partner_id, 'idle')
            
            # End the session in the database
            self.cursor.execute("""
            UPDATE sessions SET ended_at = ?
            WHERE (user1_id = ? AND user2_id = ? OR user1_id = ? AND user2_id = ?) AND ended_at IS NULL
            """, (datetime.now(), user_id, partner_id, partner_id, user_id))
            
            self.conn.commit()
        return partner_id

    def add_report(self, reporter_id, reported_id, reason):
        self.cursor.execute("""
        INSERT INTO reports (reporter_id, reported_id, reason, created_at)
        VALUES (?, ?, ?, ?)
        """, (reporter_id, reported_id, reason, datetime.now()))
        self.conn.commit()

    def check_and_reset_daily_limit(self, user_id):
        """Checks the daily search limit. Resets if it's a new day."""
        user = self.get_user(user_id)
        if not user:
            return False, 0

        if user['is_premium']:
            return True, -1 # -1 means unlimited

        today = date.today()
        last_search = date.fromisoformat(user['last_search_date']) if user['last_search_date'] else today

        if last_search < today:
            # It's a new day, reset the counter
            self.cursor.execute("UPDATE users SET daily_searches = 0, last_search_date = ? WHERE id = ?", (today, user_id))
            self.conn.commit()
            return True, 100

        remaining = 100 - user['daily_searches']
        if remaining > 0:
            return True, remaining

        return False, 0
    
    def increment_search_count(self, user_id):
        """Increments the search count for a user."""
        self.cursor.execute("UPDATE users SET daily_searches = daily_searches + 1 WHERE id = ?", (user_id,))
        self.conn.commit()

    def set_premium_status(self, user_id: int, days: int = 30):
        """Sets a user's status to premium for a number of days."""
        expires_at = datetime.now() + timedelta(days=days)
        self.cursor.execute(
            "UPDATE users SET is_premium = TRUE, premium_expires_at = ? WHERE id = ?",
            (expires_at, user_id)
        )
        self.conn.commit()
        logger.info(f"User {user_id} has been upgraded to premium. Expires at {expires_at}.")

    def update_user_preference(self, user_id: int, key: str, value: str):
        """Updates a specific user preference (gender, gender_preference, interests)."""
        if key not in ['gender', 'gender_preference', 'interests']:
            raise ValueError("Invalid preference key.")

        self.cursor.execute(f"UPDATE users SET {key} = ?, updated_at = ? WHERE id = ?", (value, datetime.now(), user_id))
        self.conn.commit()

    def get_stats(self):
        stats = {}
        self.cursor.execute("SELECT COUNT(*) FROM users")
        stats['total_users'] = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'chatting'")
        stats['active_users'] = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM sessions")
        stats['total_sessions'] = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM reports")
        stats['total_reports'] = self.cursor.fetchone()[0]
        return stats
    
    def get_reports(self, limit=5):
        self.cursor.execute("""
        SELECT id, reporter_id, reported_id, reason, created_at 
        FROM reports ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        return self.cursor.fetchall()

db = Database()