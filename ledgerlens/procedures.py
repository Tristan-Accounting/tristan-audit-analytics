"""Journal entry testing procedures.

Each test takes a prepared ledger and returns a boolean Series (True = exception),
so results can be combined into a single risk score per entry.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

import pandas as pd

from .config import DEFAULT_PARAMS, HOLIDAYS

REQUIRED_COLUMNS = ["je_id", "posted_at", "amount", "created_by"]
OPTIONAL_COLUMNS = ["source", "approved_by", "debit_account", "credit_account",
                    "description", "vendor", "invoice_number"]


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalise a ledger extract so every test can rely on its columns."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Ledger is missing required column(s): {', '.join(missing)}")
    out = df.copy()
    for col in OPTIONAL_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    text_cols = ["je_id", "created_by"] + OPTIONAL_COLUMNS
    out[text_cols] = out[text_cols].fillna("").astype(str).apply(lambda s: s.str.strip())
    out["source"] = out["source"].replace("", "Manual")  # unknown source: treat as manual (higher risk)
    out["posted_at"] = pd.to_datetime(out["posted_at"], errors="coerce")
    out["amount"] = pd.to_numeric(out["amount"], errors="coerce")
    bad = out["posted_at"].isna() | out["amount"].isna()
    if bad.any():
        raise ValueError(f"{int(bad.sum())} row(s) have an unreadable posted_at date or amount")
    return out


def _manual(df: pd.DataFrame) -> pd.Series:
    return df["source"].str.lower().eq("manual")


# --- Individual tests -------------------------------------------------------

def weekend_or_holiday(df: pd.DataFrame, holidays=HOLIDAYS, **_) -> pd.Series:
    dates = df["posted_at"].dt.date
    return _manual(df) & ((df["posted_at"].dt.day_of_week >= 5) | dates.isin(holidays))


def after_hours(df: pd.DataFrame, business_hours=DEFAULT_PARAMS["business_hours"], **_) -> pd.Series:
    start, end = business_hours
    hour = df["posted_at"].dt.hour
    return _manual(df) & ((hour < start) | (hour >= end))


def round_amount(df: pd.DataFrame, round_multiple=DEFAULT_PARAMS["round_multiple"], **_) -> pd.Series:
    cents = (df["amount"].abs() * 100).round().astype("int64")
    return (df["amount"].abs() >= round_multiple) & (cents % int(round_multiple * 100) == 0)


def just_below_threshold(df: pd.DataFrame, approval_threshold=DEFAULT_PARAMS["approval_threshold"],
                         below_threshold_band=DEFAULT_PARAMS["below_threshold_band"], **_) -> pd.Series:
    low = approval_threshold * (1 - below_threshold_band)
    amt = df["amount"].abs()
    return _manual(df) & (amt >= low) & (amt < approval_threshold)


def self_approved(df: pd.DataFrame, **_) -> pd.Series:
    approver = df["approved_by"].str.lower()
    return approver.ne("") & approver.eq(df["created_by"].str.lower())


def missing_approval(df: pd.DataFrame, approval_threshold=DEFAULT_PARAMS["approval_threshold"], **_) -> pd.Series:
    return _manual(df) & (df["amount"].abs() >= approval_threshold) & df["approved_by"].eq("")


def period_end_revenue(df: pd.DataFrame, period_end_days=DEFAULT_PARAMS["period_end_days"], **_) -> pd.Series:
    posted = df["posted_at"].dt.normalize()
    quarter_end = posted + pd.offsets.QuarterEnd(0)
    near_end = (quarter_end - posted).dt.days < period_end_days
    hits_revenue = df["credit_account"].str.startswith("4") | df["debit_account"].str.startswith("4")
    return _manual(df) & hits_revenue & near_end


def _normalise_invoice(s: str) -> str:
    s = re.sub(r"[^0-9A-Z]", "", s.upper())
    return re.sub(r"^([A-Z]*)0+(?=\d)", r"\1", s)  # INV-012345 and INV12345 are the same invoice


def duplicate_payment_pairs(df: pd.DataFrame,
                            duplicate_window_days=DEFAULT_PARAMS["duplicate_window_days"], **_) -> pd.DataFrame:
    """Pairs of entries to the same vendor, for the same amount and posting type, within the window.

    match_type is "Same invoice" when the invoice numbers match after normalisation
    (case, spaces, dashes, leading zeros), otherwise "Different invoice".
    """
    cols = ["je_id", "posted_at", "vendor", "amount", "invoice_number", "debit_account", "credit_account"]
    v = df.loc[df["vendor"].ne(""), cols].sort_values("posted_at")
    pairs = []
    for _, grp in v.groupby(["vendor", "amount", "debit_account", "credit_account"], sort=False):
        if len(grp) < 2:
            continue
        recs = grp.to_dict("records")
        for i in range(1, len(recs)):
            first, dup = recs[i - 1], recs[i]
            days = (dup["posted_at"] - first["posted_at"]).days
            if days > duplicate_window_days:
                continue
            same_inv = _normalise_invoice(first["invoice_number"]) == _normalise_invoice(dup["invoice_number"])
            pairs.append({
                "original_je": first["je_id"], "duplicate_je": dup["je_id"], "vendor": dup["vendor"],
                "amount": dup["amount"], "original_invoice": first["invoice_number"],
                "duplicate_invoice": dup["invoice_number"], "days_apart": days,
                "match_type": "Same invoice" if same_inv else "Different invoice",
            })
    return pd.DataFrame(pairs, columns=["original_je", "duplicate_je", "vendor", "amount", "original_invoice",
                                        "duplicate_invoice", "days_apart", "match_type"])


def duplicate_payment(df: pd.DataFrame, **params) -> pd.Series:
    pairs = duplicate_payment_pairs(df, **params)
    return df["je_id"].isin(pairs["duplicate_je"])


# --- Registry and scoring ---------------------------------------------------

@dataclass(frozen=True)
class Test:
    key: str
    name: str
    weight: int
    func: Callable[..., pd.Series]
    rationale: str


TESTS: list[Test] = [
    Test("weekend_holiday", "Weekend / holiday posting", 2, weekend_or_holiday,
         "Manual entries posted when the office is closed bypass normal review and are a classic "
         "fraud-risk characteristic."),
    Test("after_hours", "After-hours posting", 2, after_hours,
         "Manual entries posted late at night, when fewer people are watching."),
    Test("round_amount", "Round-dollar amount", 1, round_amount,
         "Estimates and made-up numbers tend to be round. Real invoices rarely are."),
    Test("just_below_threshold", "Just below approval limit", 3, just_below_threshold,
         "Entries sitting just under the approval limit can mean someone is splitting transactions "
         "to avoid review."),
    Test("self_approved", "Self-approved", 3, self_approved,
         "The preparer and approver are the same person, so segregation of duties failed."),
    Test("missing_approval", "Missing required approval", 3, missing_approval,
         "Manual entries over the approval limit with no approver recorded mean the control didn't work."),
    Test("period_end_revenue", "Period-end manual revenue", 3, period_end_revenue,
         "Manual revenue entries at quarter end are a common way to manage earnings or shift cut-off."),
    Test("duplicate_payment", "Possible duplicate payment", 3, duplicate_payment,
         "Same vendor and amount within a short window, often with the invoice number keyed differently."),
]
TESTS_BY_KEY = {t.key: t for t in TESTS}


def risk_level(score: int) -> str:
    if score >= 5:
        return "High"
    if score >= 3:
        return "Medium"
    if score >= 1:
        return "Low"
    return "None"


def run_all(df: pd.DataFrame, **params) -> pd.DataFrame:
    """Run every test and return the ledger with one flag column per test plus a risk score."""
    out = df.copy()
    for t in TESTS:
        out[f"flag_{t.key}"] = t.func(out, **params).astype(bool)
    flag_cols = [f"flag_{t.key}" for t in TESTS]
    weights = pd.Series({f"flag_{t.key}": t.weight for t in TESTS})
    out["risk_score"] = (out[flag_cols].astype(int) * weights).sum(axis=1).astype(int)
    out["risk_level"] = out["risk_score"].map(risk_level)
    out["exceptions"] = out[flag_cols].apply(
        lambda r: "; ".join(TESTS_BY_KEY[c[5:]].name for c in flag_cols if r[c]), axis=1)
    return out
