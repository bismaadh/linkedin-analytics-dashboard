# LinkedIn Analytics Dashboard

A full-pipeline analytics dashboard for corporate LinkedIn performance — ingests raw exports, calculates KPIs, detects data quality issues, generates interactive visualizations, and drafts leadership-ready weekly email reports.

## Overview

Built for the marketing operations team at a healthcare client, this dashboard replaced a manual weekly reporting process that consumed 3+ hours of spreadsheet work. It ingests LinkedIn's native data exports, normalizes the data into a local SQLite database, and provides real-time KPI tracking, interactive charts, and one-click report generation.

## Problem

Corporate social media teams export LinkedIn analytics as spreadsheets, manually calculate week-over-week changes, build charts in Excel, and draft email summaries to leadership. This process is:

- **Slow** — 3+ hours per weekly report
- **Error-prone** — manual formulas break with format changes
- **Static** — no interactive exploration, no filtering by date range or content type
- **Inconsistent** — different people produce different formats

## Solution

An automated pipeline that handles the full reporting lifecycle:

1. **Ingest** — Upload LinkedIn `.xlsx` or `.csv` exports; the system auto-detects whether the file contains daily metrics or individual post data
2. **Normalize** — Column mapping handles LinkedIn's format variations; dates are standardized; engagement rates calculated uniformly
3. **Analyze** — KPIs computed across configurable time windows (selected period, week-over-week, month-to-date, all-time) with period-over-period deltas
4. **Visualize** — Interactive Plotly charts: time series, top posts, post type distribution, campaign comparison
5. **Quality Check** — Automated detection of missing dates, zero-impression days, and statistical outliers
6. **Report** — One-click weekly report generation with downloadable Excel export
7. **Email** — Auto-drafted leadership email with KPI highlights, top performers, and underperformers

## Features

- **Smart Data Ingestion** — Auto-detects daily metrics vs. post-level data from LinkedIn exports; handles multiple file formats and encodings
- **Configurable Time Windows** — Compare any date range against its previous period; built-in week-over-week, MTD, and all-time views
- **Data Quality Engine** — Flags missing dates, zero-metric anomalies, and statistical outliers in the sidebar
- **Interactive Plotly Charts** — Dual-axis time series (impressions + engagement rate), top posts by impressions and engagement, post type distribution, campaign comparison
- **Weekly Report Generator** — Structured report with KPI snapshot, top 5 posts, underperformers, and planning templates; downloadable as Excel
- **Email Draft Generator** — Produces a copy-paste-ready email for leadership with formatted KPIs, post highlights, and context (gated behind internal mode)
- **Filtering** — Date range, post type (organic/sponsored), content type (video/other)

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Streamlit UI                        │
│  ┌──────────┐ ┌────────────┐ ┌───────────────────┐  │
│  │ KPI Tiles│ │  Charts    │ │  Report Generator │  │
│  │ + Deltas │ │  (Plotly)  │ │  + Email Drafter  │  │
│  └────┬─────┘ └─────┬──────┘ └────────┬──────────┘  │
│       │             │                  │             │
└───────┼─────────────┼──────────────────┼─────────────┘
        │             │                  │
┌───────▼─────────────▼──────────────────▼─────────────┐
│                  Business Logic                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │ metrics  │ │  charts  │ │ reports  │ │  qa    │  │
│  │ engine   │ │  builder │ │ + email  │ │ checks │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘  │
│       │            │            │            │       │
└───────┼────────────┼────────────┼────────────┼───────┘
        │            │            │            │
┌───────▼────────────▼────────────▼────────────▼───────┐
│                Data Layer                             │
│  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  SQLite Database  │  │  Ingestion Pipeline      │  │
│  │  daily_metrics    │  │  parse → detect → norm   │  │
│  │  posts            │  │  → upsert → record       │  │
│  │  uploads          │  │                          │  │
│  └──────────────────┘  └──────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit (interactive dashboard) |
| Visualization | Plotly (interactive charts) |
| Data Processing | Pandas, openpyxl, xlrd |
| Database | SQLite (zero-config persistence) |
| Deployment | Railway, Azure App Service |
| Language | Python 3.11+ |

## Project Structure

```
linkedin-analytics-dashboard/
├── app.py                    # Main Streamlit application
├── src/
│   ├── __init__.py
│   └── helpers/
│       ├── database.py       # SQLite schema and connection management
│       ├── ingestion.py      # File parsing, column normalization, upsert logic
│       ├── metrics.py        # KPI calculations, time window functions
│       ├── charts.py         # Plotly chart builders
│       ├── reports.py        # Weekly report generation, Excel export
│       ├── email_generator.py # Leadership email drafting engine
│       ├── qa.py             # Data quality checks (gaps, outliers, zeros)
│       └── utils.py          # Date formatting, column normalization
├── data/                     # Local data directory (gitignored)
├── requirements.txt
├── Procfile                  # Railway/Heroku deployment
├── runtime.txt               # Python version pinning
└── README.md
```

## Example Use Case

A healthcare technology company's marketing team manages a corporate LinkedIn page with 3–5 posts per week across organic and sponsored content. Each Monday, the social media manager needs to:

1. Report last week's performance to the VP of Marketing
2. Identify which content themes drove the most engagement
3. Flag underperforming posts for strategy adjustment

**Before:** Export two spreadsheets from LinkedIn, copy numbers into an Excel template, build charts, calculate deltas, draft an email. Time: 3+ hours.

**With this dashboard:** Upload the exports, click "Generate Weekly Report," copy the auto-drafted email. Time: 5 minutes.

## Installation

### Prerequisites

- Python 3.11+

### Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501 to access the dashboard.

### Deployment (Railway)

```bash
railway login
railway init
railway up
```

## Data Format

The dashboard accepts LinkedIn's native export formats:

- **Daily Metrics** — CSV/Excel with columns: Date, Impressions (organic/sponsored/total), Clicks, Reactions, Comments, Reposts, Engagement Rate
- **Post-Level Data** — CSV/Excel with columns: Post title, Post link, Post type, Impressions, Clicks, Engagement rate, Content Type

LinkedIn exports include a description row that the ingestion pipeline automatically skips.

## Future Improvements

- Scheduled automated data ingestion via LinkedIn Marketing API
- Competitor benchmarking integration
- Content calendar planning view with predicted performance
- Slack/Teams webhook for automated weekly report delivery
- A/B test tracking for sponsored content variations
- Historical trend analysis with seasonal adjustment

## AI-Assisted Development

This project was built using AI-assisted development tools (Cursor) for code generation and iteration. The product requirements, dashboard design, KPI definitions, data quality rules, email formatting, and deployment strategy were all directed by the developer based on real stakeholder needs at a healthcare technology company.

## License

MIT
