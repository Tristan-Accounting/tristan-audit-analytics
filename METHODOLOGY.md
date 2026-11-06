## Why journal entry testing?

Management override of controls is a fraud risk in every audit. The auditing standards
(**AICPA AU-C 240** and **PCAOB AS 2401**, *Consideration of Fraud in a Financial Statement Audit*)
require auditors to test the appropriateness of journal entries. Auditors do this by picking out
entries that have known fraud-risk characteristics. LedgerLens automates that selection step
across the whole population, not a handful of entries.

## The tests

| Test | What it flags | Weight |
|---|---|---|
| Weekend / holiday posting | Manual entries posted on a Saturday, Sunday or company holiday | 2 |
| After-hours posting | Manual entries posted outside business hours | 2 |
| Round-dollar amount | Amounts that are exact multiples of the chosen round number | 1 |
| Just below approval limit | Manual entries within X% under the approval threshold, a sign of possible split transactions | 3 |
| Self-approved | Preparer and approver are the same person (segregation of duties failure) | 3 |
| Missing required approval | Manual entries over the threshold with no approver recorded | 3 |
| Period-end manual revenue | Manual entries to revenue accounts in the last days of a quarter | 3 |
| Possible duplicate payment | Same vendor, amount and accounts within N days, with invoice numbers normalised | 3 |

The **risk score** for each entry is the sum of the weights of the tests it fails.
High ≥ 5, Medium 3–4, Low 1–2. A flag isn't a finding. It's an entry to pull support for and ask about.

## Benford's Law

In many naturally occurring financial datasets, the leading digit is 1 about 30.1% of the time
and 9 only 4.6% of the time. LedgerLens compares the actual first-digit distribution to Benford's and reports:

- **MAD (Mean Absolute Deviation)**, using Nigrini's first-digit conformity ranges
  (≤0.006 close, ≤0.012 acceptable, ≤0.015 marginal, above that nonconformity).
- **Z-statistics** per digit, to show which digits are significantly over- or under-represented.
- **Chi-square p-value**, used to rank individual preparers. MAD thresholds are built for large
  populations and give false alarms on a few hundred entries. The p-value accounts for sample size.

## Monetary Unit Sampling (MUS)

For substantive testing of an account, LedgerLens picks a probability-proportional-to-size sample
(**AU-C 530 / PCAOB AS 2315**, *Audit Sampling*). Sample size follows the AICPA *Audit Sampling* guide:

> n = (population value × confidence factor) ÷ (tolerable misstatement − expected misstatement × expansion factor)

Items are selected systematically from a random start using the sampling interval
(population ÷ n). Any item at least as large as the interval is always selected.

## Uploading your own ledger

Upload a CSV with one row per journal entry.

| Column | Required | Example |
|---|---|---|
| `je_id` | ✅ | JE-2025-000123 |
| `posted_at` | ✅ | 2025-03-31 22:14:05 |
| `amount` | ✅ | 9850.00 |
| `created_by` | ✅ | jsmith |
| `source` | | Manual / Automated (blank = Manual) |
| `approved_by` | | lbrown |
| `debit_account`, `credit_account` | | 6300, 1000 |
| `description`, `vendor`, `invoice_number` | | Consulting services, Apex Consulting LLC, INV-48213 |

Tests that need an optional column return no exceptions if the column is missing.
Everything runs in your browser session and nothing is stored.

## Limitations

- The holiday calendar is US federal holidays for FY2025 (`ledgerlens/config.py`).
- Each entry is one debit/credit pair. Multi-line entries would need to be summarised first.
- Analytics show where to look. They don't replace auditor judgment, inquiry or vouching to support.
