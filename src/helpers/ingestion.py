import pandas as pd
from datetime import datetime
from .database import get_connection
from .utils import normalize_column_name, extract_activity_id

# Column mapping: normalized name -> original variations
DAILY_COLUMN_MAP = {
    'date': ['Date'],
    'impressions_organic': ['Impressions (organic)'],
    'impressions_sponsored': ['Impressions (sponsored)'],
    'impressions_total': ['Impressions (total)'],
    'unique_impressions_organic': ['Unique impressions (organic)'],
    'clicks_organic': ['Clicks (organic)'],
    'clicks_sponsored': ['Clicks (sponsored)'],
    'clicks_total': ['Clicks (total)'],
    'reactions_organic': ['Reactions (organic)'],
    'reactions_sponsored': ['Reactions (sponsored)'],
    'reactions_total': ['Reactions (total)'],
    'comments_organic': ['Comments (organic)'],
    'comments_sponsored': ['Comments (sponsored)'],
    'comments_total': ['Comments (total)'],
    'reposts_organic': ['Reposts (organic)'],
    'reposts_sponsored': ['Reposts (sponsored)'],
    'reposts_total': ['Reposts (total)'],
    'engagement_rate_organic': ['Engagement rate (organic)'],
    'engagement_rate_sponsored': ['Engagement rate (sponsored)'],
    'engagement_rate_total': ['Engagement rate (total)'],
}

POSTS_COLUMN_MAP = {
    'post_title': ['Post title'],
    'post_link': ['Post link'],
    'post_type': ['Post type'],
    'campaign_name': ['Campaign name'],
    'posted_by': ['Posted by'],
    'created_date': ['Created date'],
    'campaign_start_date': ['Campaign start date'],
    'campaign_end_date': ['Campaign end date'],
    'audience': ['Audience'],
    'impressions': ['Impressions'],
    'views': ['Views'],
    'offsite_views': ['Offsite Views'],
    'clicks': ['Clicks'],
    'ctr': ['Click through rate (CTR)'],
    'likes': ['Likes'],
    'comments': ['Comments'],
    'reposts': ['Reposts'],
    'follows': ['Follows'],
    'engagement_rate': ['Engagement rate'],
    'content_type': ['Content Type'],
}

def detect_file_type(df: pd.DataFrame) -> str:
    """Detect if DataFrame is daily metrics or posts based on columns."""
    cols_lower = set(c.lower().strip() for c in df.columns)
    cols = set(df.columns)
    
    # Check for daily metrics - look for Date and any Impressions column
    has_date = 'Date' in cols or 'date' in cols_lower
    has_impressions_organic = any('impressions' in c.lower() and 'organic' in c.lower() for c in df.columns)
    has_impressions_total = any('impressions' in c.lower() and 'total' in c.lower() for c in df.columns)
    
    if has_date and (has_impressions_organic or has_impressions_total):
        return 'daily'
    
    # Check for posts - look for Post link or Post title
    has_post_link = 'Post link' in cols or 'post link' in cols_lower
    has_post_title = 'Post title' in cols or 'post title' in cols_lower
    
    if has_post_link or has_post_title:
        return 'posts'
    
    # Print columns for debugging
    raise ValueError(f"Unknown file format. Expected daily metrics or posts export. Found columns: {list(df.columns)[:10]}")

def parse_file(file, filename: str) -> pd.DataFrame:
    """Parse uploaded file (Excel or CSV), skipping description row."""
    if filename.endswith('.csv'):
        # LinkedIn CSV exports have description on row 1, headers on row 2
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        for encoding in encodings:
            try:
                file.seek(0)  # Reset file pointer
                df = pd.read_csv(file, skiprows=1, encoding=encoding)
                return df
            except (UnicodeDecodeError, LookupError):
                continue
        # If all encodings fail, try with error handling
        file.seek(0)
        df = pd.read_csv(file, skiprows=1, encoding='utf-8', errors='ignore')
        return df
    else:
        # Excel file - skip LinkedIn description header
        df = pd.read_excel(file, skiprows=1)
        return df

def normalize_dataframe(df: pd.DataFrame, column_map: dict) -> pd.DataFrame:
    """Rename columns to normalized names."""
    rename_map = {}
    for norm_name, variations in column_map.items():
        for var in variations:
            if var in df.columns:
                rename_map[var] = norm_name
                break
    return df.rename(columns=rename_map)

def ingest_daily_metrics(df: pd.DataFrame, source_file: str) -> tuple[int, int]:
    """Insert or update daily metrics. Returns (rows_added, rows_updated)."""
    df = normalize_dataframe(df, DAILY_COLUMN_MAP)
    df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y').dt.strftime('%Y-%m-%d')
    df['source_file'] = source_file
    uploaded_at = datetime.now().isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    rows_added = 0
    rows_updated = 0

    for _, row in df.iterrows():
        date_val = row['date']
        # Check if exists
        cursor.execute("SELECT 1 FROM daily_metrics WHERE date = ?", (date_val,))
        exists = cursor.fetchone() is not None

        # INSERT OR REPLACE
        cursor.execute("""
            INSERT OR REPLACE INTO daily_metrics (
                date, impressions_organic, impressions_sponsored, impressions_total,
                unique_impressions_organic, clicks_organic, clicks_sponsored, clicks_total,
                reactions_organic, reactions_sponsored, reactions_total,
                comments_organic, comments_sponsored, comments_total,
                reposts_organic, reposts_sponsored, reposts_total,
                engagement_rate_organic, engagement_rate_sponsored, engagement_rate_total,
                uploaded_at, source_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date_val, row.get('impressions_organic'), row.get('impressions_sponsored'),
            row.get('impressions_total'), row.get('unique_impressions_organic'),
            row.get('clicks_organic'), row.get('clicks_sponsored'), row.get('clicks_total'),
            row.get('reactions_organic'), row.get('reactions_sponsored'), row.get('reactions_total'),
            row.get('comments_organic'), row.get('comments_sponsored'), row.get('comments_total'),
            row.get('reposts_organic'), row.get('reposts_sponsored'), row.get('reposts_total'),
            row.get('engagement_rate_organic'), row.get('engagement_rate_sponsored'),
            row.get('engagement_rate_total'), uploaded_at, source_file
        ))

        if exists:
            rows_updated += 1
        else:
            rows_added += 1

    conn.commit()
    conn.close()
    return rows_added, rows_updated

def ingest_posts(df: pd.DataFrame, source_file: str) -> tuple[int, int]:
    """Insert or update posts. Returns (rows_added, rows_updated)."""
    df = normalize_dataframe(df, POSTS_COLUMN_MAP)
    df['created_date'] = pd.to_datetime(df['created_date'], format='%m/%d/%Y').dt.strftime('%Y-%m-%d')
    df['activity_id'] = df['post_link'].apply(extract_activity_id)
    uploaded_at = datetime.now().isoformat()

    # Handle optional date columns
    for col in ['campaign_start_date', 'campaign_end_date']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format='%m/%d/%Y', errors='coerce').dt.strftime('%Y-%m-%d')

    conn = get_connection()
    cursor = conn.cursor()

    rows_added = 0
    rows_updated = 0

    for _, row in df.iterrows():
        cursor.execute("SELECT 1 FROM posts WHERE post_link = ?", (row['post_link'],))
        exists = cursor.fetchone() is not None

        # Convert NaN to None for optional fields
        def safe_get(val):
            if pd.isna(val):
                return None
            return val

        cursor.execute("""
            INSERT OR REPLACE INTO posts (
                post_link, activity_id, post_title, post_type, campaign_name,
                posted_by, created_date, campaign_start_date, campaign_end_date,
                audience, impressions, views, offsite_views, clicks, ctr,
                likes, comments, reposts, follows, engagement_rate, content_type,
                uploaded_at, source_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row['post_link'], safe_get(row.get('activity_id')), safe_get(row.get('post_title')),
            safe_get(row.get('post_type')), safe_get(row.get('campaign_name')), safe_get(row.get('posted_by')),
            row.get('created_date'), safe_get(row.get('campaign_start_date')), safe_get(row.get('campaign_end_date')),
            safe_get(row.get('audience')), safe_get(row.get('impressions')), safe_get(row.get('views')),
            safe_get(row.get('offsite_views')), safe_get(row.get('clicks')), safe_get(row.get('ctr')),
            safe_get(row.get('likes')), safe_get(row.get('comments')), safe_get(row.get('reposts')),
            safe_get(row.get('follows')), safe_get(row.get('engagement_rate')), safe_get(row.get('content_type')),
            uploaded_at, source_file
        ))

        if exists:
            rows_updated += 1
        else:
            rows_added += 1

    conn.commit()
    conn.close()
    return rows_added, rows_updated

def record_upload(filename: str, file_type: str, rows_added: int, rows_updated: int):
    """Record upload in history table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO uploads (filename, file_type, rows_added, rows_updated)
        VALUES (?, ?, ?, ?)
    """, (filename, file_type, rows_added, rows_updated))
    conn.commit()
    conn.close()

def process_upload(file, filename: str) -> dict:
    """Process uploaded file and return results."""
    df = parse_file(file, filename)
    file_type = detect_file_type(df)

    if file_type == 'daily':
        rows_added, rows_updated = ingest_daily_metrics(df, filename)
    else:
        rows_added, rows_updated = ingest_posts(df, filename)

    record_upload(filename, file_type, rows_added, rows_updated)

    return {
        'file_type': file_type,
        'rows_added': rows_added,
        'rows_updated': rows_updated,
        'total_rows': len(df)
    }
