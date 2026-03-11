"""
DashEngine – components/tables.py
Renders the review queue and full decisions log as styled st.dataframe tables.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from config import REASON_LABELS, TXT_SECONDARY


# ── Shared column config helpers ──────────────────────────────────────────────

def _severity_col() -> st.column_config.ProgressColumn:
    return st.column_config.ProgressColumn(
        "Severity", min_value=0, max_value=100, format="%d"
    )


def _format_df(df: pd.DataFrame) -> pd.DataFrame:
    """Adds display-friendly formatted columns to a copy of the df."""
    out = df.copy()
    out["amount_fmt"]   = out["amount"].map(lambda x: f"${x:,.2f}" if pd.notna(x) else "—")
    out["created_fmt"]  = pd.to_datetime(out["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
    out["reason_label"] = out["reason_code"].map(lambda r: REASON_LABELS.get(r, r))
    return out


# ── Review Queue ──────────────────────────────────────────────────────────────

def render_review_queue(review_df: pd.DataFrame) -> None:
    if review_df.empty:
        st.info("No requests in the review queue for the current filter selection.")
        return

    st.caption(f"{len(review_df):,} HOLD requests — sorted by severity (highest first)")

    display = _format_df(review_df)

    show_cols = ["request_id", "account_id", "client_id", "amount_fmt",
                 "reason_label", "severity", "requested_speed", "created_fmt"]

    col_cfg = {
        "request_id":      st.column_config.TextColumn("Request ID",  width="medium"),
        "account_id":      st.column_config.TextColumn("Account",     width="small"),
        "client_id":       st.column_config.TextColumn("Client",      width="small"),
        "amount_fmt":      st.column_config.TextColumn("Amount",      width="small"),
        "reason_label":    st.column_config.TextColumn("Hold Reason", width="large"),
        "severity":        _severity_col(),
        "requested_speed": st.column_config.TextColumn("Speed",       width="small"),
        "created_fmt":     st.column_config.TextColumn("Created At",  width="medium"),
    }

    st.dataframe(
        display[show_cols],
        use_container_width=True,
        hide_index=True,
        column_config=col_cfg,
        height=min(400, 40 + len(display) * 37),
    )

    csv = review_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label     = "⬇  Export Review Queue (CSV)",
        data      = csv,
        file_name = "review_queue.csv",
        mime      = "text/csv",
        key       = "dl_review",
    )


# ── Full Decisions Log ────────────────────────────────────────────────────────

def render_decisions_table(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No decisions match the current filter selection.")
        return

    st.caption(f"{len(df):,} requests shown")

    display = _format_df(df)

    show_cols = ["request_id", "account_id", "client_id", "amount_fmt",
                 "decision", "reason_label", "severity", "requested_speed", "created_fmt"]

    col_cfg = {
        "request_id":      st.column_config.TextColumn("Request ID", width="medium"),
        "account_id":      st.column_config.TextColumn("Account",    width="small"),
        "client_id":       st.column_config.TextColumn("Client",     width="small"),
        "amount_fmt":      st.column_config.TextColumn("Amount",     width="small"),
        "decision":        st.column_config.TextColumn("Decision",   width="small"),
        "reason_label":    st.column_config.TextColumn("Reason",     width="large"),
        "severity":        _severity_col(),
        "requested_speed": st.column_config.TextColumn("Speed",      width="small"),
        "created_fmt":     st.column_config.TextColumn("Created At", width="medium"),
    }

    st.dataframe(
        display[show_cols],
        use_container_width=True,
        hide_index=True,
        column_config=col_cfg,
        height=420,
    )

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label     = "⬇  Export Full Log (CSV)",
        data      = csv,
        file_name = "decisions_log.csv",
        mime      = "text/csv",
        key       = "dl_full",
    )
