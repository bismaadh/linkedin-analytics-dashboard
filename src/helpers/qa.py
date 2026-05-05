from __future__ import annotations
import pandas as pd
from datetime import timedelta
from .database import get_connection

def check_missing_dates(start_date, end_date) -> list[str]:
    """Check for gaps in daily metrics date sequence."""
    conn = get_connection()
    df = pd.read_sql("""
        SELECT date FROM daily_metrics
        WHERE date >= ? AND date <= ?
        ORDER BY date
    """, conn, params=(str(start_date), str(end_date)))
    conn.close()

    if df.empty:
        return []

    df['date'] = pd.to_datetime(df['date']).dt.date
    actual_dates = set(df['date'])

    # Generate expected date range
    expected_dates = set()
    current = start_date
    while current <= end_date:
        expected_dates.add(current)
        current += timedelta(days=1)

    missing = expected_dates - actual_dates
    return sorted([d.strftime('%Y-%m-%d') for d in missing])

def check_duplicate_urls() -> list[dict]:
    """Check for posts with same URL but different data."""
    conn = get_connection()
    df = pd.read_sql("""
        SELECT post_link, COUNT(*) as count
        FROM posts
        GROUP BY post_link
        HAVING COUNT(*) > 1
    """, conn)
    conn.close()

    return df.to_dict('records')

def check_zero_metrics() -> list[dict]:
    """Check for dates with zero impressions (may indicate data delay)."""
    conn = get_connection()
    df = pd.read_sql("""
        SELECT date, impressions_total
        FROM daily_metrics
        WHERE impressions_total = 0 OR impressions_total IS NULL
        ORDER BY date DESC
        LIMIT 10
    """, conn)
    conn.close()

    return df.to_dict('records')

def check_outliers(threshold_std: float = 3.0) -> list[dict]:
    """Check for dates with metrics > threshold standard deviations from mean."""
    conn = get_connection()
    df = pd.read_sql("SELECT date, impressions_total FROM daily_metrics", conn)
    conn.close()

    if df.empty or len(df) < 5:
        return []

    mean = df['impressions_total'].mean()
    std = df['impressions_total'].std()

    if std == 0:
        return []

    outliers = df[abs(df['impressions_total'] - mean) > threshold_std * std]

    return [
        {
            'date': row['date'],
            'impressions': row['impressions_total'],
            'deviation': f"{(row['impressions_total'] - mean) / std:.1f}σ"
        }
        for _, row in outliers.iterrows()
    ]

def run_all_checks(start_date, end_date) -> dict:
    """Run all QA checks and return results."""
    return {
        'missing_dates': check_missing_dates(start_date, end_date),
        'duplicate_urls': check_duplicate_urls(),
        'zero_metrics': check_zero_metrics(),
        'outliers': check_outliers(),
    }
