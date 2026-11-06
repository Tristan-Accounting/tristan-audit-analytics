"""Runs the whole site headlessly, on the sample ledger and on small uploaded-style files."""
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).parent.parent / "app.py")

TEMPLATE_ROW = {"je_id": "JE-0001", "posted_at": "2025-03-31 14:05:00", "amount": 1250.00, "created_by": "jsmith",
                "source": "Manual", "approved_by": "", "debit_account": 6300, "credit_account": 1000,
                "description": "Consulting services", "vendor": "Acme Co", "invoice_number": "INV-1001"}
MINIMAL_ROW = {k: TEMPLATE_ROW[k] for k in ["je_id", "posted_at", "amount", "created_by"]}


@pytest.fixture(autouse=True)
def fresh_cache():
    st.cache_data.clear()  # otherwise a later test silently reuses the previous test's ledger


def test_site_runs_on_sample_data():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception


@pytest.mark.parametrize("row", [TEMPLATE_ROW, MINIMAL_ROW], ids=["template", "required_columns_only"])
def test_site_runs_on_a_ledger_with_nothing_flagged(row):
    with patch("pandas.read_csv", return_value=pd.DataFrame([row])) as read_csv:
        at = AppTest.from_file(APP, default_timeout=60).run()
    read_csv.assert_called()
    assert not at.exception
    assert not at.error
