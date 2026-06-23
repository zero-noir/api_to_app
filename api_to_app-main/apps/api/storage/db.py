import sqlite3
from pathlib import Path
from core.config import settings

DB_PATH = settings.storage_dir / 'api_to_app.sqlite3'

def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with conn() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            created_at TEXT NOT NULL,
            file_count INTEGER NOT NULL DEFAULT 0,
            endpoint_count INTEGER NOT NULL DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS files (
            session_id TEXT NOT NULL,
            path TEXT NOT NULL,
            kind TEXT NOT NULL,
            size INTEGER NOT NULL,
            content TEXT NOT NULL,
            PRIMARY KEY(session_id, path)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS generations (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            objective TEXT NOT NULL,
            app_name TEXT NOT NULL,
            artifact_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )''')
