"""
DashEngine – components/kpis.py
Renders the top KPI row as HTML metric cards via st.markdown.
"""

from __future__ import annotations

import streamlit as st

from config import (
    ACCENT, BG_CARD, BORDER, DECISION_COLORS,
    TXT_PRIMARY, TXT_SECONDARY, TXT_MUTED,
)


# ── Card builder ──────────────────────────────────────────────────────────────

def _card(label: str, value: str, sub: str = "",
          accent: str = ACCENT, icon: str = "") -> str:
    """Returns an HTML string for a single KPI card."""
    return f"""
<div style="
    background      : {BG_CARD};
    border          : 1px solid {BORDER};
    border-top      : 3px solid {accent};
    border-radius   : 10px;
    padding         : 18px 16px 14px;
    min-height      : 108px;
    display         : flex;
    flex-direction  : column;
    justify-content : space-between;
    box-sizing      : border-box;
">
    <div style="
        color          : {TXT_SECONDARY};
        font-size      : 10px;
        font-weight    : 600;
        letter-spacing : 0.10em;
        text-transform : uppercase;
        display        : flex;
        align-items    : center;
        gap            : 5px;
    ">{icon}&nbsp;{label}</div>
    <div style="
        color          : {TXT_PRIMARY};
        font-size      : 24px;
        font-weight    : 700;
        letter-spacing : -0.03em;
        line-height    : 1.1;
        margin-top     : 6px;
    ">{value}</div>
    <div style="
        color          : {accent};
        font-size      : 11px;
        font-weight    : 500;
        margin-top     : 4px;
        opacity        : 0.85;
    ">{sub if sub else "&nbsp;"}</div>
</div>
"""


# ── Public render function ────────────────────────────────────────────────────

def render_kpi_row(metrics: dict) -> None:
    """Renders 6 KPI cards in a single st.columns row."""
    total_vol = metrics["total_volume"]

    cards = [
        dict(
            label  = "Total Requests",
            value  = f"{metrics['total']:,}",
            sub    = "",
            accent = ACCENT,
            icon   = "▤",
        ),
        dict(
            label  = "Approved",
            value  = f"{metrics['approve']:,}",
            sub    = f"{metrics['approve_rate']:.1f}% approval rate",
            accent = DECISION_COLORS["APPROVE"],
            icon   = "✓",
        ),
        dict(
            label  = "On Hold",
            value  = f"{metrics['hold']:,}",
            sub    = f"{metrics['hold_rate']:.1f}% of total",
            accent = DECISION_COLORS["HOLD"],
            icon   = "⏸",
        ),
        dict(
            label  = "Rejected",
            value  = f"{metrics['reject']:,}",
            sub    = f"{metrics['reject_rate']:.1f}% reject rate",
            accent = DECISION_COLORS["REJECT"],
            icon   = "✗",
        ),
        dict(
            label  = "Total Volume",
            value  = f"${total_vol:,.0f}",
            sub    = f"Avg ${metrics['avg_amount']:,.0f} / request",
            accent = ACCENT,
            icon   = "$",
        ),
        dict(
            label  = "Approved Volume",
            value  = f"${metrics['approved_vol']:,.0f}",
            sub    = (f"{metrics['approved_vol_pct']:.1f}% of total vol"
                      if total_vol else "—"),
            accent = DECISION_COLORS["APPROVE"],
            icon   = "↑",
        ),
    ]

    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        with col:
            st.markdown(_card(**card), unsafe_allow_html=True)
