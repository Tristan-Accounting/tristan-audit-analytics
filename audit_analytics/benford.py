"""Benford's Law first-digit test.

In naturally occurring financial data the leading digit is 1 about 30% of the time and 9
under 5% of the time. Big deviations can point to fabricated or manipulated amounts.
Conformity uses Mark Nigrini's Mean Absolute Deviation (MAD) thresholds for first digits.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

DIGITS = np.arange(1, 10)
EXPECTED = np.log10(1 + 1 / DIGITS)

# Nigrini (2012), first-digit MAD conformity ranges.
MAD_THRESHOLDS = [(0.006, "Close conformity"), (0.012, "Acceptable conformity"),
                  (0.015, "Marginal conformity"), (np.inf, "Nonconformity")]


@dataclass
class BenfordResult:
    table: pd.DataFrame
    n: int
    mad: float
    conformity: str
    chi_square: float


def first_digits(amounts: pd.Series) -> pd.Series:
    """Leading digit of each amount. Amounts under $10 are excluded, as Nigrini recommends."""
    a = pd.to_numeric(amounts, errors="coerce").abs()
    a = a[a >= 10]
    return a.map(lambda x: int(f"{x:.2f}"[0])).astype(int)


def conformity_label(mad: float) -> str:
    return next(label for limit, label in MAD_THRESHOLDS if mad <= limit)


def analyze(amounts: pd.Series) -> BenfordResult:
    d = first_digits(amounts)
    n = len(d)
    counts = d.value_counts().reindex(DIGITS, fill_value=0).to_numpy()
    actual = counts / n if n else np.zeros(9)
    diff = actual - EXPECTED
    # Z-statistic with continuity correction (Nigrini).
    with np.errstate(divide="ignore", invalid="ignore"):
        z = (np.abs(diff) - 1 / (2 * n)) / np.sqrt(EXPECTED * (1 - EXPECTED) / n) if n else np.zeros(9)
    z = np.clip(z, 0, None)
    table = pd.DataFrame({
        "digit": DIGITS, "count": counts, "actual_pct": actual, "expected_pct": EXPECTED,
        "difference": diff, "z_stat": z, "significant": z > 1.96,
    })
    mad = float(np.mean(np.abs(diff))) if n else 0.0
    chi = float(np.sum((counts - n * EXPECTED) ** 2 / (n * EXPECTED))) if n else 0.0
    return BenfordResult(table, n, mad, conformity_label(mad), chi)


def chi_square_p_value(chi: float) -> float:
    """Upper-tail p-value for a chi-square statistic with 8 degrees of freedom (closed form)."""
    half = chi / 2
    return float(math.exp(-half) * sum(half ** i / math.factorial(i) for i in range(4)))


def by_group(df: pd.DataFrame, group_col: str, min_n: int = 50) -> pd.DataFrame:
    """Benford test per group (for example per user), most suspicious first.

    MAD thresholds are designed for large populations; for a few hundred entries random noise
    alone pushes MAD past them. So groups are ranked by the chi-square p-value, which accounts
    for sample size: a p-value under 0.01 means the pattern is unlikely to be chance.
    """
    rows = []
    for name, grp in df.groupby(group_col):
        res = analyze(grp["amount"])
        if res.n >= min_n:
            top = res.table.loc[res.table["difference"].idxmax()]
            rows.append({group_col: name, "entries": res.n, "mad": res.mad,
                         "chi_square": res.chi_square, "p_value": chi_square_p_value(res.chi_square),
                         "most_overused_digit": int(top["digit"]),
                         "overuse_pct_points": float(top["difference"]) * 100})
    cols = [group_col, "entries", "mad", "chi_square", "p_value", "most_overused_digit", "overuse_pct_points"]
    return pd.DataFrame(rows, columns=cols).sort_values("p_value", ignore_index=True)
