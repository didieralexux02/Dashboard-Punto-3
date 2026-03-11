"""
DashEngine – config.py
Visual constants: color palette, decision/reason mappings, Plotly base layout.
All UI modules import from here; nothing else should define colors.
"""

# ── Color Palette ─────────────────────────────────────────────────────────────
BG_PRIMARY    = "#0a0e1a"
BG_CARD       = "#111827"
BG_CARD_ALT   = "#0f172a"
BORDER        = "#1e293b"
BORDER_LIGHT  = "#243048"

ACCENT        = "#6366f1"
ACCENT_LIGHT  = "#818cf8"
ACCENT_GLOW   = "rgba(99,102,241,0.15)"

TXT_PRIMARY   = "#f1f5f9"
TXT_SECONDARY = "#94a3b8"
TXT_MUTED     = "#475569"

# ── Decision palette ──────────────────────────────────────────────────────────
DECISION_COLORS = {
    "APPROVE": "#10b981",
    "HOLD":    "#f59e0b",
    "REJECT":  "#ef4444",
}

DECISION_BG = {
    "APPROVE": "rgba(16,185,129,0.10)",
    "HOLD":    "rgba(245,158,11,0.10)",
    "REJECT":  "rgba(239,68,68,0.10)",
}

# ── Severity → color (high severity = red spectrum) ──────────────────────────
SEVERITY_COLORS: dict[int, str] = {
    100: "#ef4444",
    95:  "#f43f5e",
    90:  "#ec4899",
    85:  "#f97316",
    70:  "#eab308",
    65:  "#f59e0b",
    55:  "#84cc16",
    45:  "#22d3ee",
    35:  "#818cf8",
    0:   "#10b981",
}

# ── Reason code human labels ──────────────────────────────────────────────────
REASON_LABELS: dict[str, str] = {
    "KYC_NOT_VERIFIED":                    "KYC Not Verified",
    "ACCOUNT_NOT_ACTIVE":                  "Account Not Active",
    "UNWHITELISTED_HIGH_AML":              "Unwhitelisted High AML",
    "INVALID_AMOUNT":                      "Invalid Amount",
    "DUPLICATE_REQUEST":                   "Duplicate Request",
    "INSUFFICIENT_SETTLED_AFTER_BUFFER":   "Insuff. Settled Balance",
    "INSUFFICIENT_AVAILABLE_AFTER_BUFFER": "Insuff. Available Balance",
    "DEST_CHANGED_RECENTLY":               "Dest. Changed Recently",
    "URGENT_RISK_TIER":                    "Urgent + Risk Tier",
    "OK":                                  "Approved – No Issues",
}

# ── Plotly dark base layout (applied to every figure) ────────────────────────
PLOTLY_BASE = dict(
    paper_bgcolor = BG_CARD,
    plot_bgcolor  = BG_CARD,
    font          = dict(
        color  = TXT_SECONDARY,
        family = "Inter, system-ui, -apple-system, sans-serif",
        size   = 12,
    ),
    xaxis = dict(
        gridcolor   = BORDER,
        linecolor   = BORDER,
        zerolinecolor = BORDER,
        tickfont    = dict(color=TXT_MUTED, size=11),
    ),
    yaxis = dict(
        gridcolor   = BORDER,
        linecolor   = BORDER,
        zerolinecolor = BORDER,
        tickfont    = dict(color=TXT_MUTED, size=11),
    ),
    legend = dict(
        bgcolor     = BG_CARD,
        bordercolor = BORDER,
        borderwidth = 1,
        font        = dict(color=TXT_SECONDARY, size=11),
    ),
    margin    = dict(t=48, b=36, l=60, r=16),
    hoverlabel = dict(
        bgcolor     = "#1e293b",
        bordercolor = BORDER_LIGHT,
        font        = dict(color=TXT_PRIMARY, size=12),
    ),
    title_font = dict(color=TXT_PRIMARY, size=14, family="Inter, system-ui, sans-serif"),
)
