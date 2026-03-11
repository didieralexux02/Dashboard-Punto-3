"""
DashEngine – components/charts.py
All Plotly figure builders.  Each function is pure: takes a DataFrame,
returns a go.Figure.  No Streamlit calls here.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from config import (
    PLOTLY_BASE, DECISION_COLORS, REASON_LABELS,
    BG_CARD, TXT_PRIMARY, TXT_SECONDARY, TXT_MUTED, ACCENT,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _fig(**overrides) -> go.Figure:
    """Return a Figure with the dark base layout pre-applied."""
    fig = go.Figure()
    layout = {**PLOTLY_BASE, **overrides}
    fig.update_layout(**layout)
    return fig


def _decision_colors(labels: list[str]) -> list[str]:
    return [DECISION_COLORS.get(d, ACCENT) for d in labels]


# ── Chart 1: Decision Donut ───────────────────────────────────────────────────

def decision_donut(df: pd.DataFrame) -> go.Figure:
    counts = df["decision"].value_counts().reindex(["APPROVE", "HOLD", "REJECT"]).fillna(0)
    total  = int(counts.sum())

    fig = go.Figure(go.Pie(
        labels        = counts.index.tolist(),
        values        = counts.values.tolist(),
        hole          = 0.72,
        marker        = dict(
            colors = _decision_colors(counts.index.tolist()),
            line   = dict(color=BG_CARD, width=3),
        ),
        textinfo      = "percent",
        textfont      = dict(color=TXT_PRIMARY, size=11),
        hovertemplate = "<b>%{label}</b><br>Count: %{value:,}<br>Share: %{percent}<extra></extra>",
        direction     = "clockwise",
        sort          = False,
    ))
    fig.add_annotation(
        text    = f"<b>{total:,}</b><br><span style='font-size:10px'>{TXT_MUTED}</span>",
        x=0.5, y=0.5, showarrow=False,
        font    = dict(color=TXT_PRIMARY, size=16),
        xanchor = "center", yanchor="middle",
    )
    fig.update_layout(**{
        **PLOTLY_BASE,
        "title":      "Decision Distribution",
        "showlegend": True,
        "height":     260,
        "margin":     dict(t=40, b=12, l=12, r=90),
        "legend":     {
            **PLOTLY_BASE["legend"],
            "font":        dict(color=TXT_SECONDARY, size=10),
            "orientation": "v",
            "yanchor":     "middle", "y": 0.5,
            "xanchor":     "left",   "x": 1.01,
        },
    })
    return fig


# ── Chart 2: Timeline (stacked bar by day) ────────────────────────────────────

def timeline_chart(df: pd.DataFrame) -> go.Figure:
    df2 = df.copy()
    df2["date"] = pd.to_datetime(df2["created_at"]).dt.date
    grp = (df2.groupby(["date", "decision"])
             .size()
             .reset_index(name="count"))

    fig = _fig(title="Request Volume Over Time",
               xaxis_title="", yaxis_title="Requests",
               barmode="stack", height=320,
               margin=dict(t=48, b=36, l=48, r=16),
               legend=dict(**PLOTLY_BASE["legend"],
                           orientation="h",
                           yanchor="bottom", y=1.04,
                           xanchor="right", x=1))

    for decision in ["APPROVE", "HOLD", "REJECT"]:
        sub = grp[grp["decision"] == decision]
        if sub.empty:
            continue
        fig.add_trace(go.Bar(
            x     = sub["date"],
            y     = sub["count"],
            name  = decision,
            marker_color = DECISION_COLORS[decision],
            opacity      = 0.88,
            hovertemplate= f"<b>{decision}</b><br>%{{x}}<br>Count: %{{y:,}}<extra></extra>",
        ))
    return fig


# ── Chart 3: Reason Code Horizontal Bar ───────────────────────────────────────

def reason_breakdown_chart(df: pd.DataFrame) -> go.Figure:
    flagged = df[df["reason_code"] != "OK"].copy()

    if flagged.empty:
        fig = _fig(title="Reason Code Breakdown", height=320)
        fig.add_annotation(text="No flagged reasons in current selection.",
                           x=0.5, y=0.5, showarrow=False,
                           font=dict(color=TXT_SECONDARY, size=13))
        return fig

    counts = (flagged
              .groupby(["reason_code", "decision"])
              .size()
              .reset_index(name="count")
              .sort_values("count", ascending=True))
    counts["label"] = counts["reason_code"].map(lambda r: REASON_LABELS.get(r, r))

    # Compute total per label for sorting
    order = (counts.groupby("label")["count"].sum()
                   .sort_values()
                   .index.tolist())

    fig = _fig(title="Reason Code Breakdown",
               xaxis_title="Count", yaxis_title="",
               barmode="stack", height=max(320, len(order) * 42 + 100),
               margin=dict(t=40, b=80, l=190, r=16),
               legend=dict(**PLOTLY_BASE["legend"],
                           orientation="h",
                           yanchor="top", y=-0.22,
                           xanchor="center", x=0.5))

    for decision in ["REJECT", "HOLD"]:
        sub = counts[counts["decision"] == decision]
        if sub.empty:
            continue
        fig.add_trace(go.Bar(
            y             = sub["label"],
            x             = sub["count"],
            name          = decision,
            orientation   = "h",
            marker_color  = DECISION_COLORS[decision],
            opacity       = 0.85,
            hovertemplate = f"<b>%{{y}}</b><br>{decision}: %{{x:,}}<extra></extra>",
        ))

    fig.update_layout(yaxis=dict(**PLOTLY_BASE["yaxis"],
                                  categoryorder="array",
                                  categoryarray=order))
    return fig




# ── Chart 5: Request Speed vs Decision ────────────────────────────────────────

def speed_breakdown_chart(df: pd.DataFrame) -> go.Figure:
    grp = (df.groupby(["requested_speed", "decision"])
             .size()
             .reset_index(name="count"))

    fig = _fig(title="Request Speed vs Decision",
               xaxis_title="Speed", yaxis_title="Requests",
               barmode="group", height=300,
               margin=dict(t=40, b=80, l=48, r=16),
               legend=dict(**PLOTLY_BASE["legend"],
                           orientation="h",
                           yanchor="top", y=-0.30,
                           xanchor="center", x=0.5))

    for decision in ["APPROVE", "HOLD", "REJECT"]:
        sub = grp[grp["decision"] == decision]
        if sub.empty:
            continue
        fig.add_trace(go.Bar(
            x             = sub["requested_speed"].str.capitalize(),
            y             = sub["count"],
            name          = decision,
            marker_color  = DECISION_COLORS[decision],
            opacity       = 0.85,
            hovertemplate = f"<b>%{{x}}</b><br>{decision}: %{{y:,}}<extra></extra>",
        ))
    return fig


# ── Chart 6: Amount Distribution Histogram ────────────────────────────────────

def amount_distribution_chart(df: pd.DataFrame) -> go.Figure:
    fig = _fig(title="Amount Distribution by Decision",
               xaxis_title="Amount (USD)", yaxis_title="Count",
               barmode="overlay", height=300,
               margin=dict(t=40, b=80, l=48, r=16),
               legend=dict(**PLOTLY_BASE["legend"],
                           orientation="h",
                           yanchor="top", y=-0.30,
                           xanchor="center", x=0.5))

    for decision in ["APPROVE", "HOLD", "REJECT"]:
        sub = df[df["decision"] == decision]["amount"].dropna()
        if sub.empty:
            continue
        fig.add_trace(go.Histogram(
            x             = sub,
            name          = decision,
            marker_color  = DECISION_COLORS[decision],
            opacity       = 0.65,
            nbinsx        = 30,
            hovertemplate = f"<b>{decision}</b><br>$%{{x:,.0f}}<br>Count: %{{y}}<extra></extra>",
        ))
    return fig


# ── Chart 7: Volume (USD) by Decision ─────────────────────────────────────────

def volume_by_decision_chart(df: pd.DataFrame) -> go.Figure:
    grp = (df.groupby("decision")
             .agg(volume=("amount", "sum"), count=("request_id", "count"))
             .reset_index())

    max_vol = grp["volume"].max() if not grp.empty else 1

    fig = _fig(title="Total Volume by Decision (USD)",
               xaxis_title="", yaxis_title="",
               height=300, showlegend=False,
               margin=dict(t=48, b=36, l=16, r=16),
               bargap=0.38)

    fig.add_trace(go.Bar(
        x                = grp["decision"],
        y                = grp["volume"],
        marker_color     = _decision_colors(grp["decision"].tolist()),
        marker_line      = dict(width=0),
        opacity          = 0.90,
        text             = grp["volume"].map(lambda v: f"${v:,.0f}"),
        textposition     = "inside",
        insidetextanchor = "middle",
        textfont         = dict(color="#ffffff", size=12, family="Inter, sans-serif"),
        hovertemplate    = "<b>%{x}</b><br>Volume: $%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        yaxis=dict(
            **PLOTLY_BASE["yaxis"],
            showticklabels = False,
            showgrid       = False,
            zeroline       = False,
            range          = [0, max_vol * 1.15],
        ),
        xaxis=dict(**PLOTLY_BASE["xaxis"], showgrid=False),
    )
    return fig
