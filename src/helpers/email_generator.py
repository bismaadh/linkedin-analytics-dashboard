"""
Email Generator for the LinkedIn Dashboard.
Builds a structured, leadership-ready email draft from dashboard data.
"""
from __future__ import annotations
import pandas as pd
from datetime import date, timedelta
from .metrics import (
    get_daily_metrics, get_posts, calculate_kpis,
    get_this_week_dates, get_last_week_dates, get_all_time_dates,
    calculate_delta, get_date_range
)
from .utils import get_week_label
from .qa import run_all_checks


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def fmt_int(n) -> str:
    """Format integer with comma separators."""
    return f"{int(n):,}"


def fmt_pct(p, decimals: int = 2) -> str:
    """Format a 0-1 ratio as a percent string (e.g. 6.47%)."""
    return f"{p * 100:.{decimals}f}%"


def fmt_delta(p, decimals: int = 1) -> str:
    """Format a percent-change value with +/- sign (e.g. +53.0%)."""
    if p > 0:
        return f"+{p:.{decimals}f}%"
    return f"{p:.{decimals}f}%"


def _short_date(d) -> str:
    """'Feb 3' style."""
    if isinstance(d, str):
        d = pd.to_datetime(d).date()
    return d.strftime("%b %-d")


def _post_title_short(row, max_len: int = 80) -> str:
    """Return a readable short title from the post_title field."""
    raw = str(row.get("post_title") or "Untitled")
    raw = raw.strip()
    if len(raw) > max_len:
        raw = raw[: max_len - 3] + "..."
    return raw


# ---------------------------------------------------------------------------
# Post-line formatters
# ---------------------------------------------------------------------------

def fmt_post_impressions(row) -> str:
    """Title (Mon D) -- # impressions | #.#% ER"""
    title = _post_title_short(row)
    d = _short_date(row["created_date"])
    return f"{title} ({d}) -- {fmt_int(row['impressions'])} impressions | {fmt_pct(row['engagement_rate'])} ER"


def fmt_post_er(row) -> str:
    """Title (Mon D) -- #.#% ER | # impressions"""
    title = _post_title_short(row)
    d = _short_date(row["created_date"])
    return f"{title} ({d}) -- {fmt_pct(row['engagement_rate'])} ER | {fmt_int(row['impressions'])} impressions"


# ---------------------------------------------------------------------------
# Insight-bullet builder
# ---------------------------------------------------------------------------

def build_insights_bullets(
    kpis_current: dict,
    kpis_prior: dict,
    deltas: dict,
    top_posts: pd.DataFrame,
    underperformers: pd.DataFrame,
    format_mix: dict,
) -> list[str]:
    """
    Return 5-7 concrete, metric-backed insight bullets.
    Every bullet references a real number or delta.
    """
    bullets: list[str] = []

    imp_d = deltas["impressions"]
    er_d = deltas["engagement_rate"]
    click_d = deltas["clicks"]
    react_d = deltas["reactions"]
    repost_d = deltas["reposts"]

    # 1. Headline reach + engagement direction
    if imp_d > 0 and er_d > 0:
        bullets.append(
            f"Impressions and engagement rate both rose week-over-week "
            f"({fmt_delta(imp_d)} and {fmt_delta(er_d)}, respectively) -- "
            f"reach is growing and content quality is resonating."
        )
    elif imp_d > 0 and er_d < 0:
        bullets.append(
            f"Impressions climbed {fmt_delta(imp_d)} but engagement rate "
            f"declined {fmt_delta(er_d)} -- content is reaching more people "
            f"but may need stronger hooks or CTAs to convert views into interactions."
        )
    elif imp_d < 0 and er_d > 0:
        bullets.append(
            f"Impressions dipped {fmt_delta(imp_d)} while engagement rate "
            f"improved {fmt_delta(er_d)} -- smaller audience but higher-quality "
            f"interactions."
        )
    elif imp_d < 0 and er_d < 0:
        bullets.append(
            f"Both impressions ({fmt_delta(imp_d)}) and engagement rate "
            f"({fmt_delta(er_d)}) declined -- consider refreshing content "
            f"themes or posting cadence."
        )

    # 2. Clicks delta (call out if largest positive mover)
    positive_deltas = {
        "Clicks": click_d,
        "Impressions": imp_d,
        "Reactions": react_d,
        "Reposts": repost_d,
    }
    largest_pos = max(positive_deltas, key=positive_deltas.get)
    if click_d > 0:
        bullets.append(
            f"Clicks surged {fmt_delta(click_d)} "
            f"({fmt_int(kpis_current['clicks'])} vs. {fmt_int(kpis_prior['clicks'])})"
            f"{', the largest positive delta this week' if largest_pos == 'Clicks' else ''}"
            f", suggesting our CTAs are landing."
        )

    # 3. Reactions decline with ER rise --> composition shift
    if react_d < 0 and er_d > 0:
        bullets.append(
            f"Reactions dipped {fmt_delta(react_d)} "
            f"({fmt_int(kpis_current['reactions'])} vs. {fmt_int(kpis_prior['reactions'])}) "
            f"despite a higher overall engagement rate, likely due to the interaction mix "
            f"shifting toward clicks and reposts."
        )

    # 4. Reposts callout if notable
    if repost_d > 50:
        bullets.append(
            f"Reposts jumped {fmt_delta(repost_d)} "
            f"({fmt_int(kpis_current['reposts'])} vs. {fmt_int(kpis_prior['reposts'])}) "
            f"-- content is being amplified beyond our immediate followers."
        )

    # 5. Best content type
    if not top_posts.empty:
        top_row = top_posts.iloc[0]
        ptype = str(top_row.get("post_type", "")).lower()
        ctype = str(top_row.get("content_type", "")).lower()
        best_label = _infer_content_label(ptype, ctype)
        bullets.append(
            f"The highest-engagement post was {best_label} content "
            f"({fmt_pct(top_row['engagement_rate'])} ER), reinforcing that "
            f"authentic, people-centered posts consistently outperform on LinkedIn."
        )

    # 6. Underperformer pattern
    if not underperformers.empty:
        worst = underperformers.iloc[0]
        w_label = _infer_content_label(
            str(worst.get("post_type", "")).lower(),
            str(worst.get("content_type", "")).lower(),
        )
        if worst["impressions"] == kpis_current["impressions"] or (
            not top_posts.empty
            and worst["impressions"]
            >= top_posts.nlargest(1, "impressions").iloc[0]["impressions"]
        ):
            bullets.append(
                f"The highest-reach post had the lowest ER ({fmt_pct(worst['engagement_rate'])}) -- "
                f"high impressions did not translate to interactions. "
                f"Consider a tighter hook or clearer CTA on {w_label} posts."
            )
        else:
            bullets.append(
                f"{w_label.capitalize()} content recorded the lowest ER "
                f"({fmt_pct(worst['engagement_rate'])}). Testing a different "
                f"caption format or visual treatment may lift engagement."
            )

    # 7. Video format context
    total_posts = sum(format_mix.values()) if format_mix else 0
    video_count = sum(v for k, v in format_mix.items() if "video" in k.lower())
    if total_posts > 0 and video_count > 0:
        video_pct = video_count / total_posts * 100
        bullets.append(
            f"Video content made up {video_pct:.0f}% of posts but drove outsized "
            f"engagement -- worth continuing to invest in native video."
        )

    return bullets[:7]


def _infer_content_label(ptype: str, ctype: str) -> str:
    """Best-effort human-readable content category."""
    if "video" in ctype:
        return "video"
    if "event" in ptype or "culture" in ptype:
        return "culture/event"
    if "research" in ptype or "clinical" in ptype:
        return "research/clinical"
    if "promo" in ptype or "product" in ptype:
        return "promo/product"
    return "organic"


# ---------------------------------------------------------------------------
# Payload builder
# ---------------------------------------------------------------------------

def build_weekly_email_payload(
    filter_start: date,
    filter_end: date,
) -> dict:
    """
    Pull all data needed for the email from the database.
    Returns a flat dict (the 'payload') with every field the template needs.
    """
    selected_days = (filter_end - filter_start).days + 1
    prev_period_end = filter_start - timedelta(days=1)
    prev_period_start = prev_period_end - timedelta(days=selected_days - 1)

    min_date, max_date = get_date_range()
    this_week_start, this_week_end = get_this_week_dates(max_date)
    last_week_start, last_week_end = get_last_week_dates(max_date)
    all_time_start, all_time_end = get_all_time_dates()

    # DataFrames
    tw_df = get_daily_metrics(this_week_start, this_week_end)
    lw_df = get_daily_metrics(last_week_start, last_week_end)
    at_df = get_daily_metrics(all_time_start, all_time_end)
    tw_posts = get_posts(this_week_start, this_week_end)

    # KPIs
    tw_kpis = calculate_kpis(tw_df)
    lw_kpis = calculate_kpis(lw_df)
    at_kpis = calculate_kpis(at_df)

    # Deltas (raw numeric values)
    deltas_raw: dict[str, float] = {}
    deltas_str: dict[str, str] = {}
    for key in ("impressions", "clicks", "reactions", "comments", "reposts", "engagement_rate"):
        val, s = calculate_delta(tw_kpis[key], lw_kpis[key])
        deltas_raw[key] = val
        deltas_str[key] = s

    # Top / bottom posts (current week)
    if not tw_posts.empty:
        top_by_impressions = tw_posts.nlargest(5, "impressions")
        top_by_engagement = tw_posts.nlargest(5, "engagement_rate")
        if len(tw_posts) > 1:
            median_er = tw_posts["engagement_rate"].median()
            underperformers = tw_posts[
                tw_posts["engagement_rate"] < median_er
            ].nsmallest(3, "engagement_rate")
        else:
            underperformers = pd.DataFrame()
    else:
        top_by_impressions = pd.DataFrame()
        top_by_engagement = pd.DataFrame()
        underperformers = pd.DataFrame()

    # Format mix
    format_mix: dict[str, int] = {}
    if not tw_posts.empty:
        for _, p in tw_posts.iterrows():
            ptype = str(p.get("post_type", "Unknown") or "Unknown")
            ctype = str(p.get("content_type", "") or "")
            if "video" in ctype.lower():
                label = "Organic video"
            else:
                label = "Organic (static/image)"
            format_mix[label] = format_mix.get(label, 0) + 1

    # Data quality notes
    data_notes: list[str] = []
    if lw_kpis["impressions"] == 0:
        data_notes.append(
            f"No data exists for the prior week "
            f"({last_week_start.strftime('%b %-d')} - {last_week_end.strftime('%b %-d')}). "
            f"Week-over-week % changes should be interpreted with caution."
        )
    qa = run_all_checks(this_week_start, this_week_end)
    if qa["missing_dates"]:
        data_notes.append(
            f"{len(qa['missing_dates'])} date(s) missing in the current week range."
        )
    if qa["zero_metrics"]:
        data_notes.append(
            f"{len(qa['zero_metrics'])} date(s) recorded zero impressions (possible data delay)."
        )

    # Insights
    insights = build_insights_bullets(
        tw_kpis, lw_kpis, deltas_raw,
        top_by_engagement, underperformers, format_mix,
    )

    return {
        "current_period_label": f"{_short_date(this_week_start)}-{_short_date(this_week_end)}",
        "prior_period_label": f"{_short_date(last_week_start)}-{_short_date(last_week_end)}",
        "current_period_year": this_week_end.year,
        "this_week_start": this_week_start,
        "this_week_end": this_week_end,
        "all_time_impressions": at_kpis["impressions"],
        "kpis_current": tw_kpis,
        "kpis_prior": lw_kpis,
        "deltas_raw": deltas_raw,
        "deltas_str": deltas_str,
        "top_by_impressions": top_by_impressions,
        "top_by_engagement": top_by_engagement,
        "underperformers": underperformers,
        "format_mix": format_mix,
        "insights": insights,
        "data_notes": data_notes,
    }


# ---------------------------------------------------------------------------
# Email renderer
# ---------------------------------------------------------------------------

def render_email(payload: dict) -> str:
    """
    Render a deterministic, leadership-ready plain-text email
    from the payload dict.  Output is copy/paste ready.
    """
    lines: list[str] = []
    cur = payload["current_period_label"]
    prior = payload["prior_period_label"]
    year = payload["current_period_year"]
    kc = payload["kpis_current"]
    kp = payload["kpis_prior"]
    ds = payload["deltas_str"]
    dr = payload["deltas_raw"]

    # --- Subject ---
    lines.append(f"Subject: LinkedIn Weekly Report -- {cur}, {year}")
    lines.append("")

    # --- 1. Opening paragraph ---
    lines.append("Hi team,")
    lines.append("")

    # Directional takeaway sentence
    imp_dir = "up" if dr["impressions"] >= 0 else "down"
    er_dir = "up" if dr["engagement_rate"] >= 0 else "down"
    lines.append(
        f"Below is this week's LinkedIn performance summary for the "
        f"company page ({cur}). "
        f"Reach was {imp_dir} ({ds['impressions']}) and engagement efficiency "
        f"was {er_dir} ({ds['engagement_rate']}) versus the prior week ({prior}). "
        f"All-time impressions to date: {fmt_int(payload['all_time_impressions'])}."
    )
    lines.append("")

    # --- 2. Top 5 posts by impressions ---
    lines.append(f"Top 5 posts by impressions (in the last 7 days):")
    lines.append("")
    if not payload["top_by_impressions"].empty:
        for i, (_, row) in enumerate(payload["top_by_impressions"].iterrows(), 1):
            lines.append(f"{i}. {fmt_post_impressions(row)}")
            desc = _build_post_descriptor(row)
            lines.append(f"   {desc}")
            lines.append("")
    else:
        lines.append("No posts in this period.")
        lines.append("")

    # --- 3. Top 5 posts by engagement rate ---
    lines.append(f"Top 5 posts by engagement rate (in the last 7 days):")
    lines.append("")
    if not payload["top_by_engagement"].empty:
        for i, (_, row) in enumerate(payload["top_by_engagement"].iterrows(), 1):
            lines.append(f"{i}. {fmt_post_er(row)}")
    else:
        lines.append("No posts in this period.")
    lines.append("")

    # --- 4. Underperforming posts ---
    lines.append("Underperforming posts (lowest engagement):")
    lines.append("")
    if not payload["underperformers"].empty:
        imp_top = payload["top_by_impressions"]
        highest_imp = (
            imp_top.iloc[0]["impressions"] if not imp_top.empty else 0
        )
        for i, (_, row) in enumerate(payload["underperformers"].iterrows(), 1):
            title = _post_title_short(row)
            d = _short_date(row["created_date"])
            lines.append(f"{i}. {title} ({d}) -- {fmt_pct(row['engagement_rate'])} ER")
            reason = _build_underperformer_note(row, highest_imp)
            lines.append(f"   {reason}")
            lines.append("")
    else:
        lines.append("No underperformers identified (insufficient post volume).")
        lines.append("")

    # --- 5. Format mix ---
    lines.append("Format mix:")
    lines.append("")
    if payload["format_mix"]:
        total = sum(payload["format_mix"].values())
        for label in ("Organic (static/image)", "Organic video"):
            count = payload["format_mix"].get(label, 0)
            if count > 0:
                pct = count / total * 100
                lines.append(f"  {label}: {pct:.0f}%")
        for label, count in sorted(
            payload["format_mix"].items(), key=lambda x: -x[1]
        ):
            if label not in ("Organic (static/image)", "Organic video"):
                pct = count / total * 100
                lines.append(f"  {label}: {pct:.0f}%")
    else:
        lines.append("  No post data available.")
    lines.append("")

    # --- 6. What this tells us ---
    lines.append("What this tells us:")
    lines.append("")
    for bullet in payload["insights"]:
        lines.append(f"- {bullet}")
    lines.append("")

    # --- 7. Data notes (only if present) ---
    if payload["data_notes"]:
        lines.append("Data notes:")
        lines.append("")
        for note in payload["data_notes"]:
            lines.append(f"- {note}")
        lines.append("")

    # --- 8. Next week focus ---
    lines.append("Next week focus:")
    lines.append("")
    next_focus = _build_next_week_focus(payload)
    for bullet in next_focus:
        lines.append(f"- {bullet}")
    lines.append("")

    # --- Sign-off ---
    lines.append(
        "Happy to adjust the format or add any KPIs. Let me know."
    )
    lines.append("")
    lines.append("Best,")
    lines.append("Bismaad")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers for render
# ---------------------------------------------------------------------------

def _build_post_descriptor(row) -> str:
    """One-sentence descriptor (~12-18 words) for a post, inferred from title.

    Note: production deployments customize the keyword maps below to the
    specific brand voice, product lines, and event calendar of the company.
    The mapping shown here is illustrative.
    """
    title = str(row.get("post_title") or "").lower()
    ctype = str(row.get("content_type", "")).lower()

    if "video" in ctype:
        fmt_hint = "Video"
    else:
        fmt_hint = "Post"

    if any(kw in title for kw in ("study", "research", "data", "results")):
        return f"{fmt_hint} featuring research findings or product data."
    if any(kw in title for kw in ("testimonial", "shares how", "story")):
        return f"{fmt_hint} highlighting a customer's real-world experience."
    if any(kw in title for kw in ("launch", "introducing", "new", "available")):
        return f"{fmt_hint} announcing a product launch or feature update."
    if any(kw in title for kw in ("event", "summit", "conference", "expo")):
        return f"{fmt_hint} recapping takeaways from an industry event."
    if any(kw in title for kw in ("award", "recognition", "milestone")):
        return f"{fmt_hint} spotlighting a company milestone or industry recognition."
    if any(kw in title for kw in ("team", "culture", "employee", "welcome", "celebrate")):
        return f"{fmt_hint} highlighting team culture and internal community moments."

    return f"{fmt_hint} covering a corporate initiative relevant to the target audience."


def _build_underperformer_note(row, highest_imp: int) -> str:
    """1-2 sentence constructive note on why a post may have underperformed."""
    er = row["engagement_rate"]
    imp = row["impressions"]
    title_lower = str(row.get("post_title", "")).lower()

    if imp >= highest_imp:
        return (
            f"Highest reach of the week ({fmt_int(imp)} impressions) but "
            f"lowest engagement. Research- or product-heavy content may need "
            f"a stronger opening hook or a clear CTA to convert views into interactions."
        )

    if any(kw in title_lower for kw in ("study", "research", "translational", "speckle")):
        return (
            f"Research content drove solid impressions ({fmt_int(imp)}) but ER "
            f"fell below the weekly median. Consider leading with a patient-impact "
            f"angle or a concise takeaway to lift engagement."
        )

    if any(kw in title_lower for kw in ("see the data", "inspire", "radius", "promo", "offer")):
        return (
            f"Promotional content ({fmt_int(imp)} impressions) with below-average ER. "
            f"Promo posts typically see lower engagement; pairing with a clinician "
            f"quote or patient outcome may help."
        )

    return (
        f"Below-average ER on {fmt_int(imp)} impressions. "
        f"Testing a different visual treatment or caption structure may improve performance."
    )


def _build_next_week_focus(payload: dict) -> list[str]:
    """3-5 actionable bullets derived from this week's insights."""
    bullets: list[str] = []
    dr = payload["deltas_raw"]
    kc = payload["kpis_current"]
    fm = payload["format_mix"]

    # Continue what worked
    if not payload["top_by_engagement"].empty:
        best = payload["top_by_engagement"].iloc[0]
        ctype = str(best.get("content_type", "")).lower()
        if "video" in ctype:
            bullets.append(
                "Continue the video testimonial series -- it drove the strongest "
                "engagement this week."
            )
        else:
            label = _infer_content_label(
                str(best.get("post_type", "")).lower(), ctype
            )
            bullets.append(
                f"Replicate the {label} format that drove the highest ER this week."
            )

    # Fix what didn't
    if not payload["underperformers"].empty:
        worst_title = str(
            payload["underperformers"].iloc[0].get("post_title", "")
        ).lower()
        if any(kw in worst_title for kw in ("study", "research", "translational")):
            bullets.append(
                "Test a shorter, punchier caption on the next research/clinical "
                "post to lift ER."
            )
        else:
            bullets.append(
                "Revisit caption structure on underperforming posts -- tighter hooks "
                "and clearer CTAs."
            )

    # Clicks / promo follow-up
    if dr.get("clicks", 0) > 20:
        bullets.append(
            "Monitor whether promo and CTA-driven posts continue to generate "
            "click-throughs into next week."
        )

    # Video investment
    video_count = fm.get("Organic video", 0)
    total = sum(fm.values()) if fm else 0
    if total > 0 and video_count / total < 0.5:
        bullets.append(
            "Consider increasing the video share above 50% -- native video "
            "consistently outperforms static posts on LinkedIn."
        )

    # Culture / event
    if any("event" in k.lower() or "culture" in k.lower() for k in fm):
        bullets.append(
            "Look for upcoming team or event moments to replicate the strong "
            "engagement from culture/event posts."
        )

    if not bullets:
        bullets.append("Maintain current posting cadence and content mix.")

    return bullets[:5]
