import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from plotly.subplots import make_subplots

def create_time_series_chart(df: pd.DataFrame) -> go.Figure:
    """Create dual-axis time series: Impressions + Engagement Rate."""
    if df.empty:
        return go.Figure().add_annotation(text="No data available", showarrow=False)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Impressions on primary y-axis
    fig.add_trace(
        go.Scatter(
            x=df['date'],
            y=df['impressions_total'],
            name="Impressions",
            line=dict(color='#1f77b4', width=2),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.1)'
        ),
        secondary_y=False
    )

    # Engagement rate on secondary y-axis
    fig.add_trace(
        go.Scatter(
            x=df['date'],
            y=df['engagement_rate_total'],
            name="Engagement Rate",
            line=dict(color='#ff7f0e', width=2, dash='dot')
        ),
        secondary_y=True
    )

    fig.update_layout(
        title="Impressions & Engagement Rate Over Time",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Impressions", secondary_y=False)
    fig.update_yaxes(title_text="Engagement Rate", tickformat=".2%", secondary_y=True)

    return fig

def create_top_posts_by_impressions(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """Create horizontal bar chart of top posts by impressions."""
    if df.empty:
        return go.Figure().add_annotation(text="No data available", showarrow=False)

    top_df = df.nlargest(top_n, 'impressions').sort_values('impressions')

    # Truncate titles for display
    top_df = top_df.copy()
    top_df['display_title'] = top_df['post_title'].apply(
        lambda x: (str(x)[:50] + '...') if pd.notna(x) and len(str(x)) > 50 else str(x)
    )

    fig = go.Figure(go.Bar(
        x=top_df['impressions'],
        y=top_df['display_title'],
        orientation='h',
        marker_color='#1f77b4',
        text=top_df['impressions'].apply(lambda x: f"{x:,}"),
        textposition='outside'
    ))

    fig.update_layout(
        title=f"Top {min(top_n, len(top_df))} Posts by Impressions",
        xaxis_title="Impressions",
        yaxis_title="",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig

def create_top_posts_by_engagement(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """Create horizontal bar chart of top posts by engagement rate."""
    if df.empty:
        return go.Figure().add_annotation(text="No data available", showarrow=False)

    top_df = df.nlargest(top_n, 'engagement_rate').sort_values('engagement_rate')

    # Truncate titles for display
    top_df = top_df.copy()
    top_df['display_title'] = top_df['post_title'].apply(
        lambda x: (str(x)[:50] + '...') if pd.notna(x) and len(str(x)) > 50 else str(x)
    )

    fig = go.Figure(go.Bar(
        x=top_df['engagement_rate'],
        y=top_df['display_title'],
        orientation='h',
        marker_color='#ff7f0e',
        text=top_df['engagement_rate'].apply(lambda x: f"{x:.2%}"),
        textposition='outside'
    ))

    fig.update_layout(
        title=f"Top {min(top_n, len(top_df))} Posts by Engagement Rate",
        xaxis_title="Engagement Rate",
        yaxis_title="",
        xaxis_tickformat=".1%",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig

def create_post_type_distribution(df: pd.DataFrame) -> go.Figure:
    """Create pie chart of post type distribution."""
    if df.empty:
        return go.Figure().add_annotation(text="No data available", showarrow=False)

    # Combine post_type and content_type for richer breakdown
    df = df.copy()
    df['type_label'] = df.apply(
        lambda row: f"{row['post_type']} - {row['content_type']}"
        if pd.notna(row['content_type']) and row['content_type']
        else row['post_type'],
        axis=1
    )

    type_counts = df['type_label'].value_counts()

    fig = go.Figure(go.Pie(
        labels=type_counts.index,
        values=type_counts.values,
        hole=0.4,
        marker_colors=px.colors.qualitative.Set2
    ))

    fig.update_layout(
        title="Post Type Distribution",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2)
    )

    return fig

def create_campaign_comparison(df: pd.DataFrame) -> go.Figure:
    """Create campaign comparison chart (or placeholder if no campaign data)."""
    if df.empty:
        return go.Figure().add_annotation(text="No data available", showarrow=False)

    # Check if campaign_name has any non-empty values
    campaigns = df[df['campaign_name'].notna() & (df['campaign_name'] != '')]

    if campaigns.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No campaign data available.<br>Campaign tags will appear here when used.",
            showarrow=False,
            font=dict(size=14, color="gray")
        )
        fig.update_layout(
            title="Campaign Comparison",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
        return fig

    # Group by campaign
    campaign_stats = campaigns.groupby('campaign_name').agg({
        'impressions': 'sum',
        'engagement_rate': 'mean',
        'post_link': 'count'
    }).rename(columns={'post_link': 'post_count'}).reset_index()

    fig = go.Figure(go.Bar(
        x=campaign_stats['campaign_name'],
        y=campaign_stats['impressions'],
        text=campaign_stats['impressions'].apply(lambda x: f"{x:,}"),
        textposition='outside',
        marker_color='#2ca02c'
    ))

    fig.update_layout(
        title="Campaign Comparison (Impressions)",
        xaxis_title="Campaign",
        yaxis_title="Total Impressions"
    )

    return fig
