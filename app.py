"""Tristan Audit Analytics: journal entry testing site.  Run:  streamlit run app.py"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from audit_analytics import benford, procedures, sampling, ui
from audit_analytics.config import DEFAULT_PARAMS

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
REPO_URL = "https://github.com/Tristan-Accounting/ledgerlens"

st.set_page_config(page_title="Tristan Audit Analytics | Journal Entry Testing",
                   page_icon=":material/fact_check:", layout="wide", initial_sidebar_state="collapsed")
st.html(ui.CSS)


@st.cache_data
def load(file) -> pd.DataFrame:
    return procedures.prepare(pd.read_csv(file))


@st.cache_data
def score(df: pd.DataFrame, params: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    return procedures.run_all(df, **params), procedures.duplicate_payment_pairs(df, **params)


TEMPLATE_CSV = ("je_id,posted_at,amount,created_by,source,approved_by,debit_account,credit_account,"
                "description,vendor,invoice_number\n"
                "JE-0001,2025-03-31 14:05:00,1250.00,jsmith,Manual,,6300,1000,Consulting services,Acme Co,INV-1001\n")

TABLE_COLS = ["je_id", "posted_at", "source", "created_by", "approved_by", "debit_account_name",
              "credit_account_name", "amount", "description", "vendor"]
LABELS = {"je_id": "Entry", "posted_at": "Posted", "source": "Source", "created_by": "Prepared by",
          "approved_by": "Approved by", "debit_account_name": "Debit", "credit_account_name": "Credit",
          "description": "Description", "vendor": "Vendor", "risk_level": "Risk", "exceptions": "Why flagged",
          "hits": "Times picked", "individually_significant": "Too large to skip"}


def show_table(df: pd.DataFrame, extra: list[str] | None = None) -> None:
    cols = [c for c in (extra or []) + TABLE_COLS if c in df.columns]
    config = {c: st.column_config.Column(label) for c, label in LABELS.items()}
    config["amount"] = st.column_config.NumberColumn("Amount", format="$%.2f")
    config["posted_at"] = st.column_config.DatetimeColumn("Posted", format="YYYY-MM-DD HH:mm")
    st.dataframe(df[cols], hide_index=True, width="stretch", column_config=config)


def plot(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", theme=None, config=ui.CHART_CONFIG)


# --- Top bar -------------------------------------------------------------------
bar_brand, bar_data, bar_settings = st.columns([4, 2.2, 1.8], vertical_alignment="center")
bar_brand.html(ui.brand())

with bar_data.popover("Use your own data", icon=":material/upload_file:", width="stretch"):
    st.markdown("**1.** Download the template and paste your entries into it.")
    st.download_button("Download template", TEMPLATE_CSV, "ledger_template.csv", "text/csv",
                       icon=":material/download:", width="stretch")
    st.markdown("**2.** Upload it here.")
    upload = st.file_uploader("Upload your ledger", type="csv", label_visibility="collapsed")
    st.caption("This is a public demo, so never upload real client data.")

with bar_settings.popover("Test settings", icon=":material/tune:", width="stretch"):
    st.caption("Optional. These match a typical company's policy, and every result updates when you change them.")
    threshold = st.number_input("Approval limit ($)", 1_000, 1_000_000,
                                int(DEFAULT_PARAMS["approval_threshold"]), step=1_000)
    band = st.slider("Count as 'just under the limit' within", 1, 20, int(DEFAULT_PARAMS["below_threshold_band"] * 100),
                     format="%d%%") / 100
    round_multiple = st.selectbox("Count as a round number if a multiple of", [100, 500, 1_000, 5_000, 10_000], index=2,
                                  format_func=ui.money)
    hours = st.slider("Business hours", 0, 24, DEFAULT_PARAMS["business_hours"])
    period_days = st.slider("Last days of a quarter to check", 1, 10, DEFAULT_PARAMS["period_end_days"])
    dup_window = st.slider("Days apart to count as a double payment", 1, 90, DEFAULT_PARAMS["duplicate_window_days"])

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
preparers = benford.by_group(scored, "created_by")

# --- Hero ----------------------------------------------------------------------
summary = [("Population tested", "100%"),
           ("Value tested", ui.compact_money(scored["amount"].abs().sum())),
           ("High-risk entries", f"{(scored['risk_level'] == 'High').sum():,}")]
key_path = DATA_DIR / "anomaly_key.csv"
if upload is None and key_path.exists():
    key = pd.read_csv(key_path)
    summary.append(("Planted anomalies caught", f"{key['je_id'].isin(flagged['je_id']).sum()} / {len(key)}"))
    source_note = "Shown here on a fictional company's FY2025 ledger."
else:
    summary.append(("Value flagged", ui.compact_money(flagged["amount"].abs().sum())))
    source_note = f"Shown here on {upload.name}."
st.html(ui.hero(len(flagged), len(scored), source_note, summary))
st.html(ui.steps([("Add a ledger", "Use the sample already loaded, or upload your own with the button at the top."),
                  ("Read the summary", "See which checks failed, who was involved and which entries to review first."),
                  ("Follow up", "Each check says what to do next. Download the list and work through it.")]))

tab_find, tab_tests, tab_benford, tab_dups, tab_mus, tab_method = st.tabs(
    ["Summary", "The 8 checks", "Number patterns", "Double payments", "Pick a sample", "How it works"])

# --- Findings ------------------------------------------------------------------
with tab_find:
    st.html(ui.heading("Results", "What the checks found",
                       "Eight checks ran on every entry. Each card shows how many entries failed, "
                       "and names anyone responsible for most of them."))
    cards = []
    for t in procedures.TESTS:
        hits = scored[scored[f"flag_{t.key}"]]
        if hits.empty:
            detail = "No exceptions noted."
        else:
            top = hits["created_by"].value_counts()
            value = ui.money(hits["amount"].abs().sum())
            if len(hits) >= 3 and top.iloc[0] / len(hits) >= 0.6:
                detail = f"<code>{ui.esc(top.index[0])}</code> accounts for {top.iloc[0]} of {len(hits)}. Total {value}."
            else:
                detail = f"Spread across {len(top)} people. Total {value}."
        cards.append({"name": t.name, "count": len(hits), "detail": detail, "weight": t.weight})
    cards.sort(key=lambda c: (-(c["count"] > 0), -c["weight"], -c["count"]))
    st.html(ui.test_cards(cards))

    st.html(ui.heading("Priorities", "Where to start",
                       "These are the riskiest entries, and the more checks an entry fails, the higher it ranks. "
                       "A flag doesn't prove anything is wrong. It tells you what to look at first.",
                       space=True))
    st.html(ui.priority_table(flagged.head(10)))
    st.write("")
    st.download_button("Download the full review list",
                       flagged.drop(columns=[c for c in flagged if c.startswith("flag_")]).to_csv(index=False),
                       "audit_exceptions.csv", "text/csv", icon=":material/download:")

    st.html(ui.heading("Patterns", "When and who", space=True))
    left, right = st.columns(2, gap="large")
    with left:
        st.html('<div class="ll-eyebrow" style="color:#5C6A67">Flagged entries by month</div>')
        monthly = flagged.assign(month=flagged["posted_at"].dt.to_period("M"))
        monthly = monthly.groupby(["month", "risk_level"]).size().unstack(fill_value=0).sort_index()
        labels = [m.strftime("%b") for m in monthly.index]
        fig = go.Figure([go.Bar(x=labels, y=monthly[lvl], name=lvl,
                                marker=dict(color=ui.RISK[lvl], line=dict(color="#F7F5EF", width=2)),
                                hovertemplate=f"%{{x}}: %{{y}} {lvl.lower()}-risk<extra></extra>")
                         for lvl in ["High", "Medium", "Low"] if lvl in monthly])
        fig.update_layout(barmode="stack")
        plot(ui.style_chart(fig))
    with right:
        st.html('<div class="ll-eyebrow" style="color:#5C6A67">Flagged entries by preparer</div>')
        who = flagged["created_by"].value_counts().head(8).sort_values()
        fig = go.Figure(go.Bar(x=who.values, y=who.index, orientation="h", text=who.values,
                               textposition="outside", cliponaxis=False,
                               marker=dict(color=ui.PINE, cornerradius=4),
                               hovertemplate="%{y}: %{x} flagged<extra></extra>"))
        fig = ui.style_chart(fig)
        fig.update_xaxes(visible=False, range=[0, who.max() * 1.15 if len(who) else 1])
        fig.update_yaxes(showgrid=False, tickfont=dict(family="IBM Plex Mono, monospace", color=ui.INK))
        plot(fig)

# --- The 8 checks ---------------------------------------------------------------
with tab_tests:
    st.html(ui.heading("The 8 checks", "See what each check found", "Pick a check to see why it matters, what to do next and every entry it flagged."))
    names = {t.name: t for t in procedures.TESTS}
    choice = st.pills("Check", list(names), default=procedures.TESTS[3].name, label_visibility="collapsed")
    t = names[choice or procedures.TESTS[3].name]
    hits = scored[scored[f"flag_{t.key}"]].sort_values("amount", ascending=False)
    st.html(ui.note(f"<b>Why it matters:</b> {ui.esc(t.rationale)}<br>"
                    f"<b>What to do next:</b> {ui.esc(procedures.NEXT_STEPS[t.key])}"))
    st.html(ui.stats([("Entries flagged", f"{len(hits):,}"), ("Total value", ui.money(hits["amount"].abs().sum())),
                      ("People involved", str(hits["created_by"].nunique())), ("Risk weight (1 to 3)", str(t.weight))]))
    if hits.empty:
        st.html(ui.note("Nothing failed this check."))
    else:
        show_table(hits, extra=["risk_level", "exceptions"])

# --- Benford -------------------------------------------------------------------
with tab_benford:
    st.html(ui.heading("Benford's Law", "Do the numbers look natural?",
                       "In real financial data, about 30% of amounts start with a 1 and under 5% start with a 9. "
                       "Made-up numbers usually break that pattern."))
    overall = benford.analyze(scored["amount"])
    verdict = ("<b>Overall, the numbers look natural.</b>" if overall.mad <= 0.012
               else "<b>Overall, the numbers don't follow the expected pattern.</b>")
    if not preparers.empty and preparers.at[0, "p_value"] < 0.01:
        p = preparers.iloc[0]
        p_text = "p < 0.0001" if p["p_value"] < 0.0001 else f"p = {p['p_value']:.4f}"
        verdict += (f" But <code>{ui.esc(p['created_by'])}</code> stands out: too many of their amounts start "
                    f"with {int(p['most_overused_digit'])}, {p['overuse_pct_points']:.1f} percentage points above "
                    f"normal. That's very unlikely to be chance ({ui.esc(p_text)}).")
    st.html(ui.note(verdict))
    options = ["All entries"] + sorted(scored["created_by"].unique())
    pick = st.selectbox("Show entries from", options)
    pop = scored if pick == "All entries" else scored[scored["created_by"] == pick]
    res = benford.analyze(pop["amount"])
    tb = res.table
    fig = go.Figure()
    fig.add_bar(x=tb["digit"], y=tb["actual_pct"] * 100, name="Actual",
                marker=dict(color=[ui.RISK["High"] if s else ui.PINE for s in tb["significant"]], cornerradius=4),
                hovertemplate="Digit %{x}: %{y:.1f}% actual<extra></extra>")
    fig.add_scatter(x=tb["digit"], y=tb["expected_pct"] * 100, name="Expected", mode="lines+markers",
                    line=dict(color=ui.BRASS, width=2), marker=dict(size=9, line=dict(color="#F7F5EF", width=2)),
                    hovertemplate="Digit %{x}: %{y:.1f}% expected<extra></extra>")
    fig = ui.style_chart(fig, 360)
    fig.update_xaxes(dtick=1, title="First digit of the amount")
    fig.update_yaxes(title="Share of amounts", ticksuffix="%")
    plot(fig)
    st.caption("Bars should follow the gold line. A dark red bar means that digit is significantly off.")

    with st.expander("Technical details for auditors"):
        st.html(ui.stats([("Amounts tested (≥ $10)", f"{res.n:,}"), ("MAD", f"{res.mad:.4f}"),
                          ("Conformity (Nigrini)", res.conformity.replace(" conformity", "")),
                          ("Chi-square p-value", f"{benford.chi_square_p_value(res.chi_square):.4f}")]))
        st.caption("Dark red bars have z > 1.96. MAD thresholds are built for large populations, so individual "
                   "preparers are ranked by chi-square p-value. Under 0.01 is unlikely to be chance.")
        st.dataframe(preparers, hide_index=True, width="stretch", column_config={
            "created_by": st.column_config.Column("Prepared by"), "entries": st.column_config.NumberColumn("Entries"),
            "mad": st.column_config.NumberColumn("MAD", format="%.4f"),
            "chi_square": st.column_config.NumberColumn("Chi-square", format="%.1f"),
            "p_value": st.column_config.NumberColumn("p-value", format="%.4f"),
            "most_overused_digit": st.column_config.NumberColumn("Most overused digit"),
            "overuse_pct_points": st.column_config.NumberColumn("Overuse (pct pts)", format="%.1f")})

# --- Duplicates ----------------------------------------------------------------
with tab_dups:
    st.html(ui.heading("Duplicate payments", "Was anyone paid twice?",
                       f"These pairs have the same vendor and amount within {dup_window} days. Invoice numbers are "
                       "matched even when they're typed differently, which is how double payments usually slip through."))
    st.html(ui.note(f"<b>What to do next:</b> {ui.esc(procedures.NEXT_STEPS['duplicate_payment'])}"))
    st.html(ui.stats([("Possible double payments", str(len(dup_pairs))),
                      ("Same invoice number", str(int((dup_pairs["match_type"] == "Same invoice").sum()))),
                      ("Possible overpayment", ui.money(dup_pairs["amount"].sum()))]))
    st.dataframe(dup_pairs, hide_index=True, width="stretch", column_config={
        "original_je": st.column_config.Column("Original entry"), "duplicate_je": st.column_config.Column("Duplicate entry"),
        "vendor": st.column_config.Column("Vendor"), "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
        "original_invoice": st.column_config.Column("Original invoice"),
        "duplicate_invoice": st.column_config.Column("Duplicate invoice"),
        "days_apart": st.column_config.NumberColumn("Days apart"), "match_type": st.column_config.Column("Match")})

# --- Sampling ------------------------------------------------------------------
with tab_mus:
    st.html(ui.heading("Monetary Unit Sampling", "Which items should we test?",
                       "You can't check every item by hand, so this picks a fair, statistically sound sample. "
                       "Bigger amounts are more likely to be picked."))
    accounts = scored[["debit_account", "debit_account_name"]].drop_duplicates().sort_values("debit_account")
    opts = ["All entries"] + [f"{a} - {n}" if n else a for a, n in accounts.itertuples(index=False) if a]
    c = st.columns(2)
    acct = c[0].selectbox("Which account are you testing?", opts, index=opts.index("2000 - Accounts Payable")
                          if "2000 - Accounts Payable" in opts else 0)
    conf = c[1].selectbox("How confident do you need to be?", [0.80, 0.90, 0.95, 0.99], index=2,
                          format_func=lambda x: f"{x:.0%}")
    population = scored if acct == "All entries" else scored[scored["debit_account"] == acct.split(" - ")[0]]
    pv = float(population["amount"].abs().sum())
    with st.expander("Technical settings for auditors"):
        a, b = st.columns(2)
        tolerable = a.number_input("Tolerable misstatement ($)", 1_000, None, max(1_000, int(pv * 0.05)), step=1_000,
                                   help="The most error you could accept in this account. Defaults to 5% of its value.")
        expected = b.number_input("Expected misstatement ($)", 0, None, 0, step=1_000,
                                  help="How much error you expect to find.")
    try:
        if pv <= 0:
            raise ValueError("This account has no amounts to sample.")
        n = min(sampling.sample_size(pv, tolerable, conf, expected), len(population))
    except ValueError as e:
        st.error(str(e))
    else:
        sample = sampling.select(population, n)
        st.html(ui.stats([("Items to test", f"{len(sample.selections):,}"), ("Account value", ui.money(pv)),
                          ("One pick about every", ui.money(sample.interval)),
                          ("Too large to skip", str(int(sample.selections["individually_significant"].sum())))]))
        st.html(f'<p class="ll-formula">n = (population × {sampling.CONFIDENCE_FACTORS[conf]:.2f}) ÷ (tolerable − '
                f'expected × {sampling.EXPANSION_FACTORS[conf]}) = {n} · random start {ui.money(sample.random_start)}</p>')
        show_table(sample.selections, extra=["hits", "individually_significant"])
        st.write("")
        st.download_button("Download the sample", sample.selections.to_csv(index=False),
                           "audit_sample.csv", "text/csv", icon=":material/download:")

# --- Methodology ---------------------------------------------------------------
with tab_method:
    st.html(ui.heading("Methodology", "How it works", "The full method, with the audit standards behind each check."))
    st.markdown((ROOT / "METHODOLOGY.md").read_text(encoding="utf-8"))

st.html(ui.footer(REPO_URL))
