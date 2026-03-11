"""
DashEngine – app.py
Entry point.  Run with:  streamlit run DashEngine/app.py

Architecture
────────────
app.py              ← layout, routing, CSS, sidebar
config.py           ← colors, Plotly base template
data_processing.py  ← engine logic, caching, metrics, filtering
components/
  kpis.py           ← KPI card row
  charts.py         ← Plotly figure builders (pure functions)
  tables.py         ← Review queue + decisions log tables
"""

from __future__ import annotations

import os
import sys

# Ensure sibling modules (config, data_processing, components) resolve correctly
# regardless of the CWD from which Streamlit is invoked.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import pandas as pd
import streamlit as st
from datetime import datetime

from config import (
    ACCENT, BG_CARD, BG_PRIMARY, BORDER, BORDER_LIGHT,
    DECISION_COLORS, TXT_MUTED, TXT_PRIMARY, TXT_SECONDARY,
)
from data_processing import (apply_filters, compute_metrics, load_and_process,
                             BUFFER_USD, RECENT_DEST_DAYS, DUP_WINDOW_MIN)
from components.charts import (
    amount_distribution_chart,
    decision_donut,
    reason_breakdown_chart,
    speed_breakdown_chart,
    timeline_chart,
    volume_by_decision_chart,
)
from components.kpis import render_kpi_row
from components.tables import render_decisions_table, render_review_queue


# ── Page config (must be first Streamlit call) ────────────────────────────────

st.set_page_config(
    page_title        = "DashEngine · Withdrawal Ops",
    page_icon         = "⚡",
    layout            = "wide",
    initial_sidebar_state = "expanded",
)


# ── Custom CSS ────────────────────────────────────────────────────────────────

def _inject_css() -> None:
    st.markdown(f"""
    <style>
        /* ── Google Font ── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* ── Root ── */
        html, body,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {{
            background-color : {BG_PRIMARY} !important;
            font-family      : 'Inter', system-ui, -apple-system, sans-serif !important;
        }}
        .main .block-container {{
            padding-top    : 1.25rem;
            padding-bottom : 2rem;
            max-width      : 1380px;
        }}

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {{
            background-color : #0d1424 !important;
            border-right     : 1px solid {BORDER} !important;
        }}
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span {{
            color : {TXT_SECONDARY} !important;
        }}

        /* ── Headings ── */
        h1, h2, h3, h4 {{
            color       : {TXT_PRIMARY} !important;
            font-family : 'Inter', system-ui, sans-serif !important;
        }}

        /* ── Section label helper class ── */
        .section-label {{
            font-size      : 10px;
            font-weight    : 700;
            letter-spacing : 0.12em;
            text-transform : uppercase;
            color          : {TXT_MUTED};
            margin-bottom  : 10px;
        }}

        /* ── Tabs ── */
        .stTabs [data-baseweb="tab-list"] {{
            background    : {BG_CARD} !important;
            border-radius : 8px 8px 0 0 !important;
            border-bottom : 1px solid {BORDER} !important;
            padding       : 4px 12px 0 !important;
            gap           : 4px !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            background    : transparent !important;
            color         : {TXT_SECONDARY} !important;
            border-radius : 6px 6px 0 0 !important;
            padding       : 8px 18px !important;
            font-size     : 13px !important;
            font-weight   : 500 !important;
            border-bottom : 2px solid transparent !important;
        }}
        .stTabs [aria-selected="true"] {{
            color         : {TXT_PRIMARY} !important;
            border-bottom : 2px solid {ACCENT} !important;
        }}
        .stTabs [data-baseweb="tab-panel"] {{
            background    : {BG_CARD} !important;
            border        : 1px solid {BORDER} !important;
            border-top    : none !important;
            border-radius : 0 0 8px 8px !important;
            padding       : 20px !important;
        }}

        /* ── Dataframe table ── */
        [data-testid="stDataFrame"] > div {{
            border        : 1px solid {BORDER} !important;
            border-radius : 8px !important;
        }}

        /* ── Download button ── */
        .stDownloadButton > button {{
            background   : transparent !important;
            border       : 1px solid {BORDER} !important;
            color        : {TXT_SECONDARY} !important;
            font-size    : 12px !important;
            padding      : 5px 14px !important;
            border-radius: 6px !important;
            margin-top   : 10px !important;
        }}
        .stDownloadButton > button:hover {{
            border-color : {ACCENT} !important;
            color        : {TXT_PRIMARY} !important;
        }}

        /* ── File uploader ── */
        [data-testid="stFileUploader"] {{
            border        : 2px dashed {BORDER} !important;
            border-radius : 10px !important;
            background    : {BG_CARD} !important;
        }}

        /* ── Plotly chart borders ── */
        .js-plotly-plot {{
            border        : 1px solid {BORDER};
            border-radius : 8px;
        }}

        /* ── Streamlit info / warning boxes ── */
        .stAlert {{ border-radius: 8px !important; }}

        /* ── Horizontal rule ── */
        hr {{ border-color: {BORDER} !important; margin: 1.25rem 0 !important; }}

        /* ── Hide Streamlit branding (keep header so sidebar toggle stays visible) ── */
        #MainMenu                              {{ visibility: hidden !important; }}
        footer                                 {{ visibility: hidden !important; }}
        [data-testid="stDeployButton"]         {{ display: none !important; }}
        [data-testid="stDecoration"]           {{ display: none !important; }}
        [data-testid="stStatusWidget"]         {{ display: none !important; }}
    </style>
    """, unsafe_allow_html=True)


# ── Upload / landing screen ───────────────────────────────────────────────────

def _render_landing() -> None:
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(f"""
        <div style="
            text-align    : center;
            padding       : 56px 40px;
            background    : {BG_CARD};
            border        : 1px dashed {BORDER};
            border-radius : 16px;
        ">
            <div style="font-size:52px; margin-bottom:20px;">⚡</div>
            <div style="
                color          : {TXT_PRIMARY};
                font-size      : 26px;
                font-weight    : 700;
                letter-spacing : -0.03em;
                margin-bottom  : 10px;
            ">DashEngine</div>
            <div style="
                color       : {TXT_SECONDARY};
                font-size   : 14px;
                line-height : 1.7;
                max-width   : 380px;
                margin      : 0 auto 28px;
            ">
                Upload your
                <code style="
                    background : rgba(99,102,241,.15);
                    color      : {ACCENT};
                    padding    : 2px 7px;
                    border-radius : 4px;
                ">withdrawals.xlsx</code>
                file in the sidebar to start monitoring withdrawal decisions.
            </div>
            <div style="
                color       : {TXT_MUTED};
                font-size   : 12px;
                line-height : 2.2;
            ">
                Required sheets:<br>
                <b style="color:{TXT_SECONDARY}">withdrawal_requests</b> &nbsp;·&nbsp;
                <b style="color:{TXT_SECONDARY}">account_snapshot</b> &nbsp;·&nbsp;
                <b style="color:{TXT_SECONDARY}">destination_registry</b>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ── Page header ───────────────────────────────────────────────────────────────

def _render_header(data: dict | None = None) -> None:
    col_brand, col_meta = st.columns([3, 2])

    with col_brand:
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:14px; margin-bottom:2px;">
            <div style="
                background    : linear-gradient(135deg, {ACCENT} 0%, #4338ca 100%);
                border-radius : 10px;
                width:42px; height:42px;
                display:flex; align-items:center; justify-content:center;
                font-size:20px; flex-shrink:0;
            ">⚡</div>
            <div>
                <div style="
                    color          : {TXT_PRIMARY};
                    font-size      : 22px;
                    font-weight    : 700;
                    letter-spacing : -0.03em;
                    line-height    : 1.1;
                ">DashEngine</div>
                <div style="color:{TXT_SECONDARY}; font-size:12px; margin-top:2px;">
                    Withdrawal Decision Operations
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_meta:
        if data:
            total = len(data["decisions"])
            ts    = datetime.now().strftime("%b %d, %Y  %H:%M")
            dups  = data["duplicate_count"]
            st.markdown(f"""
            <div style="text-align:right; padding-top:8px;">
                <span style="
                    background   : rgba(16,185,129,.10);
                    color        : #10b981;
                    border       : 1px solid rgba(16,185,129,.30);
                    border-radius: 20px;
                    padding      : 3px 12px;
                    font-size    : 12px;
                    font-weight  : 600;
                ">● LIVE</span>
                <div style="
                    color     : {TXT_MUTED};
                    font-size : 11px;
                    margin-top: 5px;
                ">{total:,} requests &nbsp;·&nbsp; {dups} duplicate(s) flagged &nbsp;·&nbsp; {ts}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(f'<hr style="border-color:{BORDER}; margin:14px 0 20px;">', unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────

def _render_upload_section() -> object | None:
    st.markdown(f"""
    <div style="padding:6px 0 14px;">
        <div style="color:{TXT_PRIMARY}; font-size:15px; font-weight:700;">Controls</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="section-label">Data Source</div>', unsafe_allow_html=True)
    return st.file_uploader(
        "Upload withdrawals.xlsx",
        type      = ["xlsx"],
        help      = "Must contain sheets: withdrawal_requests, account_snapshot, destination_registry",
        label_visibility = "collapsed",
    )


def _render_filter_section(data: dict) -> dict:
    """Renders filter controls; returns a filters dict."""
    filters: dict = {}
    df = data["enriched"]

    st.markdown("---")

    # ── Date range ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Date Range</div>', unsafe_allow_html=True)
    dates     = pd.to_datetime(df["created_at"]).dt.date
    min_date  = dates.min()
    max_date  = dates.max()

    if min_date < max_date:
        dr = st.date_input(
            "Date range", value=(min_date, max_date),
            min_value=min_date, max_value=max_date,
            label_visibility="collapsed",
        )
        if isinstance(dr, (list, tuple)) and len(dr) == 2:
            filters["date_from"], filters["date_to"] = dr[0], dr[1]
        else:
            filters["date_from"] = filters["date_to"] = min_date
    else:
        filters["date_from"] = filters["date_to"] = min_date

    # ── Decision ──────────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Decision</div>', unsafe_allow_html=True)
    all_decisions = sorted(df["decision"].dropna().unique().tolist())
    filters["decisions"] = st.multiselect(
        "Decision", options=all_decisions, default=all_decisions,
        label_visibility="collapsed",
    )

    # ── Speed ─────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Request Speed</div>', unsafe_allow_html=True)
    all_speeds = sorted(df["requested_speed"].dropna().unique().tolist())
    filters["speeds"] = st.multiselect(
        "Speed", options=all_speeds, default=all_speeds,
        label_visibility="collapsed",
    )

    # ── Amount slider ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Amount (USD)</div>', unsafe_allow_html=True)
    amt_min = float(df["amount"].min() or 0)
    amt_max = float(df["amount"].max() or 10_000)
    if amt_min < amt_max:
        lo, hi = st.slider(
            "Amount range", min_value=amt_min, max_value=amt_max,
            value=(amt_min, amt_max), format="$%.0f",
            label_visibility="collapsed",
        )
        filters["amt_lo"], filters["amt_hi"] = lo, hi
    else:
        filters["amt_lo"] = amt_min
        filters["amt_hi"] = amt_max

    # ── Engine Parameters (read-only info panel) ──────────────────────────────
    st.markdown("---")
    st.markdown('<div class="section-label">Engine Parameters</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="
        background    : {BG_CARD};
        border        : 1px solid {BORDER};
        border-left   : 3px solid {ACCENT};
        border-radius : 8px;
        padding       : 12px 14px;
        font-size     : 12px;
        line-height   : 2;
    ">
        <div style="display:flex; justify-content:space-between;">
            <span style="color:{TXT_SECONDARY};">Buffer (USD)</span>
            <span style="color:{TXT_PRIMARY}; font-weight:600;">${BUFFER_USD}</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
            <span style="color:{TXT_SECONDARY};">Dest. change window</span>
            <span style="color:{TXT_PRIMARY}; font-weight:600;">{RECENT_DEST_DAYS} days</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
            <span style="color:{TXT_SECONDARY};">Duplicate window</span>
            <span style="color:{TXT_PRIMARY}; font-weight:600;">{DUP_WINDOW_MIN} min</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"""
    <div style="color:{TXT_MUTED}; font-size:10px; line-height:1.8;">
        <b style="color:{TXT_SECONDARY}">DashEngine</b> v1.0<br>
        Withdrawal Decision Monitor<br>
        <span style="color:{ACCENT}">Streamlit · Plotly · pandas</span>
    </div>
    """, unsafe_allow_html=True)

    return filters


# ── Chart section label ───────────────────────────────────────────────────────

def _section(title: str) -> None:
    st.markdown(f'<p class="section-label">{title}</p>', unsafe_allow_html=True)


# ── Dashboard layout ──────────────────────────────────────────────────────────

def _render_dashboard(filtered_df: pd.DataFrame, review_df: pd.DataFrame) -> None:
    metrics = compute_metrics(filtered_df)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    render_kpi_row(metrics)
    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)

    # ── Row 1: Donut · Timeline ───────────────────────────────────────────────
    _section("Decision Overview")
    col_donut, col_timeline = st.columns([1, 2], gap="medium")
    _chart_cfg = {"displayModeBar": False, "responsive": True}

    with col_donut:
        st.plotly_chart(decision_donut(filtered_df),
                        use_container_width=True, config=_chart_cfg)
    with col_timeline:
        st.plotly_chart(timeline_chart(filtered_df),
                        use_container_width=True, config=_chart_cfg)

    # ── Row 2: Volume · Reason Breakdown ──────────────────────────────────────
    _section("Volume & Risk Analysis")
    col_vol, col_reason = st.columns(2, gap="medium")

    with col_vol:
        st.plotly_chart(volume_by_decision_chart(filtered_df),
                        use_container_width=True, config=_chart_cfg)
    with col_reason:
        st.plotly_chart(reason_breakdown_chart(filtered_df),
                        use_container_width=True, config=_chart_cfg)

    # ── Row 3: Speed · Amount ─────────────────────────────────────────────────
    _section("Risk Segmentation")
    col_speed, col_amt = st.columns(2, gap="medium")

    with col_speed:
        st.plotly_chart(speed_breakdown_chart(filtered_df),
                        use_container_width=True, config=_chart_cfg)
    with col_amt:
        st.plotly_chart(amount_distribution_chart(filtered_df),
                        use_container_width=True, config=_chart_cfg)

    st.markdown("---")

    # ── Tabs: Review Queue + Full Log ─────────────────────────────────────────
    hold_count = len(review_df)
    all_count  = len(filtered_df)

    tab_hold, tab_all = st.tabs([
        f"⏸  Review Queue  ({hold_count:,})",
        f"▤  Full Decision Log  ({all_count:,})",
    ])

    with tab_hold:
        render_review_queue(review_df)

    with tab_all:
        render_decisions_table(filtered_df)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    _inject_css()

    # ── Sidebar: upload section (always visible)
    with st.sidebar:
        uploaded = _render_upload_section()

    # ── No file → landing page
    if uploaded is None:
        _render_header()
        _render_landing()
        return

    # ── Process file (cached)
    with st.spinner("Running withdrawal decision engine…"):
        try:
            data = load_and_process(uploaded.read())
        except KeyError as e:
            st.error(f"Missing sheet or column in the uploaded file: {e}")
            return
        except Exception as e:
            st.error(f"Failed to process file: {e}")
            return

    # ── Sidebar: filter controls (only when data available)
    with st.sidebar:
        filters = _render_filter_section(data)

    # ── Apply filters
    filtered_df, review_df = apply_filters(data["enriched"], filters)

    # ── Header
    _render_header(data)

    # ── Filter summary badge
    total_all = len(data["decisions"])
    total_flt = len(filtered_df)
    if total_flt < total_all:
        st.caption(f"Filters active — showing **{total_flt:,}** of {total_all:,} requests")

    if filtered_df.empty:
        st.warning("No requests match the current filter selection. Adjust the sidebar controls.")
        return

    _render_dashboard(filtered_df, review_df)


if __name__ == "__main__":
    main()
