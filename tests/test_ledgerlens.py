"""Checks that every planted anomaly is caught and the statistics behave as expected."""
import pandas as pd
import pytest

from ledgerlens import benford, procedures, sampling
from ledgerlens.generate_data import generate


@pytest.fixture(scope="module")
def results():
    ledger, key = generate()
    scored = procedures.run_all(procedures.prepare(ledger))
    return scored, key


def test_every_planted_anomaly_is_detected_by_the_right_test(results):
    scored, key = results
    flagged = scored.set_index("je_id")
    misses = []
    for je_id, tags in key.itertuples(index=False):
        for tag in tags.split(";"):
            if not flagged.at[je_id, f"flag_{tag}"]:
                misses.append((je_id, tag))
    assert not misses, f"Planted anomalies not detected: {misses}"


def test_false_positive_rate_is_low(results):
    scored, key = results
    unplanted = scored[~scored["je_id"].isin(key["je_id"])]
    assert (unplanted["risk_score"] > 0).mean() < 0.01


def test_benford_population_conforms_but_structuring_user_does_not(results):
    scored, _ = results
    assert benford.analyze(scored["amount"]).mad <= 0.012
    users = benford.by_group(scored, "created_by").set_index("created_by")
    assert users.index[0] == "dwilson"
    assert users.at["dwilson", "p_value"] < 0.001
    assert users.at["dwilson", "most_overused_digit"] == 9
    assert (users.drop(index="dwilson")["p_value"] > 0.01).all()


def test_benford_known_values():
    assert benford.first_digits(pd.Series([123.45, 9.99, 1000, -45, 0.5])).tolist() == [1, 1, 4]
    assert benford.conformity_label(0.005) == "Close conformity"
    assert benford.conformity_label(0.02) == "Nonconformity"


def test_mus_sample_size_matches_aicpa_formula():
    # $5,000,000 population, $250,000 tolerable, 95% confidence, no expected misstatement -> 60
    assert sampling.sample_size(5_000_000, 250_000, 0.95) == 60
    # with $50,000 expected: 5,000,000 x 3.0 / (250,000 - 50,000 x 1.6) = 88.2 -> 89
    assert sampling.sample_size(5_000_000, 250_000, 0.95, 50_000) == 89


def test_mus_always_selects_items_above_the_interval():
    df = pd.DataFrame({"je_id": list("ABCDE"), "amount": [100.0, 5_000.0, 200.0, 300.0, 400.0]})
    s = sampling.select(df, n=3)
    assert "B" in s.selections["je_id"].tolist()
    assert s.selections.loc[s.selections["je_id"] == "B", "individually_significant"].item()


def test_invoice_normalisation():
    norm = procedures._normalise_invoice
    assert norm("INV-012345") == norm("inv 12345") == norm("INV12345 ")


def test_prepare_rejects_missing_columns():
    with pytest.raises(ValueError, match="amount"):
        procedures.prepare(pd.DataFrame({"je_id": ["1"], "posted_at": ["2025-01-01"], "created_by": ["x"]}))
