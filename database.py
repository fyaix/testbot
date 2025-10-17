import sqlite3
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('chatbot.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Tabel Users
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            status TEXT DEFAULT 'idle',
            partner_id INTEGER,
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

    def add_user(self, user_id, username):
        self.cursor.execute("""
        INSERT OR IGNORE INTO users (id, username, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        """, (user_id, username, datetime.now(), datetime.now()))
        self.conn.commit()

    def set_user_status(self, user_id, status, partner_id=None):
        # Perbaikan: Gunakan parameter yang benar
        if partner_id is not None:
            self.cursor.execute("""
            UPDATE users SET status = ?, partner_id = ?, updated_at = ?
            WHERE id = ?
            """, (status, partner_id, datetime.now(), user_id))
        else:
            self.cursor.execute("""
            UPDATE users SET status = ?, partner_id = NULL, updated_at = ?
            WHERE id = ?
            """, (status, datetime.now(), user_id))
        self.conn.commit()

    def get_user_status(self, user_id):
        self.cursor.execute("""
        SELECT status, partner_id FROM users WHERE id = ?
        """, (user_id,))
        row = self.cursor.fetchone()
        if row:
            return {"status": row[0], "partner_id": row[1]}
        return None

    def get_searching_users(self, exclude_user_id=None):
        query = "SELECT id FROM users WHERE status = 'searching'"
        params = []
        if exclude_user_id:
            query += " AND id != ?"
            params.append(exclude_user_id)
        self.cursor.execute(query, params)
        return [row[0] for row in self.cursor.fetchall()]

    def add_session(self, user1_id, user2_id):
        """Logs a new chat session."""
        self.cursor.execute(
            "INSERT INTO sessions (user1_id, user2_id, started_at) VALUES (?, ?, ?)",
            (user1_id, user2_id, datetime.now())
        )
        self.conn.commit()

    def end_chat(self, user_id):
        user_data = self.get_user_status(user_id)
        if not user_data:
            return None

        partner_id = user_data.get('partner_id')
        if partner_id:
            # Update status kedua user
            self.cursor.execute("""
            UPDATE users SET status = 'idle', partner_id = NULL, updated_at = ?
            WHERE id = ?
            """, (datetime.now(), user_id))
            
            self.cursor.execute("""
            UPDATE users SET status = 'idle', partner_id = NULL, updated_at = ?
            WHERE id = ?
            """, (datetime.now(), partner_id))

            # Update session
            self.cursor.execute("""
            UPDATE sessions SET ended_at = ?
            WHERE user1_id = ? AND user2_id = ? AND ended_at IS NULL
            """, (datetime.now(), user_id, partner_id))

            self.conn.commit()
            return partner_id
        return None

    def add_report(self, reporter_id, reported_id, reason):
        self.cursor.execute("""
        INSERT INTO reports (reporter_id, reported_id, reason, created_at)
        VALUES (?, ?, ?, ?)
        """, (reporter_id, reported_id, reason, datetime.now()))
        self.conn.commit()

    def is_premium_user(self, user_id):
        # Untuk sementara, return False
        return False

    def get_stats(self):
        # Total users
        self.cursor.execute("SELECT COUNT(*) FROM users")
        total_users = self.cursor.fetchone()[0]

        # Active users (status chatting)
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'chatting'")
        active_users = self.cursor.fetchone()[0]

        # Total sessions
        self.cursor.execute("SELECT COUNT(*) FROM sessions")
        total_sessions = self.cursor.fetchone()[0]

        # Total reports
        self.cursor.execute("SELECT COUNT(*) FROM reports")
        total_reports = self.cursor.fetchone()[0]

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_sessions": total_sessions,
            "total_reports": total_reports
        }

    def get_reports(self, limit=5):
        self.cursor.execute("""
        SELECT id, reporter_id, reported_id, reason, created_at
        FROM reports
        ORDER BY created_at DESC
        LIMIT ?
        """, (limit,))
        return self.cursor.fetchall()

# Tambahkan baris ini di akhir file
db = Database()
