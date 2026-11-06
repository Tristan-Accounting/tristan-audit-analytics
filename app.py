"""LedgerLens: journal entry testing dashboard.  Run:  streamlit run app.py"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ledgerlens import benford, procedures, sampling
from ledgerlens.config import DEFAULT_PARAMS

DATA_DIR = Path(__file__).parent / "data"
ACCENT, MUTED, RISK_COLORS = "#1f5f8b", "#9aa5b1", {"High": "#c0392b", "Medium": "#e67e22", "Low": "#f1c40f"}

st.set_page_config(page_title="LedgerLens | Journal Entry Testing", page_icon="🔎", layout="wide")


@st.cache_data
def load(file) -> pd.DataFrame:
    return procedures.prepare(pd.read_csv(file))


@st.cache_data
def score(df: pd.DataFrame, params: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    return procedures.run_all(df, **params), procedures.duplicate_payment_pairs(df, **params)


def money(x: float) -> str:
    return f"${x:,.0f}"


DISPLAY_COLS = ["je_id", "posted_at", "source", "created_by", "approved_by", "debit_account_name",
                "credit_account_name", "amount", "description", "vendor"]


def show_table(df: pd.DataFrame, extra: list[str] | None = None) -> None:
    cols = [c for c in (extra or []) + DISPLAY_COLS if c in df.columns]
    st.dataframe(df[cols], hide_index=True, width="stretch",
                 column_config={"amount": st.column_config.NumberColumn(format="$%.2f"),
                                "posted_at": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm")})


# --- Sidebar: data and parameters --------------------------------------------
with st.sidebar:
    st.title("🔎 LedgerLens")
    st.caption("Audit analytics for journal entry testing")
    upload = st.file_uploader("Upload a general ledger CSV", type="csv",
                              help="Required columns: je_id, posted_at, amount, created_by. "
                                   "See the Methodology tab for the full layout.")
    st.caption("Using the built-in sample ledger (fictional company, FY2025)." if upload is None
               else f"Using **{upload.name}**")

    st.subheader("Test parameters")
    threshold = st.number_input("Approval threshold ($)", 1_000, 1_000_000,
                                int(DEFAULT_PARAMS["approval_threshold"]), step=1_000)
    band = st.slider("'Just below threshold' band", 1, 20, int(DEFAULT_PARAMS["below_threshold_band"] * 100),
                     format="%d%%") / 100
    round_multiple = st.selectbox("Round-dollar multiple", [100, 500, 1_000, 5_000, 10_000], index=2,
                                  format_func=money)
    hours = st.slider("Business hours", 0, 24, DEFAULT_PARAMS["business_hours"])
    period_days = st.slider("Period-end window (days)", 1, 10, DEFAULT_PARAMS["period_end_days"])
    dup_window = st.slider("Duplicate look-back (days)", 1, 90, DEFAULT_PARAMS["duplicate_window_days"])

params = {"approval_threshold": float(threshold), "below_threshold_band": band,
          "round_multiple": round_multiple, "business_hours": tuple(hours),
          "period_end_days": period_days, "duplicate_window_days": dup_window}

try:
    ledger = load(upload if upload is not None else DATA_DIR / "sample_general_ledger.csv")
except ValueError as e:
    st.error(f"Couldn't read that file: {e}")
    st.stop()

scored, dup_pairs = score(ledger, params)
flagged = scored[scored["risk_score"] > 0].sort_values(["risk_score", "amount"], ascending=False)

st.title("Journal Entry Testing Dashboard")
st.caption(f"{len(scored):,} entries · {scored['posted_at'].min():%b %d, %Y} to "
           f"{scored['posted_at'].max():%b %d, %Y}")

tab_overview, tab_tests, tab_benford, tab_dups, tab_mus, tab_method = st.tabs(
    ["Overview", "JE Tests", "Benford's Law", "Duplicate Payments", "MUS Sampling", "Methodology"])

# --- Overview ------------------------------------------------------------------
with tab_overview:
    c = st.columns(4)
    c[0].metric("Entries tested", f"{len(scored):,}", help=f"{money(scored['amount'].abs().sum())} total value")
    c[1].metric("Entries with exceptions", f"{len(flagged):,}",
                help=f"{len(flagged) / len(scored):.1%} of the population")
    c[2].metric("High-risk entries", f"{(scored['risk_level'] == 'High').sum():,}")
    c[3].metric("Value of flagged entries", money(flagged["amount"].abs().sum()))

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Exceptions by test")
        counts = pd.DataFrame({"test": [t.name for t in procedures.TESTS],
                               "count": [int(scored[f"flag_{t.key}"].sum()) for t in procedures.TESTS]}
                              ).sort_values("count")
        fig = go.Figure(go.Bar(x=counts["count"], y=counts["test"], orientation="h", marker_color=ACCENT,
                               text=counts["count"], textposition="outside"))
        fig.update_layout(height=340, margin=dict(l=0, r=30, t=10, b=0), xaxis_title="Entries flagged")
        st.plotly_chart(fig, width="stretch")
    with right:
        st.subheader("Flagged entries by month")
        monthly = flagged.assign(month=flagged["posted_at"].dt.to_period("M").astype(str))
        monthly = monthly.groupby(["month", "risk_level"]).size().unstack(fill_value=0)
        fig = go.Figure([go.Bar(x=monthly.index, y=monthly[lvl], name=lvl, marker_color=RISK_COLORS[lvl])
                         for lvl in ["High", "Medium", "Low"] if lvl in monthly])
        fig.update_layout(barmode="stack", height=340, margin=dict(l=0, r=0, t=10, b=0),
                          legend=dict(orientation="h", y=1.1), yaxis_title="Entries")
        st.plotly_chart(fig, width="stretch")

    st.subheader("Highest-risk entries")
    st.caption("Risk score = sum of test weights (1-3 each). High ≥ 5, Medium 3-4, Low 1-2. "
               "These are the entries to pull support for first.")
    show_table(flagged.head(25), extra=["risk_level", "risk_score", "exceptions"])
    st.download_button("Download all exceptions (CSV)",
                       flagged.drop(columns=[c for c in flagged if c.startswith("flag_")]).to_csv(index=False),
                       "ledgerlens_exceptions.csv", "text/csv")

    key_path = DATA_DIR / "anomaly_key.csv"
    if upload is None and key_path.exists():
        with st.expander("Validation: did the tests catch the planted anomalies?"):
            key = pd.read_csv(key_path)
            caught = key["je_id"].isin(flagged["je_id"])
            false_pos = (~flagged["je_id"].isin(key["je_id"])).sum()
            st.write(f"The sample ledger has **{len(key)}** anomalies planted on purpose. LedgerLens flagged "
                     f"**{caught.sum()}/{len(key)}** of them, plus **{false_pos}** routine entries "
                     f"(false positives) at the current settings.")

# --- JE tests ------------------------------------------------------------------
with tab_tests:
    names = {t.name: t for t in procedures.TESTS}
    choice = st.radio("Test", list(names), horizontal=True)
    t = names[choice]
    hits = scored[scored[f"flag_{t.key}"]].sort_values("amount", ascending=False)
    st.info(f"**Why it matters:** {t.rationale}  \n**Weight in risk score:** {t.weight}")
    c = st.columns(3)
    c[0].metric("Exceptions", f"{len(hits):,}")
    c[1].metric("Value", money(hits["amount"].abs().sum()))
    c[2].metric("Users involved", hits["created_by"].nunique())
    if hits.empty:
        st.success("No exceptions noted.")
    else:
        show_table(hits, extra=["risk_level", "exceptions"])
        by_user = hits.groupby("created_by").agg(entries=("je_id", "count"), value=("amount", "sum"))
        st.caption("By preparer: one person accounting for most exceptions is worth asking about.")
        st.dataframe(by_user.sort_values("entries", ascending=False), width="stretch",
                     column_config={"value": st.column_config.NumberColumn(format="$%.2f")})

# --- Benford -------------------------------------------------------------------
with tab_benford:
    users = ["All entries"] + sorted(scored["created_by"].unique())
    who = st.selectbox("Population", users)
    pop = scored if who == "All entries" else scored[scored["created_by"] == who]
    res = benford.analyze(pop["amount"])
    c = st.columns(4)
    c[0].metric("Amounts tested (≥ $10)", f"{res.n:,}")
    c[1].metric("MAD", f"{res.mad:.4f}")
    c[2].metric("Conformity", res.conformity.replace(" conformity", ""))
    c[3].metric("Chi-square p-value", f"{benford.chi_square_p_value(res.chi_square):.4f}")
    tb = res.table
    fig = go.Figure()
    fig.add_bar(x=tb["digit"], y=tb["actual_pct"] * 100, name="Actual",
                marker_color=[RISK_COLORS["High"] if s else ACCENT for s in tb["significant"]])
    fig.add_scatter(x=tb["digit"], y=tb["expected_pct"] * 100, name="Benford expected",
                    mode="lines+markers", line=dict(color=MUTED, width=3))
    fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(dtick=1, title="First digit"),
                      yaxis_title="% of amounts", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, width="stretch")
    st.caption("Red bars are digits where the gap is statistically significant (z > 1.96). "
               "MAD thresholds (Nigrini): ≤0.006 close, ≤0.012 acceptable, ≤0.015 marginal. "
               "MAD needs large populations, so for one user's entries go by the p-value.")

    st.subheader("Benford by preparer")
    st.caption("Ranked by chi-square p-value. Under 0.01, the digit pattern is unlikely to be chance.")
    st.dataframe(benford.by_group(scored, "created_by"), hide_index=True, width="stretch",
                 column_config={"mad": st.column_config.NumberColumn(format="%.4f"),
                                "chi_square": st.column_config.NumberColumn(format="%.1f"),
                                "p_value": st.column_config.NumberColumn(format="%.4f"),
                                "overuse_pct_points": st.column_config.NumberColumn(
                                    "overuse (pct pts)", format="%.1f")})

# --- Duplicates ----------------------------------------------------------------
with tab_dups:
    c = st.columns(3)
    c[0].metric("Possible duplicates", len(dup_pairs))
    c[1].metric("Same invoice (after normalising)", int((dup_pairs["match_type"] == "Same invoice").sum()))
    c[2].metric("Potential overpayment", money(dup_pairs["amount"].sum()))
    st.caption(f"Same vendor, same amount, same posting accounts, within {dup_window} days. Invoice numbers "
               "are compared ignoring case, spaces, dashes and leading zeros, since that's how duplicates "
               "usually get past ERP duplicate checks.")
    st.dataframe(dup_pairs, hide_index=True, width="stretch",
                 column_config={"amount": st.column_config.NumberColumn(format="$%.2f")})

# --- MUS -----------------------------------------------------------------------
with tab_mus:
    st.caption("Select a statistical sample for substantive testing with Monetary Unit Sampling.")
    accounts = scored[["debit_account", "debit_account_name"]].drop_duplicates().sort_values("debit_account")
    opts = ["All entries"] + [f"{a} - {n}" for a, n in accounts.itertuples(index=False)]
    c = st.columns(4)
    acct = c[0].selectbox("Population (debit account)", opts, index=opts.index("2000 - Accounts Payable")
                          if "2000 - Accounts Payable" in opts else 0)
    population = scored if acct == "All entries" else scored[scored["debit_account"] == acct.split(" - ")[0]]
    pv = float(population["amount"].abs().sum())
    tolerable = c[1].number_input("Tolerable misstatement ($)", 1_000, None, max(1_000, int(pv * 0.05)),
                                  step=1_000)
    expected = c[2].number_input("Expected misstatement ($)", 0, None, 0, step=1_000)
    conf = c[3].selectbox("Confidence", [0.80, 0.90, 0.95, 0.99], index=2, format_func=lambda x: f"{x:.0%}")
    try:
        n = sampling.sample_size(pv, tolerable, conf, expected)
    except ValueError as e:
        st.error(str(e))
        st.stop()
    n = min(n, len(population))
    sample = sampling.select(population, n)
    m = st.columns(4)
    m[0].metric("Population value", money(pv))
    m[1].metric("Sample size", n)
    m[2].metric("Sampling interval", money(sample.interval))
    m[3].metric("Individually significant", int(sample.selections["individually_significant"].sum()))
    st.caption(f"n = (population × {sampling.CONFIDENCE_FACTORS[conf]:.2f}) ÷ (tolerable − expected × "
               f"{sampling.EXPANSION_FACTORS[conf]}). Random start {money(sample.random_start)}. "
               "Items ≥ the interval are always selected.")
    show_table(sample.selections, extra=["hits", "individually_significant"])
    st.download_button("Download sample (CSV)", sample.selections.to_csv(index=False),
                       "ledgerlens_mus_sample.csv", "text/csv")

# --- Methodology ---------------------------------------------------------------
with tab_method:
    st.markdown((Path(__file__).parent / "METHODOLOGY.md").read_text(encoding="utf-8"))
