import pandas as pd
from datetime import date
from io import BytesIO
from .database import get_connection
from .metrics import (
    get_daily_metrics, get_posts, calculate_kpis,
    get_this_week_dates, get_last_week_dates, calculate_delta
)
from .utils import get_week_label

# Status thresholds (configurable)
THRESHOLDS = {
    'impressions_wow': {'green': 0, 'yellow': -10},  # % change
    'engagement_wow': {'green': 0, 'yellow': -5},    # % change
}

def get_status(value: float, metric_type: str) -> str:
    """Determine Green/Yellow/Red status based on thresholds."""
    thresholds = THRESHOLDS.get(metric_type, {'green': 0, 'yellow': -10})

    if value >= thresholds['green']:
        return 'green'
    elif value >= thresholds['yellow']:
        return 'yellow'
    else:
        return 'red'

def get_status_emoji(status: str) -> str:
    """Return emoji for status."""
    return {'green': '🟢', 'yellow': '🟡', 'red': '🔴'}.get(status, '⚪')

def generate_weekly_report(reference_date: date = None) -> dict:
    """Generate weekly report data."""
    if reference_date is None:
        # Use latest date in database
        conn = get_connection()
        result = pd.read_sql("SELECT MAX(date) as max_date FROM daily_metrics", conn)
        conn.close()
        reference_date = pd.to_datetime(result['max_date'].iloc[0]).date()

    # Get date ranges
    this_week_start, this_week_end = get_this_week_dates(reference_date)
    last_week_start, last_week_end = get_last_week_dates(reference_date)

    # Get metrics
    this_week_daily = get_daily_metrics(this_week_start, this_week_end)
    last_week_daily = get_daily_metrics(last_week_start, last_week_end)
    this_week_posts = get_posts(this_week_start, this_week_end)

    this_week_kpis = calculate_kpis(this_week_daily)
    last_week_kpis = calculate_kpis(last_week_daily)

    # Calculate deltas
    imp_delta, imp_delta_str = calculate_delta(
        this_week_kpis['impressions'],
        last_week_kpis['impressions']
    )
    eng_delta, eng_delta_str = calculate_delta(
        this_week_kpis['engagement_rate'],
        last_week_kpis['engagement_rate']
    )

    # Determine status
    imp_status = get_status(imp_delta, 'impressions_wow')
    eng_status = get_status(eng_delta, 'engagement_wow')

    # Overall status (worst of the two)
    status_priority = {'red': 0, 'yellow': 1, 'green': 2}
    overall_status = min([imp_status, eng_status], key=lambda x: status_priority[x])

    # Top 5 posts
    top_posts = this_week_posts.nlargest(5, 'impressions') if not this_week_posts.empty else pd.DataFrame()

    # Underperformers (engagement rate below median)
    if not this_week_posts.empty and len(this_week_posts) > 1:
        median_engagement = this_week_posts['engagement_rate'].median()
        underperformers = this_week_posts[
            this_week_posts['engagement_rate'] < median_engagement
        ].nsmallest(3, 'engagement_rate')
    else:
        underperformers = pd.DataFrame()

    return {
        'reference_date': reference_date,
        'week_label': get_week_label(this_week_start, this_week_end),
        'this_week_start': this_week_start,
        'this_week_end': this_week_end,
        'this_week_kpis': this_week_kpis,
        'last_week_kpis': last_week_kpis,
        'impressions_delta': imp_delta,
        'impressions_delta_str': imp_delta_str,
        'impressions_status': imp_status,
        'engagement_delta': eng_delta,
        'engagement_delta_str': eng_delta_str,
        'engagement_status': eng_status,
        'overall_status': overall_status,
        'top_posts': top_posts,
        'underperformers': underperformers,
    }

def export_to_excel(report: dict) -> BytesIO:
    """Export report data to Excel with multiple tabs."""
    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Raw daily data
        conn = get_connection()
        raw_daily = pd.read_sql("SELECT * FROM daily_metrics ORDER BY date", conn)
        raw_posts = pd.read_sql("SELECT * FROM posts ORDER BY created_date DESC", conn)
        conn.close()

        raw_daily.to_excel(writer, sheet_name='Raw Daily', index=False)
        raw_posts.to_excel(writer, sheet_name='Raw Posts', index=False)

        # Clean data (this week only)
        this_week_daily = get_daily_metrics(report['this_week_start'], report['this_week_end'])
        this_week_posts = get_posts(report['this_week_start'], report['this_week_end'])

        this_week_daily.to_excel(writer, sheet_name='This Week Daily', index=False)
        this_week_posts.to_excel(writer, sheet_name='This Week Posts', index=False)

        # Summary report
        summary_data = {
            'Metric': [
                'Report Week',
                'Impressions',
                'Impressions WoW Change',
                'Impressions Status',
                'Engagement Rate',
                'Engagement WoW Change',
                'Engagement Status',
                'Overall Status',
                'Clicks',
                'Reactions',
                'Comments',
                'Reposts',
            ],
            'Value': [
                report['week_label'],
                report['this_week_kpis']['impressions'],
                report['impressions_delta_str'],
                report['impressions_status'].upper(),
                f"{report['this_week_kpis']['engagement_rate']:.2%}",
                report['engagement_delta_str'],
                report['engagement_status'].upper(),
                report['overall_status'].upper(),
                report['this_week_kpis']['clicks'],
                report['this_week_kpis']['reactions'],
                report['this_week_kpis']['comments'],
                report['this_week_kpis']['reposts'],
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Weekly Report', index=False)

        # Top posts
        if not report['top_posts'].empty:
            report['top_posts'][['post_title', 'created_date', 'impressions', 'engagement_rate']].to_excel(
                writer, sheet_name='Top Posts', index=False
            )

        # Underperformers
        if not report['underperformers'].empty:
            report['underperformers'][['post_title', 'created_date', 'impressions', 'engagement_rate']].to_excel(
                writer, sheet_name='Underperformers', index=False
            )

    output.seek(0)
    return output
