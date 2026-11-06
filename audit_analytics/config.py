"""Shared settings: chart of accounts, holiday calendar and default audit parameters."""
from __future__ import annotations

import datetime as dt

FISCAL_YEAR = 2025

# Company policy: manual entries at or above this amount need a second approver.
APPROVAL_THRESHOLD = 10_000.00

CHART_OF_ACCOUNTS: dict[str, str] = {
    "1000": "Cash - Operating",
    "1200": "Accounts Receivable",
    "1400": "Inventory",
    "1500": "Prepaid Expenses",
    "2000": "Accounts Payable",
    "2100": "Accrued Liabilities",
    "4000": "Revenue - Product Sales",
    "4100": "Revenue - Services",
    "5000": "Cost of Goods Sold",
    "6000": "Salaries & Wages",
    "6100": "Rent Expense",
    "6200": "Utilities",
    "6300": "Professional Fees",
    "6400": "Travel & Entertainment",
    "6500": "Office Supplies",
    "6600": "Repairs & Maintenance",
    "6900": "Miscellaneous Expense",
}

# Company holiday calendar (US federal holidays observed in FY2025).
HOLIDAYS: frozenset[dt.date] = frozenset(
    dt.date(2025, m, d)
    for m, d in [
        (1, 1), (1, 20), (2, 17), (5, 26), (6, 19), (7, 4),
        (9, 1), (10, 13), (11, 11), (11, 27), (12, 25),
    ]
)

# Default parameters for the journal entry tests (all adjustable in the app).
DEFAULT_PARAMS = {
    "approval_threshold": APPROVAL_THRESHOLD,
    "below_threshold_band": 0.05,   # flag manual entries within 5% under the threshold
    "round_multiple": 1_000,        # amounts that are exact multiples of $1,000
    "business_hours": (7, 20),      # manual postings outside 7:00-20:00 are after hours
    "period_end_days": 3,           # last N days of each quarter
    "duplicate_window_days": 30,    # look-back window for duplicate payments
}
