# 🔎 LedgerLens: Audit Analytics for Journal Entry Testing

LedgerLens tests **100% of a general ledger** for the fraud-risk characteristics that the auditing standards
(AU-C 240 / PCAOB AS 2401) ask auditors to look at. It ranks entries by risk, runs a Benford's Law analysis,
finds duplicate vendor payments and selects a Monetary Unit Sample, all in one interactive dashboard.

**[▶ Live demo](https://YOUR-APP.streamlit.app)** <!-- replace after deploying -->

![Dashboard screenshot](docs/screenshot.png) <!-- add a screenshot after deploying -->

## Why I built it

Traditional journal entry testing has auditors filter a ledger by hand in Excel, one criterion at a time.
I wanted to see how much of that work could be automated, and whether a simple, explainable scoring model
could surface the entries an experienced auditor would pick.

## Results on the sample ledger

The repo includes a synthetic FY2025 ledger for a fictional distributor: **5,111 journal entries** with
**73 anomalies planted on purpose** (see [`data/anomaly_key.csv`](data/anomaly_key.csv)).

| | |
|---|---|
| Planted anomalies detected | **73 / 73 (100%)** |
| Routine entries flagged (false positives) | **3 of 5,038 (0.06%)** |
| Entries left for auditor follow-up | **76 of 5,111 (1.5%)** |

What it found:
- **Structuring:** one preparer posted 24 payments of $9,500–$9,999 to a new consulting vendor, just under
  the $10,000 approval limit. Benford's Law independently flags the same user: the digit 9 is
  over-represented by 11 percentage points (chi-square p < 0.0001). The rest of the population conforms closely (MAD 0.003).
- **Management override:** a manager posted and approved their own round-dollar "management fees"
  ($25k–$100k), some of them on weekends. These are the highest-risk entries.
- **Duplicate payments:** 10 vendor payments re-entered with the invoice number keyed differently
  (`INV-48213` vs `inv-48213` vs `INV-048213`), which is how duplicates usually get past ERP checks.
- **Cut-off risk:** manual revenue entries booked in the last days of each quarter.

The 3 false positives are routine entries that happen to fall just under $10,000, one each from
three different people. That's why the dashboard shows exceptions by preparer: the pattern matters more
than any single flag.

## Features

| Tab | What it does |
|---|---|
| **Overview** | Risk-ranked exceptions, exceptions by test and by month, CSV export |
| **JE Tests** | 8 tests with adjustable parameters and the audit reason for each |
| **Benford's Law** | First-digit test with MAD (Nigrini), z-stats, chi-square, ranked by preparer |
| **Duplicate Payments** | Same vendor and amount within N days, with fuzzy invoice matching |
| **MUS Sampling** | AICPA sample-size formula, systematic PPS selection, exportable sample |
| **Methodology** | How each test works and which standards it supports |

You can also upload your own ledger CSV (layout on the Methodology tab).

## Run it locally

```bash
git clone https://github.com/YOUR-USERNAME/ledgerlens.git
cd ledgerlens
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Regenerate the sample data with `python -m ledgerlens.generate_data`. Run the tests with `pytest`.

## How it's built

```
app.py                     Streamlit dashboard
ledgerlens/
  procedures.py            the 8 journal entry tests + risk scoring
  benford.py               Benford's Law (MAD, z-stat, chi-square)
  sampling.py              Monetary Unit Sampling
  generate_data.py         synthetic ledger with planted anomalies
  config.py                chart of accounts, holidays, default thresholds
tests/                     pytest suite: checks every planted anomaly is caught
```

Python · pandas · NumPy · Streamlit · Plotly · pytest

## Limitations and next steps

- Each entry is a single debit/credit pair. Real ERP extracts have multi-line entries.
- Next ideas: a completeness check (reconcile the ledger to the trial balance), gaps in JE numbering,
  seldom-used accounts, and testing against a public dataset.

*All data is synthetic. Company, vendor and user names are fictional.*
