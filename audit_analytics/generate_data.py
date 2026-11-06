"""Generate a synthetic FY2025 general ledger with planted anomalies.

Run:  python -m audit_analytics.generate_data

Writes two files to data/:
  sample_general_ledger.csv  - ~5,000 journal entries for a fictional distributor
  anomaly_key.csv            - the "answer key": which entries were planted and why

All company, vendor and user names are fictional.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from .config import APPROVAL_THRESHOLD, CHART_OF_ACCOUNTS, FISCAL_YEAR, HOLIDAYS

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SEED = 2025
N_ROUTINE = 5_000

PREPARERS = ["jsmith", "mgarcia", "alee", "rpatel", "kchen", "dwilson"]
APPROVERS = ["lbrown", "tnguyen"]
SYSTEM_USER = "SYS_BATCH"

VENDORS = [
    "Northwind Supply Co", "Bluewater Utilities", "Summit Office Products",
    "Ironclad Repairs Inc", "Cascade Legal Group", "Meridian Freight",
    "Harbor IT Services", "Pinecrest Travel", "Granite Facilities Mgmt",
    "Lakeside Packaging",
]
EXPENSE_ACCOUNTS = ["6200", "6300", "6400", "6500", "6600", "6900"]

# (debit, credit, weight, log-mean, log-sd, source, uses_vendor, description)
TEMPLATES = [
    ("1200", "4000", 0.20, 7.6, 1.5, "Automated", False, "Customer invoice - product"),
    ("1200", "4100", 0.06, 8.0, 1.4, "Automated", False, "Customer invoice - services"),
    ("1000", "1200", 0.16, 7.8, 1.5, "Automated", False, "Customer payment received"),
    ("5000", "1400", 0.10, 7.3, 1.5, "Automated", False, "Cost of goods shipped"),
    ("1400", "2000", 0.10, 8.2, 1.4, "Automated", True, "Inventory purchase"),
    (None, "2000", 0.12, 6.5, 1.6, "Manual", True, "Vendor invoice - expense"),
    ("2000", "1000", 0.16, 7.5, 1.5, "Automated", True, "AP payment run"),
    (None, "2100", 0.05, 7.5, 1.5, "Manual", False, "Month-end accrual"),
    ("1500", "1000", 0.05, 7.8, 1.3, "Manual", False, "Prepaid expense"),
]


def _business_days(rng_dates: pd.DatetimeIndex) -> list[dt.date]:
    return [d.date() for d in rng_dates if d.weekday() < 5 and d.date() not in HOLIDAYS]


YEAR_DAYS = pd.date_range(f"{FISCAL_YEAR}-01-01", f"{FISCAL_YEAR}-12-31", freq="D")
BUSINESS_DAYS = _business_days(YEAR_DAYS)
WEEKEND_OR_HOLIDAY = [d.date() for d in YEAR_DAYS if d.weekday() >= 5 or d.date() in HOLIDAYS]


def _timestamp(rng: np.random.Generator, day: dt.date, source: str) -> dt.datetime:
    # Batch jobs run overnight; people post during the working day.
    hour = rng.integers(1, 4) if source == "Automated" else rng.integers(8, 18)
    return dt.datetime.combine(day, dt.time(int(hour), int(rng.integers(0, 60)), int(rng.integers(0, 60))))


def _invoice(rng: np.random.Generator) -> str:
    return f"INV-{rng.integers(10000, 99999)}"


def _approver(rng: np.random.Generator, source: str, amount: float) -> str:
    if source == "Manual" and amount >= APPROVAL_THRESHOLD:
        return str(rng.choice(APPROVERS))
    return ""


def _routine_entries(rng: np.random.Generator) -> list[dict]:
    weights = np.array([t[2] for t in TEMPLATES])
    picks = rng.choice(len(TEMPLATES), size=N_ROUTINE, p=weights / weights.sum())
    rows = []
    for i in picks:
        debit, credit, _, mu, sd, source, uses_vendor, desc = TEMPLATES[i]
        amount = round(float(np.clip(rng.lognormal(mu, sd), 5, 750_000)), 2)
        day = BUSINESS_DAYS[rng.integers(len(BUSINESS_DAYS))]
        rows.append({
            "posted_at": _timestamp(rng, day, source),
            "source": source,
            "created_by": SYSTEM_USER if source == "Automated" else str(rng.choice(PREPARERS)),
            "approved_by": _approver(rng, source, amount),
            "debit_account": debit or str(rng.choice(EXPENSE_ACCOUNTS)),
            "credit_account": credit,
            "amount": amount,
            "description": desc,
            "vendor": str(rng.choice(VENDORS)) if uses_vendor else "",
            "invoice_number": _invoice(rng) if uses_vendor else "",
            "_planted": "",
        })

    # Recurring entries: biweekly payroll and monthly rent.
    for friday in pd.date_range(f"{FISCAL_YEAR}-01-10", f"{FISCAL_YEAR}-12-31", freq="14D"):
        rows.append({
            "posted_at": _timestamp(rng, friday.date(), "Automated"), "source": "Automated",
            "created_by": SYSTEM_USER, "approved_by": "", "debit_account": "6000",
            "credit_account": "1000", "amount": round(float(rng.normal(184_000, 6_000)), 2),
            "description": "Payroll", "vendor": "", "invoice_number": "", "_planted": "",
        })
    for month in range(1, 13):
        first_bd = next(d for d in BUSINESS_DAYS if d.month == month)
        rows.append({
            "posted_at": _timestamp(rng, first_bd, "Automated"), "source": "Automated",
            "created_by": SYSTEM_USER, "approved_by": "", "debit_account": "6100",
            "credit_account": "1000", "amount": 12_500.00, "description": "Monthly rent",
            "vendor": "", "invoice_number": "", "_planted": "",
        })
    return rows


def _manual(rng, day, amount, debit, credit, desc, user=None, approver=None,
            vendor="", hour=None, planted="") -> dict:
    ts = _timestamp(rng, day, "Manual")
    if hour is not None:
        ts = ts.replace(hour=hour)
    user = user or str(rng.choice(PREPARERS))
    return {
        "posted_at": ts, "source": "Manual", "created_by": user,
        "approved_by": approver if approver is not None else _approver(rng, "Manual", amount),
        "debit_account": debit, "credit_account": credit, "amount": round(amount, 2),
        "description": desc, "vendor": vendor,
        "invoice_number": _invoice(rng) if vendor else "", "_planted": planted,
    }


def _planted_entries(rng: np.random.Generator, routine: list[dict]) -> list[dict]:
    rows: list[dict] = []
    pick_bd = lambda: BUSINESS_DAYS[rng.integers(len(BUSINESS_DAYS))]  # noqa: E731

    # 1. Manual entries posted on weekends or holidays.
    for _ in range(12):
        day = WEEKEND_OR_HOLIDAY[rng.integers(len(WEEKEND_OR_HOLIDAY))]
        rows.append(_manual(rng, day, float(rng.lognormal(7.8, 1.0)), str(rng.choice(EXPENSE_ACCOUNTS)),
                            "2100", "Adjusting entry", planted="weekend_holiday"))

    # 2. Manual entries posted late at night.
    for _ in range(10):
        rows.append(_manual(rng, pick_bd(), float(rng.lognormal(7.8, 1.0)), str(rng.choice(EXPENSE_ACCOUNTS)),
                            "1000", "Expense reclass", hour=int(rng.integers(21, 24)), planted="after_hours"))

    # 3. Structuring: one preparer splits payments to a new vendor to stay under the approval limit.
    for _ in range(24):
        amount = float(rng.uniform(9_500, 9_999.99))
        rows.append(_manual(rng, pick_bd(), amount, "6300", "1000", "Consulting services",
                            user="dwilson", vendor="Apex Consulting LLC", planted="just_below_threshold"))

    # 4. A manager posts and approves their own large, round-dollar entries - some over the weekend.
    for i, amount in enumerate([25_000, 50_000, 40_000, 100_000, 75_000]):
        day = WEEKEND_OR_HOLIDAY[rng.integers(len(WEEKEND_OR_HOLIDAY))] if i % 2 == 0 else pick_bd()
        tags = "round_amount;self_approved" + (";weekend_holiday" if i % 2 == 0 else "")
        rows.append(_manual(rng, day, float(amount), "6900", "1000", "Management fee",
                            user="tnguyen", approver="tnguyen", planted=tags))

    # 5. Other round-dollar manual entries.
    for amount in [20_000, 15_000, 30_000]:
        rows.append(_manual(rng, pick_bd(), float(amount), "6600", "2100", "Repairs accrual",
                            planted="round_amount"))

    # 6. Large manual entries that skipped the required approval.
    for _ in range(3):
        rows.append(_manual(rng, pick_bd(), float(rng.uniform(18_000, 60_000)), "6400", "1000",
                            "Travel reimbursement", approver="", planted="missing_approval"))

    # 7. Manual revenue entries booked in the last days of a quarter (possible cut-off / earnings management).
    quarter_ends = [dt.date(FISCAL_YEAR, m, d) for m, d in [(3, 31), (6, 30), (9, 30), (12, 31)]]
    for qe in quarter_ends + quarter_ends[2:]:
        day = next(d for d in reversed(BUSINESS_DAYS) if d <= qe)
        rows.append(_manual(rng, day, float(rng.uniform(40_000, 150_000)), "1200", "4000",
                            "Revenue adjustment", planted="period_end_revenue"))

    # 8. Duplicate vendor payments: same vendor and amount, invoice number keyed slightly differently.
    payments = [r for r in routine
                if r["description"] == "AP payment run" and r["posted_at"].month < 12]
    variants = [
        lambda s: s.replace("-", ""), lambda s: s.lower(), lambda s: s.replace("-", "-0"),
        lambda s: s + " ", lambda s: s.replace("-", " "), lambda s: s,
    ]
    for k, idx in enumerate(rng.choice(len(payments), size=10, replace=False)):
        dup = dict(payments[idx])
        dup["posted_at"] = dup["posted_at"] + dt.timedelta(days=int(rng.integers(1, 21)))
        dup["invoice_number"] = variants[k % len(variants)](dup["invoice_number"])
        dup["_planted"] = "duplicate_payment"
        rows.append(dup)

    return rows


def generate(seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    routine = _routine_entries(rng)
    df = pd.DataFrame(routine + _planted_entries(rng, routine))
    df = df.sort_values("posted_at", kind="stable").reset_index(drop=True)
    df.insert(0, "je_id", [f"JE-{FISCAL_YEAR}-{i:06d}" for i in range(1, len(df) + 1)])
    df.insert(2, "period", df["posted_at"].dt.strftime("%Y-%m"))
    df.insert(df.columns.get_loc("credit_account"), "debit_account_name", df["debit_account"].map(CHART_OF_ACCOUNTS))
    df.insert(df.columns.get_loc("amount"), "credit_account_name", df["credit_account"].map(CHART_OF_ACCOUNTS))

    key = (df.loc[df["_planted"] != "", ["je_id", "_planted"]]
             .rename(columns={"_planted": "planted_anomalies"}))
    ledger = df.drop(columns="_planted")
    ledger["posted_at"] = ledger["posted_at"].dt.strftime("%Y-%m-%d %H:%M:%S")
    return ledger, key


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    ledger, key = generate()
    ledger.to_csv(DATA_DIR / "sample_general_ledger.csv", index=False)
    key.to_csv(DATA_DIR / "anomaly_key.csv", index=False)
    print(f"Wrote {len(ledger):,} journal entries ({len(key)} planted anomalies) to {DATA_DIR}")


if __name__ == "__main__":
    main()
