"""
DashEngine – data_processing.py
Loads the Excel, runs the full withdrawal decision engine, enriches the output,
and exposes clean metric helpers.  All functions are pure / cache-friendly.
UI modules must NOT import pandas or run engine logic – only call these helpers.
"""

from __future__ import annotations

import io
from datetime import timedelta

import pandas as pd
import streamlit as st

# ── Engine constants (mirrors withdrawal_engine.py) ───────────────────────────
BUFFER_USD       = 50
RECENT_DEST_DAYS = 7
DUP_WINDOW_MIN   = 15

SEVERITY: dict[str, int] = {
    "KYC_NOT_VERIFIED":                   100,
    "ACCOUNT_NOT_ACTIVE":                  95,
    "UNWHITELISTED_HIGH_AML":              90,
    "INVALID_AMOUNT":                      85,
    "DUPLICATE_REQUEST":                   70,
    "INSUFFICIENT_SETTLED_AFTER_BUFFER":   65,
    "INSUFFICIENT_AVAILABLE_AFTER_BUFFER": 55,
    "DEST_CHANGED_RECENTLY":               45,
    "URGENT_RISK_TIER":                    35,
}

# ── Internal engine helpers ────────────────────────────────────────────────────

def _flag_duplicates(req: pd.DataFrame) -> set:
    sorted_req    = req.sort_values("created_at").reset_index(drop=True)
    duplicate_ids: set = set()
    for i, row in sorted_req.iterrows():
        window_start = row["created_at"] - timedelta(minutes=DUP_WINDOW_MIN)
        mask = (
            (sorted_req.index < i) &
            (sorted_req["account_id"]    == row["account_id"]) &
            (sorted_req["amount"]         == row["amount"]) &
            (sorted_req["destination_id"] == row["destination_id"]) &
            (sorted_req["created_at"]     >= window_start)
        )
        if mask.any():
            duplicate_ids.add(row["request_id"])
    return duplicate_ids


def _evaluate(row: pd.Series, snap_map: dict, dest_map: dict,
              duplicate_ids: set) -> tuple[str, str, int]:
    req_id  = row["request_id"]
    acct_id = row["account_id"]
    dest_id = row["destination_id"]
    amount  = row["amount"]
    speed   = str(row.get("requested_speed", "")).strip().lower()

    snap = snap_map.get(acct_id, {})
    dest = dest_map.get(dest_id, {})

    reject_reasons: list[str] = []
    hold_reasons:   list[str] = []

    # ── REJECT checks ─────────────────────────────────────────────────────────
    if snap.get("account_status", "") != "active":
        reject_reasons.append("ACCOUNT_NOT_ACTIVE")
    if snap.get("kyc_status", "") != "verified":
        reject_reasons.append("KYC_NOT_VERIFIED")
    if pd.isna(amount) or amount <= 0:
        reject_reasons.append("INVALID_AMOUNT")
    if req_id in duplicate_ids:
        reject_reasons.append("DUPLICATE_REQUEST")
    aml_tier       = snap.get("aml_risk_tier", "")
    is_whitelisted = dest.get("is_whitelisted", True)
    if aml_tier == "high" and not is_whitelisted:
        reject_reasons.append("UNWHITELISTED_HIGH_AML")

    # ── HOLD checks (skipped when there is a reject) ──────────────────────────
    if not reject_reasons:
        available = snap.get("available_cash", 0) or 0
        settled   = snap.get("settled_cash",   0) or 0

        if (available - amount) < BUFFER_USD:
            hold_reasons.append("INSUFFICIENT_AVAILABLE_AFTER_BUFFER")
        if (settled - amount) < BUFFER_USD:
            hold_reasons.append("INSUFFICIENT_SETTLED_AFTER_BUFFER")

        last_changed = dest.get("last_changed_at")
        as_of        = snap.get("as_of")
        if last_changed and as_of:
            days_since = (as_of - last_changed).days
            if days_since <= RECENT_DEST_DAYS:
                hold_reasons.append("DEST_CHANGED_RECENTLY")

        if speed == "urgent" and aml_tier in ("medium", "high"):
            hold_reasons.append("URGENT_RISK_TIER")

    # ── Final verdict ─────────────────────────────────────────────────────────
    if reject_reasons:
        best = max(reject_reasons, key=lambda r: SEVERITY[r])
        return "REJECT", best, SEVERITY[best]
    if hold_reasons:
        best = max(hold_reasons, key=lambda r: SEVERITY[r])
        return "HOLD", best, SEVERITY[best]
    return "APPROVE", "OK", 0


# ── Public API ────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_and_process(file_bytes: bytes) -> dict:
    """
    Parse the uploaded Excel, run the decision engine, enrich the output,
    and return a dict with all DataFrames needed by the dashboard.

    Cached by content hash – re-running with the same file is instant.
    """
    xl   = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
    req  = xl["withdrawal_requests"].copy()
    snap = xl["account_snapshot"].copy()
    dest = xl["destination_registry"].copy()

    # ── Parse timestamps ──────────────────────────────────────────────────────
    req["created_at"]       = pd.to_datetime(req["created_at"],       utc=True)
    snap["as_of"]           = pd.to_datetime(snap["as_of"],           utc=True)
    dest["last_changed_at"] = pd.to_datetime(dest["last_changed_at"], utc=True)

    # ── Build lookup maps ─────────────────────────────────────────────────────
    snap_map = snap.set_index("account_id").to_dict("index")
    dest_map = dest.set_index("destination_id").to_dict("index")

    duplicate_ids = _flag_duplicates(req)

    # ── Evaluate every request ────────────────────────────────────────────────
    records = []
    for _, row in req.iterrows():
        decision, reason_code, severity = _evaluate(row, snap_map, dest_map, duplicate_ids)
        ts = row["created_at"]
        records.append({
            "request_id":      row["request_id"],
            "account_id":      row["account_id"],
            "client_id":       row.get("client_id", ""),
            "amount":          row["amount"],
            "destination_id":  row["destination_id"],
            "requested_speed": row.get("requested_speed", ""),
            "created_at":      ts.tz_localize(None) if ts.tzinfo else ts,
            "decision":        decision,
            "reason_code":     reason_code,
            "severity":        severity,
        })

    decisions_df = pd.DataFrame(records)

    # ── Enrich with account / destination context ─────────────────────────────
    snap_ctx = snap[["account_id", "available_cash", "settled_cash"]].copy()
    dest_ctx = dest[["destination_id", "is_whitelisted"]].copy()

    # Strip tz from snapshot dates before merge to avoid type conflicts
    snap_ctx = snap_ctx.copy()

    enriched = (
        decisions_df
        .merge(snap_ctx, on="account_id",    how="left")
        .merge(dest_ctx, on="destination_id", how="left")
    )

    review_df = (
        decisions_df[decisions_df["decision"] == "HOLD"]
        .sort_values("severity", ascending=False)
        .reset_index(drop=True)
    )

    return {
        "decisions":       decisions_df,
        "enriched":        enriched,
        "review":          review_df,
        "snap":            snap,
        "dest":            dest,
        "req":             req,
        "duplicate_count": len(duplicate_ids),
    }


def compute_metrics(df: pd.DataFrame) -> dict:
    """
    Returns a flat dict of summary KPIs from a (possibly filtered) decisions df.
    Accepts both the raw decisions_df and the enriched df.
    """
    total   = len(df)
    if total == 0:
        return {k: 0 for k in ("total", "approve", "hold", "reject",
                                "approve_rate", "hold_rate", "reject_rate",
                                "total_volume", "avg_amount", "approved_vol")}

    counts   = df["decision"].value_counts().to_dict()
    approve  = counts.get("APPROVE", 0)
    hold     = counts.get("HOLD",    0)
    reject   = counts.get("REJECT",  0)

    vol_total    = df["amount"].sum()
    vol_approved = df[df["decision"] == "APPROVE"]["amount"].sum()

    return {
        "total":        total,
        "approve":      approve,
        "hold":         hold,
        "reject":       reject,
        "approve_rate": approve / total * 100,
        "hold_rate":    hold    / total * 100,
        "reject_rate":  reject  / total * 100,
        "total_volume": vol_total,
        "avg_amount":   df["amount"].mean(),
        "approved_vol": vol_approved,
        "approved_vol_pct": (vol_approved / vol_total * 100) if vol_total else 0,
    }


def apply_filters(enriched_df: pd.DataFrame, filters: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Applies sidebar filter state to the enriched DataFrame.
    Returns (filtered_df, review_df).
    """
    df = enriched_df.copy()
    dates = pd.to_datetime(df["created_at"]).dt.date

    if "date_from" in filters and filters["date_from"]:
        df = df[dates >= filters["date_from"]]
    if "date_to" in filters and filters["date_to"]:
        dates = pd.to_datetime(df["created_at"]).dt.date   # re-index after slice
        df = df[dates <= filters["date_to"]]

    if filters.get("decisions"):
        df = df[df["decision"].isin(filters["decisions"])]
    if filters.get("speeds"):
        df = df[df["requested_speed"].isin(filters["speeds"])]
    if "amt_lo" in filters and "amt_hi" in filters:
        df = df[(df["amount"] >= filters["amt_lo"]) & (df["amount"] <= filters["amt_hi"])]
    if "aml_tiers" in filters and filters["aml_tiers"] and "aml_risk_tier" in df.columns:
        df = df[df["aml_risk_tier"].isin(filters["aml_tiers"])]

    review_df = (
        df[df["decision"] == "HOLD"]
        .sort_values("severity", ascending=False)
        .reset_index(drop=True)
    )
    return df.reset_index(drop=True), review_df
