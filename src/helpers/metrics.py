import pandas as pd
from datetime import date, timedelta
from .database import get_connection
from .utils import PACIFIC

def get_date_range() -> tuple[date, date]:
    """Get min and max dates from daily_metrics."""
    conn = get_connection()
    df = pd.read_sql("SELECT MIN(date) as min_date, MAX(date) as max_date FROM daily_metrics", conn)
    conn.close()
    if df['min_date'].iloc[0] is None:
        return None, None
    return pd.to_datetime(df['min_date'].iloc[0]).date(), pd.to_datetime(df['max_date'].iloc[0]).date()

def get_daily_metrics(start_date: date, end_date: date) -> pd.DataFrame:
    """Get daily metrics for date range."""
    conn = get_connection()
    df = pd.read_sql("""
        SELECT * FROM daily_metrics
        WHERE date >= ? AND date <= ?
        ORDER BY date
    """, conn, params=(str(start_date), str(end_date)))
    conn.close()
    if not df.empty:
        df['date'] = pd.to_datetime(df['date']).dt.date
    return df

def get_posts(start_date: date, end_date: date, post_type: str = None, content_type: str = None) -> pd.DataFrame:
    """Get posts for date range with optional filters."""
    conn = get_connection()
    query = "SELECT * FROM posts WHERE created_date >= ? AND created_date <= ?"
    params = [str(start_date), str(end_date)]

    if post_type and post_type != "All":
        query += " AND post_type = ?"
        params.append(post_type)

    if content_type and content_type != "All":
        if content_type == "Video":
            query += " AND content_type = 'Video'"
        else:
            query += " AND (content_type IS NULL OR content_type != 'Video')"

    query += " ORDER BY created_date DESC"
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    if not df.empty:
        df['created_date'] = pd.to_datetime(df['created_date']).dt.date
    return df

def calculate_kpis(df: pd.DataFrame) -> dict:
    """Calculate KPI summary from daily metrics DataFrame."""
    if df.empty:
        return {
            'impressions': 0,
            'clicks': 0,
            'reactions': 0,
            'comments': 0,
            'reposts': 0,
            'engagement_rate': 0.0,
        }

    total_impressions = df['impressions_total'].sum()
    total_clicks = df['clicks_total'].sum()
    total_reactions = df['reactions_total'].sum()
    total_comments = df['comments_total'].sum()
    total_reposts = df['reposts_total'].sum()

    # Calculate engagement rate: (reactions + comments + reposts + clicks) / impressions
    if total_impressions > 0:
        engagement_rate = (total_reactions + total_comments + total_reposts + total_clicks) / total_impressions
    else:
        engagement_rate = 0.0

    return {
        'impressions': int(total_impressions),
        'clicks': int(total_clicks),
        'reactions': int(total_reactions),
        'comments': int(total_comments),
        'reposts': int(total_reposts),
        'engagement_rate': engagement_rate,
    }

def get_this_week_dates(reference_date: date = None) -> tuple[date, date]:
    """Get last 7 days ending at reference_date (latest data date)."""
    if reference_date is None:
        reference_date = date.today()
    end = reference_date
    start = end - timedelta(days=6)  # 7 days inclusive
    return start, end

def get_last_week_dates(reference_date: date = None) -> tuple[date, date]:
    """Get the 7 days prior to 'this week'."""
    if reference_date is None:
        reference_date = date.today()
    this_week_start = reference_date - timedelta(days=6)
    end = this_week_start - timedelta(days=1)
    start = end - timedelta(days=6)  # 7 days inclusive
    return start, end

def get_mtd_dates(reference_date: date = None) -> tuple[date, date]:
    """Get start of month to reference date."""
    if reference_date is None:
        reference_date = date.today()
    start = reference_date.replace(day=1)
    return start, reference_date

def get_all_time_dates() -> tuple[date, date]:
    """Get all-time date range from earliest data to latest."""
    min_date, max_date = get_date_range()
    if min_date is None:
        return date.today(), date.today()
    return min_date, max_date

def calculate_delta(current: float, previous: float) -> tuple[float, str]:
    """Calculate percentage change and format string."""
    if previous == 0:
        if current > 0:
            return 100.0, "+100%"
        return 0.0, "—"

    delta = ((current - previous) / previous) * 100
    if delta > 0:
        return delta, f"+{delta:.1f}%"
    else:
        return delta, f"{delta:.1f}%"
