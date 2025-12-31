import sqlite3
from datetime import datetime
from contextlib import contextmanager

DATABASE_PATH = 'meshtastic_messages.db'

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_database():
    """Initialize the database schema"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_node INTEGER NOT NULL,
                to_node INTEGER NOT NULL,
                text TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                channel_index INTEGER DEFAULT 0,
                is_dm BOOLEAN NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON messages(timestamp DESC)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_is_dm
            ON messages(is_dm)
        ''')

        print("Database initialized successfully")

def save_message(from_node, to_node, text, timestamp, channel_index=0):
    """Save a message to the database"""
    # Determine if it's a DM
    is_dm = to_node != 4294967295  # Not broadcast (0xffffffff)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages
            (from_node, to_node, text, timestamp, channel_index, is_dm)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (from_node, to_node, text, timestamp, channel_index, is_dm))

    print(f"Saved message to database: from={from_node}, to={to_node}, is_dm={is_dm}")

def get_recent_messages(limit=100, is_dm=None):
    """
    Get recent messages from the database

    Args:
        limit: Maximum number of messages to return
        is_dm: If True, only DMs. If False, only channel messages. If None, all messages.

    Returns:
        List of message dictionaries
    """
    with get_db() as conn:
        cursor = conn.cursor()

        if is_dm is None:
            query = '''
                SELECT * FROM messages
                ORDER BY timestamp DESC
                LIMIT ?
            '''
            cursor.execute(query, (limit,))
        else:
            query = '''
                SELECT * FROM messages
                WHERE is_dm = ?
                ORDER BY timestamp DESC
                LIMIT ?
            '''
            cursor.execute(query, (is_dm, limit))

        rows = cursor.fetchall()

        # Convert to list of dicts and reverse to get chronological order
        messages = []
        for row in reversed(rows):
            messages.append({
                'from': row['from_node'],
                'to': row['to_node'],
                'text': row['text'],
                'time': row['timestamp'],
                'is_dm': bool(row['is_dm']),
                'channel_index': row['channel_index']
            })

        return messages

def get_message_count():
    """Get total number of messages in database"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM messages')
        return cursor.fetchone()['count']
