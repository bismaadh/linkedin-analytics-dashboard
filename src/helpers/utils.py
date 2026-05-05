from __future__ import annotations
import re
from datetime import datetime, timedelta
import pytz

PACIFIC = pytz.timezone('America/Los_Angeles')
UTC = pytz.UTC

def normalize_column_name(col: str) -> str:
    """Convert column name to snake_case."""
    # Replace parentheses content: "Impressions (organic)" -> "impressions_organic"
    col = re.sub(r'\s*\(([^)]+)\)', r'_\1', col)
    # Replace spaces and special chars
    col = re.sub(r'[^a-zA-Z0-9]+', '_', col)
    # Lowercase and strip underscores
    return col.lower().strip('_')

def extract_activity_id(post_link: str) -> str | None:
    """Extract activity ID from LinkedIn URL."""
    if not post_link:
        return None
    match = re.search(r'activity:(\d+)', str(post_link))
    return match.group(1) if match else None

def get_week_start(date: datetime.date) -> datetime.date:
    """Return the Monday that starts this date's week (Mon-Tue cycle, 8 days)."""
    days_since_mon = date.weekday()  # Monday = 0
    return date - timedelta(days=days_since_mon)

def get_week_end(date: datetime.date) -> datetime.date:
    """Return the following Tuesday that ends this date's week (Mon-Tue cycle, 8 days)."""
    return get_week_start(date) + timedelta(days=7)

def get_week_label(start_date: datetime.date, end_date: datetime.date = None) -> str:
    """Return week label like 'Feb 03-Feb 09'. Accepts explicit start/end."""
    if end_date is None:
        end_date = start_date + timedelta(days=6)
    return f"{start_date.strftime('%b %d')}-{end_date.strftime('%b %d')}"
