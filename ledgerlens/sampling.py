"""Monetary Unit Sampling (MUS), also called probability-proportional-to-size sampling.

Every dollar in the population has an equal chance of selection, so larger items are more
likely to be picked. Any item at least as large as the sampling interval is always selected.
Sample size follows the AICPA Audit Sampling guide formula:

    n = (population value x confidence factor) / (tolerable misstatement - expected misstatement x expansion factor)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Confidence (reliability) factors for zero misstatements and expansion factors.
CONFIDENCE_FACTORS = {0.80: 1.61, 0.90: 2.31, 0.95: 3.00, 0.99: 4.61}
EXPANSION_FACTORS = {0.80: 1.3, 0.90: 1.5, 0.95: 1.6, 0.99: 1.9}


def sample_size(population_value: float, tolerable: float, confidence: float = 0.95,
                expected: float = 0.0) -> int:
    if confidence not in CONFIDENCE_FACTORS:
        raise ValueError(f"Confidence must be one of {sorted(CONFIDENCE_FACTORS)}")
    denom = tolerable - expected * EXPANSION_FACTORS[confidence]
    if tolerable <= 0 or denom <= 0:
        raise ValueError("Tolerable misstatement must exceed expected misstatement x expansion factor")
    return max(1, math.ceil(population_value * CONFIDENCE_FACTORS[confidence] / denom))


@dataclass
class MUSSample:
    selections: pd.DataFrame
    population_value: float
    sample_size: int
    interval: float
    random_start: float


def select(df: pd.DataFrame, n: int, seed: int = 42) -> MUSSample:
    """Systematic MUS selection with a random start. Items hit more than once are listed once."""
    pop = df.loc[df["amount"].abs() > 0].copy()
    pop["_abs"] = pop["amount"].abs()
    total = float(pop["_abs"].sum())
    interval = total / n
    start = float(np.random.default_rng(seed).uniform(0, interval))
    points = start + interval * np.arange(n)
    cum = pop["_abs"].cumsum().to_numpy()
    idx = np.searchsorted(cum, points, side="left")
    hits = pd.Series(idx).value_counts()
    sel = pop.iloc[hits.index.sort_values()].copy()
    sel["hits"] = hits.sort_index().to_numpy()
    sel["individually_significant"] = sel["_abs"] >= interval
    return MUSSample(sel.drop(columns="_abs"), total, n, interval, start)
