import streamlit as st
import pandas as pd
from datetime import date, timedelta
from src.helpers.database import init_database
from src.helpers.ingestion import process_upload
from src.helpers.metrics import (
    get_date_range, get_daily_metrics, get_posts,
    calculate_kpis, get_this_week_dates, get_last_week_dates,
    get_mtd_dates, get_all_time_dates, calculate_delta
)
from src.helpers.utils import get_week_label
from src.helpers.charts import (
    create_time_series_chart, create_top_posts_by_impressions,
    create_top_posts_by_engagement, create_post_type_distribution,
    create_campaign_comparison
)
from src.helpers.reports import generate_weekly_report, export_to_excel, get_status_emoji
from src.helpers.qa import run_all_checks
from src.helpers.email_generator import build_weekly_email_payload, render_email

# Page config
st.set_page_config(
    page_title="LinkedIn Dashboard",
    page_icon="📊",
    layout="wide"
)

# Initialize database
init_database()

# Header
st.title("LinkedIn Analytics Dashboard")

# Get data range
min_date, max_date = get_date_range()
has_data = min_date is not None

# Sidebar filters
st.sidebar.header("Filters")

if has_data:
    # Date range filter
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    if len(date_range) == 2:
        filter_start, filter_end = date_range
    else:
        filter_start, filter_end = min_date, max_date

    # Post type filter
    post_type = st.sidebar.selectbox("Post Type", ["All", "Organic", "Sponsored"])

    # Content type filter
    content_type = st.sidebar.selectbox("Content Type", ["All", "Video", "Other"])

    # Data freshness indicator
    st.sidebar.divider()
    st.sidebar.caption(f"📅 Data as of: {max_date.strftime('%b %d, %Y')}")

    # Data Quality section
    st.sidebar.divider()
    st.sidebar.subheader("Data Quality")

    qa_results = run_all_checks(filter_start, filter_end)
    issues_found = False

    if qa_results['missing_dates']:
        issues_found = True
        st.sidebar.warning(f"⚠️ {len(qa_results['missing_dates'])} missing date(s)")
        with st.sidebar.expander("View missing dates"):
            for d in qa_results['missing_dates'][:10]:
                st.write(d)
            if len(qa_results['missing_dates']) > 10:
                st.write(f"... and {len(qa_results['missing_dates']) - 10} more")

    if qa_results['zero_metrics']:
        issues_found = True
        st.sidebar.warning(f"⚠️ {len(qa_results['zero_metrics'])} date(s) with zero impressions")

    if qa_results['outliers']:
        issues_found = True
        st.sidebar.info(f"📊 {len(qa_results['outliers'])} outlier date(s) detected")
        with st.sidebar.expander("View outliers"):
            for o in qa_results['outliers']:
                st.write(f"{o['date']}: {o['impressions']:,} ({o['deviation']})")

    if not issues_found:
        st.sidebar.success("✅ No data quality issues")

    # Definitions section
    st.sidebar.divider()
    with st.sidebar.expander("📖 Definitions"):
        st.markdown("""
**Impressions**: Times posts were displayed

**Unique Impressions**: Unique members who saw posts

**Clicks**: Link clicks on posts

**Reactions**: Likes/reactions on posts

**Comments**: Comments on posts

**Reposts**: Shares/reposts

**Engagement Rate**:
(Reactions + Comments + Reposts + Clicks) / Impressions

**CTR**: Clicks / Impressions

---

**Week Definition**: Last 7 days from latest data

**Timezone**: Pacific (America/Los_Angeles)

**Data Source**: LinkedIn UTC, delayed up to 2 days
        """)
else:
    st.sidebar.info("Upload data to enable filters.")
    filter_start, filter_end = None, None
    post_type, content_type = "All", "All"

# KPI Tiles
st.subheader("Key Metrics — Impressions")

if has_data:
    # Calculate KPIs for selected date range
    selected_days = (filter_end - filter_start).days + 1
    
    # Previous period of equal length for comparison
    prev_period_end = filter_start - timedelta(days=1)
    prev_period_start = prev_period_end - timedelta(days=selected_days - 1)
    
    # Get data for selected period and previous period
    selected_df = get_daily_metrics(filter_start, filter_end)
    prev_df = get_daily_metrics(prev_period_start, prev_period_end)
    
    # Also get fixed time windows for reference
    this_week_start, this_week_end = get_this_week_dates(max_date)
    last_week_start, last_week_end = get_last_week_dates(max_date)
    all_time_start, all_time_end = get_all_time_dates()
    
    this_week_df = get_daily_metrics(this_week_start, this_week_end)
    last_week_df = get_daily_metrics(last_week_start, last_week_end)
    all_time_df = get_daily_metrics(all_time_start, all_time_end)
    
    selected_kpis = calculate_kpis(selected_df)
    prev_kpis = calculate_kpis(prev_df)
    this_week_kpis = calculate_kpis(this_week_df)
    last_week_kpis = calculate_kpis(last_week_df)
    all_time_kpis = calculate_kpis(all_time_df)

    # Period-over-period delta
    _, period_delta_str = calculate_delta(
        selected_kpis['impressions'],
        prev_kpis['impressions']
    )

    # Show selected range label
    if filter_start == filter_end:
        range_label = filter_start.strftime('%b %d')
    else:
        range_label = f"{filter_start.strftime('%b %d')} - {filter_end.strftime('%b %d')}"
    
    prev_range_label = f"{prev_period_start.strftime('%b %d')} - {prev_period_end.strftime('%b %d')}"

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            f"📅 Selected ({range_label})",
            f"{selected_kpis['impressions']:,}",
            period_delta_str,
            help=f"Total impressions for selected period. Compared to previous {selected_days} days ({prev_range_label})"
        )

    with col2:
        st.metric(
            f"⏮️ Previous Period",
            f"{prev_kpis['impressions']:,}",
            None,
            help=f"Total impressions for {prev_range_label}"
        )

    with col3:
        _, wow_delta = calculate_delta(this_week_kpis['impressions'], last_week_kpis['impressions'])
        st.metric(
            f"📆 This Week ({get_week_label(this_week_start, this_week_end)})",
            f"{this_week_kpis['impressions']:,}",
            wow_delta,
            help="Total impressions for current Wed-Tue week vs last week"
        )

    with col4:
        st.metric(
            "📊 All-Time Total",
            f"{all_time_kpis['impressions']:,}",
            None,
            help="Total impressions across all uploaded data"
        )

    # Secondary KPIs row - Selected period with comparison deltas
    st.divider()
    st.caption(f"Selected Period ({range_label}) vs Previous {selected_days} Days ({prev_range_label})")
    col1, col2, col3, col4, col5 = st.columns(5)

    _, clicks_delta = calculate_delta(selected_kpis['clicks'], prev_kpis['clicks'])
    _, reactions_delta = calculate_delta(selected_kpis['reactions'], prev_kpis['reactions'])
    _, comments_delta = calculate_delta(selected_kpis['comments'], prev_kpis['comments'])
    _, reposts_delta = calculate_delta(selected_kpis['reposts'], prev_kpis['reposts'])
    _, engagement_delta = calculate_delta(selected_kpis['engagement_rate'], prev_kpis['engagement_rate'])

    with col1:
        st.metric("Clicks", f"{selected_kpis['clicks']:,}", clicks_delta)
    with col2:
        st.metric("Reactions", f"{selected_kpis['reactions']:,}", reactions_delta)
    with col3:
        st.metric("Comments", f"{selected_kpis['comments']:,}", comments_delta)
    with col4:
        st.metric("Reposts", f"{selected_kpis['reposts']:,}", reposts_delta)
    with col5:
        st.metric("Engagement Rate", f"{selected_kpis['engagement_rate']:.2%}", engagement_delta)

    # Previous period KPIs row for reference
    st.divider()
    st.caption(f"Previous Period ({prev_range_label}) - For Reference")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Clicks", f"{prev_kpis['clicks']:,}")
    with col2:
        st.metric("Reactions", f"{prev_kpis['reactions']:,}")
    with col3:
        st.metric("Comments", f"{prev_kpis['comments']:,}")
    with col4:
        st.metric("Reposts", f"{prev_kpis['reposts']:,}")
    with col5:
        st.metric("Engagement Rate", f"{prev_kpis['engagement_rate']:.2%}")

else:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Selected Period", "—", "—")
    with col2:
        st.metric("Previous Period", "—", None)
    with col3:
        st.metric("This Week", "—", None)
    with col4:
        st.metric("All-Time", "—", None)

st.divider()

# Charts
st.subheader("Charts")

if has_data:
    # Get filtered data
    filtered_daily = get_daily_metrics(filter_start, filter_end)
    filtered_posts = get_posts(filter_start, filter_end, post_type, content_type)

    # Time series chart (full width)
    st.plotly_chart(
        create_time_series_chart(filtered_daily),
        use_container_width=True,
        key="time_series_chart"
    )

    # Top posts charts (side by side)
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            create_top_posts_by_impressions(filtered_posts),
            use_container_width=True,
            key="top_posts_impressions_chart"
        )

    with col2:
        st.plotly_chart(
            create_top_posts_by_engagement(filtered_posts),
            use_container_width=True,
            key="top_posts_engagement_chart"
        )

    # Expandable post details
    if not filtered_posts.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            with st.expander("📋 View Top Posts by Impressions (Full Details)"):
                top_by_impressions = filtered_posts.nlargest(10, 'impressions')
                for idx, post in top_by_impressions.iterrows():
                    st.markdown(f"**#{top_by_impressions.index.get_loc(idx) + 1} — {post['impressions']:,} impressions**")
                    st.markdown(f"*Posted: {post['created_date']} | Engagement: {post['engagement_rate']:.2%}*")
                    st.write(post['post_title'] if pd.notna(post['post_title']) else "No title")
                    if pd.notna(post.get('post_link')) and post['post_link']:
                        st.markdown(f"[View on LinkedIn]({post['post_link']})")
                    st.divider()
        
        with col2:
            with st.expander("📋 View Top Posts by Engagement (Full Details)"):
                top_by_engagement = filtered_posts.nlargest(10, 'engagement_rate')
                for idx, post in top_by_engagement.iterrows():
                    st.markdown(f"**#{top_by_engagement.index.get_loc(idx) + 1} — {post['engagement_rate']:.2%} engagement**")
                    st.markdown(f"*Posted: {post['created_date']} | Impressions: {post['impressions']:,}*")
                    st.write(post['post_title'] if pd.notna(post['post_title']) else "No title")
                    if pd.notna(post.get('post_link')) and post['post_link']:
                        st.markdown(f"[View on LinkedIn]({post['post_link']})")
                    st.divider()

    # Distribution charts (side by side)
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            create_post_type_distribution(filtered_posts),
            use_container_width=True,
            key="post_type_distribution_chart"
        )

    with col2:
        st.plotly_chart(
            create_campaign_comparison(filtered_posts),
            use_container_width=True,
            key="campaign_comparison_chart"
        )
else:
    st.info("Upload data to view charts.")

st.divider()

# Weekly Report Generator
st.subheader("Weekly Report Generator")

if has_data:
    col1, col2 = st.columns([1, 2])

    with col1:
        if st.button("Generate Weekly Report", type="primary"):
            st.session_state['report'] = generate_weekly_report()

    if 'report' in st.session_state:
        report = st.session_state['report']

        with col2:
            # Status indicator
            status_emoji = get_status_emoji(report['overall_status'])
            st.markdown(f"### {status_emoji} Week of {report['week_label']}")

        # KPI snapshot
        st.markdown("#### KPI Snapshot")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Impressions",
                f"{report['this_week_kpis']['impressions']:,}",
                report['impressions_delta_str']
            )
        with col2:
            st.metric(
                "Engagement Rate",
                f"{report['this_week_kpis']['engagement_rate']:.2%}",
                report['engagement_delta_str']
            )
        with col3:
            st.metric("Clicks", f"{report['this_week_kpis']['clicks']:,}")
        with col4:
            st.metric("Reactions", f"{report['this_week_kpis']['reactions']:,}")

        # Top posts
        if not report['top_posts'].empty:
            st.markdown("#### Top 5 Posts by Impressions")
            for _, post in report['top_posts'].iterrows():
                title = str(post['post_title'])[:200] + "..." if len(str(post['post_title'])) > 200 else post['post_title']
                with st.expander(f"📈 {post['impressions']:,} impressions"):
                    st.write(title)
                    st.caption(f"Engagement: {post['engagement_rate']:.2%} | Posted: {post['created_date']}")

        # Underperformers
        if not report['underperformers'].empty:
            st.markdown("#### Underperforming Posts")
            for _, post in report['underperformers'].iterrows():
                title = str(post['post_title'])[:200] + "..." if len(str(post['post_title'])) > 200 else post['post_title']
                with st.expander(f"📉 {post['engagement_rate']:.2%} engagement"):
                    st.write(title)
                    st.caption(f"Impressions: {post['impressions']:,} | Posted: {post['created_date']}")

        # Planning templates
        st.markdown("#### Next Week Planning")
        st.text_area("Next week content plan:", placeholder="• Post 1: ...\n• Post 2: ...\n• Post 3: ...", height=100, key="next_week_plan")
        st.text_area("Risks & dependencies:", placeholder="• Risk 1: ...\n• Dependency: ...", height=100, key="risks")

        # Export button
        st.divider()
        excel_data = export_to_excel(report)
        st.download_button(
            label="📥 Download Excel Report",
            data=excel_data,
            file_name=f"LinkedIn_Weekly_Report_{report['week_label'].replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Upload data to generate weekly reports.")

# ── Email Generator (Internal Only) ──
# Gated: only visible when INTERNAL_MODE env var is set OR ?internal=true in URL
import os

_internal_env = os.environ.get("INTERNAL_MODE", "").lower() == "true"
_internal_param = st.query_params.get("internal", "").lower() == "true"
_is_internal = _internal_env or _internal_param

if _is_internal:
    st.divider()
    st.subheader("Email Draft Generator")
    st.caption("🔒 Internal only — this section is not visible to external viewers.")

    if has_data:
        col1, col2 = st.columns([1, 2])

        with col1:
            if st.button("📧 Generate Weekly Email", type="primary", key="gen_email_btn"):
                payload = build_weekly_email_payload(filter_start, filter_end)
                st.session_state['email_draft'] = render_email(payload)

        if 'email_draft' in st.session_state:
            email_text = st.session_state['email_draft']

            # Extract subject line for display
            subject_line = email_text.split("\n")[0] if email_text else ""
            with col2:
                st.markdown(f"**{subject_line}**")

            st.markdown("**Email Draft** — hover over the box and click the 📋 icon in the top-right to copy")
            st.code(email_text, language=None)

            st.download_button(
                label="📥 Download as .txt",
                data=email_text,
                file_name="LinkedIn_Email_Draft.txt",
                mime="text/plain",
                key="download_email_btn",
            )
    else:
        st.info("Upload data to generate email drafts.")

st.divider()

# File uploader
st.subheader("Data Upload")
uploaded_files = st.file_uploader(
    "Upload LinkedIn Export (.xlsx, .csv)",
    type=["xlsx", "xls", "csv"],
    accept_multiple_files=True
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        with st.spinner(f"Processing {uploaded_file.name}..."):
            try:
                result = process_upload(uploaded_file, uploaded_file.name)
                st.success(f"Processed {result['file_type']} data: {result['rows_added']} added, {result['rows_updated']} updated")
            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {str(e)}")
    st.rerun()
