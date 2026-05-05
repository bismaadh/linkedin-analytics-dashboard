import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "linkedin_metrics.db"

def get_connection():
    """Get SQLite connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database schema."""
    conn = get_connection()
    cursor = conn.cursor()

    # Daily aggregated metrics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_metrics (
            date DATE PRIMARY KEY,
            impressions_organic INTEGER,
            impressions_sponsored INTEGER,
            impressions_total INTEGER,
            unique_impressions_organic INTEGER,
            clicks_organic INTEGER,
            clicks_sponsored INTEGER,
            clicks_total INTEGER,
            reactions_organic INTEGER,
            reactions_sponsored INTEGER,
            reactions_total INTEGER,
            comments_organic INTEGER,
            comments_sponsored INTEGER,
            comments_total INTEGER,
            reposts_organic INTEGER,
            reposts_sponsored INTEGER,
            reposts_total INTEGER,
            engagement_rate_organic REAL,
            engagement_rate_sponsored REAL,
            engagement_rate_total REAL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_file TEXT
        )
    """)

    # Individual posts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            post_link TEXT PRIMARY KEY,
            activity_id TEXT,
            post_title TEXT,
            post_type TEXT,
            campaign_name TEXT,
            posted_by TEXT,
            created_date DATE,
            campaign_start_date DATE,
            campaign_end_date DATE,
            audience TEXT,
            impressions INTEGER,
            views INTEGER,
            offsite_views INTEGER,
            clicks INTEGER,
            ctr REAL,
            likes INTEGER,
            comments INTEGER,
            reposts INTEGER,
            follows INTEGER,
            engagement_rate REAL,
            content_type TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_file TEXT
        )
    """)

    # Upload history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            file_type TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            rows_added INTEGER,
            rows_updated INTEGER
        )
    """)

    conn.commit()
    conn.close()
