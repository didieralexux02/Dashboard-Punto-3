# DashEngine

El Link para el dashboard es el siguiente. https://dashboard-punto-3-kxag7ppcc2bgzxzamtcg7e.streamlit.app/

Solo es necesario cargar el archivo en la barra izquierda "Withdrawals.xlsx" que se envio en la prueba y se carga autimaticamente el dashboard.







---

## Overview

DashEngine processes a withdrawal requests Excel file, runs the full decision engine, and presents the results as an interactive analytics dashboard built with Streamlit and Plotly.

Decisions are classified as **APPROVE**, **HOLD**, or **REJECT** based on account status, KYC verification, balance checks, destination history, and AML risk rules.

---

## Requirements

```
Python 3.10+
streamlit >= 1.35
pandas >= 2.0
plotly >= 5.20
openpyxl >= 3.1
```

Install dependencies:

```bash
pip install -r DashEngine/requirements.txt
```

---

## Usage

Run from the project root:

```bash
streamlit run DashEngine/app.py
```

Then upload your `withdrawals.xlsx` file using the sidebar. The file must contain three sheets:

| Sheet | Key columns |
|---|---|
| `withdrawal_requests` | `request_id`, `account_id`, `client_id`, `amount`, `destination_id`, `requested_speed`, `created_at` |
| `account_snapshot` | `account_id`, `as_of`, `account_status`, `kyc_status`, `aml_risk_tier`, `available_cash`, `settled_cash` |
| `destination_registry` | `destination_id`, `last_changed_at`, `is_whitelisted` |

---

## Engine Parameters

| Parameter | Value | Description |
|---|---|---|
| `BUFFER_USD` | $50 | Minimum balance required after withdrawal |
| `RECENT_DEST_DAYS` | 7 days | Destination must be unchanged for this period |
| `DUP_WINDOW_MIN` | 15 min | Window for duplicate request detection |

---

## Project Structure

```
DashEngine/
├── app.py                  # Entry point — layout, sidebar, CSS
├── config.py               # Color palette and Plotly base template
├── data_processing.py      # Decision engine, caching, metrics, filters
├── requirements.txt
└── components/
    ├── charts.py           # Plotly figure builders (pure functions)
    ├── kpis.py             # KPI card row
    └── tables.py           # Review queue and decisions log tables
```

---

## Dashboard Sections

- **KPI Row** — Total requests, approval/hold/reject counts and rates, total and approved volume
- **Decision Distribution** — Donut chart with request share per decision
- **Request Volume Over Time** — Stacked bar chart by day
- **Total Volume by Decision** — USD volume per decision outcome
- **Reason Code Breakdown** — Frequency of each flagging reason
- **Request Speed vs Decision** — Standard vs urgent split by outcome
- **Amount Distribution** — Histogram of withdrawal amounts by decision
- **Review Queue** — All HOLD requests sorted by severity, with CSV export
- **Full Decision Log** — Complete filterable log with CSV export

---

## Sidebar Filters

Date range · Decision type · Request speed · Amount range
