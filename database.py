import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

# Use absolute path so database is always in the same location
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'meshtastic_messages.db')

@contextmanager
def get_db():
    """Context manager for database connections"""
    # Set a timeout to handle concurrent access better
    conn = sqlite3.connect(DATABASE_PATH, timeout=10.0)
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

        # Nodes table - stores node information
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                node_num INTEGER PRIMARY KEY,
                short_name TEXT,
                long_name TEXT,
                node_id TEXT,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
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

def upsert_node(node_num, short_name=None, long_name=None, node_id=None):
    """
    Insert or update node information in the database.
    Only updates fields if the new value is not None (preserves existing data).

    Args:
        node_num: Node number (primary key)
        short_name: Short name of the node
        long_name: Long name of the node
        node_id: Node ID string
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO nodes (node_num, short_name, long_name, node_id, last_seen)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(node_num) DO UPDATE SET
                short_name = COALESCE(excluded.short_name, nodes.short_name),
                long_name = COALESCE(excluded.long_name, nodes.long_name),
                node_id = COALESCE(excluded.node_id, nodes.node_id),
                last_seen = CURRENT_TIMESTAMP
        ''', (node_num, short_name, long_name, node_id))

    print(f"Saved node to database: {node_num} ({short_name})")

def get_all_nodes():
    """
    Get all nodes from the database

    Returns:
        Dict mapping node_num to node info
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM nodes')
        rows = cursor.fetchall()

        nodes = {}
        for row in rows:
            nodes[row['node_num']] = {
                'shortName': row['short_name'],
                'longName': row['long_name'],
                'id': row['node_id'],
                'lastSeen': row['last_seen']
            }

        return nodes

def get_node(node_num):
    """
    Get a specific node from the database

    Args:
        node_num: Node number to look up

    Returns:
        Dict with node info or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM nodes WHERE node_num = ?', (node_num,))
        row = cursor.fetchone()

        if row:
            return {
                'shortName': row['short_name'],
                'longName': row['long_name'],
                'id': row['node_id'],
                'lastSeen': row['last_seen']
            }

        return None
