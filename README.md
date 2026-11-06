# Tristan Audit Analytics

A website that tests **100% of a general ledger** for the fraud-risk warning signs that the auditing standards
(AU-C 240 / PCAOB AS 2401) ask auditors to look at. It ranks entries by risk, tells you what to do next, runs a
Benford's Law analysis, finds double payments and selects a Monetary Unit Sample.

**[▶ Open the live site](https://ledgerlens-6n89b9tdyecztmfkja8akz.streamlit.app)**

![Site screenshot](docs/screenshot.jpg)

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
  ($25k–$100k), some of them on weekends. Three of the four high-risk entries are theirs.
- **Duplicate payments:** 10 vendor payments re-entered with the invoice number keyed differently
  (`INV-48213` vs `inv-48213` vs `INV-048213`), which is how duplicates usually get past ERP checks.
- **Cut-off risk:** manual revenue entries booked in the last days of each quarter.

The 3 false positives are routine entries that happen to fall just under $10,000, one each from
three different people. That's why the site shows exceptions by preparer: the pattern matters more
than any single flag.

## Features

| Section | What it does |
|---|---|
| **Summary** | Scorecards for all 8 checks, a ranked review list, patterns by month and person, CSV export |
| **The 8 checks** | Every flagged entry, why the check matters and what to do next |
| **Number patterns** | Benford's Law in plain English, with MAD, z-stats and chi-square for auditors |
| **Double payments** | Same vendor and amount within N days, matching invoice numbers typed differently |
| **Pick a sample** | AICPA sample-size formula, systematic PPS selection, exportable sample |
| **How it works** | The method and the audit standards behind each check |

Plain-English answers come first, and the technical detail sits one click away. You can also upload your own
ledger using the built-in template.

## Run it locally

```bash
git clone https://github.com/Tristan-Accounting/ledgerlens.git
cd ledgerlens
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Regenerate the sample data with `python -m audit_analytics.generate_data`. Run the tests with `pytest`.

## How it's built

```
app.py                     the site
audit_analytics/
  procedures.py            the 8 journal entry tests + risk scoring
  benford.py               Benford's Law (MAD, z-stat, chi-square)
  sampling.py              Monetary Unit Sampling
  generate_data.py         synthetic ledger with planted anomalies
  config.py                chart of accounts, holidays, default thresholds
  ui.py                    design system: CSS, components, chart styling
tests/                     pytest suite: checks every planted anomaly is caught
```

Python · pandas · NumPy · Streamlit · Plotly · pytest

## Limitations and next steps

- Each entry is a single debit/credit pair. Real ERP extracts have multi-line entries.
- Next ideas: a completeness check (reconcile the ledger to the trial balance), gaps in JE numbering,
  seldom-used accounts, and testing against a public dataset.

*All data is synthetic. Company, vendor and user names are fictional.*
