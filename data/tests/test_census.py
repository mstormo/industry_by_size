import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from data.sources.census import (
    fetch_industry_by_employment,
    fetch_industry_by_revenue,
    parse_census_response,
    NAICS_LABELS,
    ECNSIZE_NAICS,
    EMPSIZE_LABELS,
    EMPSIZE_COLLAPSED,
    RCPSIZE_LABELS,
)


# Simulated ecnsize API response for revenue size
MOCK_ECNSIZE_RESPONSE = [
    ["FIRM", "EMP", "RCPTOT", "NAICS2022", "RCPSZFF", "us"],
    ["152901", "182808", "22680294", "23", "415", "1"],
    ["257398", "6319618", "1944680123", "23", "430", "1"],
    ["3164", "4965", "482123", "54", "410", "1"],
]

# Simulated SUSB CSV rows (as list of dicts after DictReader)
# Codes 04 (10-14) and 05 (15-19) both collapse into "10-24"
MOCK_SUSB_ROWS = [
    {"STATE": "00", "NAICS": "23", "ENTRSIZE": "02", "FIRM": "424187", "ESTB": "500000",
     "EMPL": "843199", "EMPLFL_N": "", "PAYR": "1000", "PAYRFL_N": "",
     "RCPT": "2000", "RCPTFL_N": "", "STATEDSCR": "United States",
     "NAICSDSCR": "Construction", "ENTRSIZEDSCR": "<5"},
    {"STATE": "00", "NAICS": "23", "ENTRSIZE": "04", "FIRM": "50000", "ESTB": "55000",
     "EMPL": "600000", "EMPLFL_N": "", "PAYR": "800", "PAYRFL_N": "",
     "RCPT": "1500", "RCPTFL_N": "", "STATEDSCR": "United States",
     "NAICSDSCR": "Construction", "ENTRSIZEDSCR": "10-14"},
    {"STATE": "00", "NAICS": "23", "ENTRSIZE": "05", "FIRM": "30000", "ESTB": "32000",
     "EMPL": "500000", "EMPLFL_N": "", "PAYR": "600", "PAYRFL_N": "",
     "RCPT": "1200", "RCPTFL_N": "", "STATEDSCR": "United States",
     "NAICSDSCR": "Construction", "ENTRSIZEDSCR": "15-19"},
    {"STATE": "00", "NAICS": "54", "ENTRSIZE": "02", "FIRM": "693445", "ESTB": "700000",
     "EMPL": "995896", "EMPLFL_N": "", "PAYR": "1200", "PAYRFL_N": "",
     "RCPT": "2500", "RCPTFL_N": "", "STATEDSCR": "United States",
     "NAICSDSCR": "Professional", "ENTRSIZEDSCR": "<5"},
    # Non-US row (should be skipped)
    {"STATE": "06", "NAICS": "23", "ENTRSIZE": "02", "FIRM": "50000", "ESTB": "60000",
     "EMPL": "100000", "EMPLFL_N": "", "PAYR": "500", "PAYRFL_N": "",
     "RCPT": "800", "RCPTFL_N": "", "STATEDSCR": "California",
     "NAICSDSCR": "Construction", "ENTRSIZEDSCR": "<5"},
    # Total row (should be skipped)
    {"STATE": "00", "NAICS": "23", "ENTRSIZE": "01", "FIRM": "999999", "ESTB": "999999",
     "EMPL": "999999", "EMPLFL_N": "", "PAYR": "9999", "PAYRFL_N": "",
     "RCPT": "9999", "RCPTFL_N": "", "STATEDSCR": "United States",
     "NAICSDSCR": "Construction", "ENTRSIZEDSCR": "Total"},
]


def test_parse_ecnsize_response_revenue():
    records = parse_census_response(
        MOCK_ECNSIZE_RESPONSE, "revenueSize", "RCPSZFF", RCPSIZE_LABELS,
    )
    assert len(records) == 3
    assert records[0].target_dimension == "revenueSize"
    assert records[0].target_value == "$100-250K"
    assert records[0].firms == 152901
    assert records[1].target_value == "$1-2.5M"
    assert records[2].source_value == "Professional, scientific, and technical services"


def test_parse_census_response_suppressed_values():
    """Census returns 'D' for suppressed cells — should be treated as 0."""
    response = [
        ["FIRM", "EMP", "RCPTOT", "NAICS2022", "RCPSZFF", "us"],
        ["D", "D", "D", "23", "410", "1"],
    ]
    records = parse_census_response(
        response, "revenueSize", "RCPSZFF", RCPSIZE_LABELS,
    )
    assert len(records) == 1
    assert records[0].firms == 0
    assert records[0].employees == 0


def test_parse_census_response_skips_totals():
    """Rows with size code 001 (total) should be skipped."""
    response = [
        ["FIRM", "EMP", "RCPTOT", "NAICS2022", "RCPSZFF", "us"],
        ["759808", "7341276", "9999", "23", "001", "1"],
        ["152901", "182808", "22680294", "23", "410", "1"],
        ["257398", "6319618", "1944680123", "23", "430", "1"],
    ]
    records = parse_census_response(
        response, "revenueSize", "RCPSZFF", RCPSIZE_LABELS,
    )
    assert len(records) == 2
    assert records[0].target_value == "<$100K"
    assert records[1].target_value == "$1-2.5M"


@patch("data.sources.census._download_susb")
def test_fetch_industry_by_employment(mock_download):
    mock_download.return_value = MOCK_SUSB_ROWS

    records = fetch_industry_by_employment()
    by_label = {(r.source_value, r.target_value): r for r in records}

    # 3 collapsed buckets: Construction/<5, Construction/10-24 (aggregated), Professional/<5
    assert len(records) == 3
    assert all(r.target_dimension == "employeeSize" for r in records)

    # <5 bucket is not aggregated
    r = by_label[("Construction", "<5")]
    assert r.firms == 424187
    assert r.employees == 843199

    # 10-24 bucket aggregates codes 04 (10-14) and 05 (15-19)
    r = by_label[("Construction", "10-24")]
    assert r.firms == 80000   # 50000 + 30000
    assert r.employees == 1100000  # 600000 + 500000


@patch("data.sources.census._download_susb")
def test_fetch_industry_by_employment_skips_non_us(mock_download):
    mock_download.return_value = MOCK_SUSB_ROWS

    records = fetch_industry_by_employment()
    # Should not include California row or total row
    assert len(records) == 3
    assert all(r.source_value in ("Construction", "Professional, scientific, and technical services") for r in records)


@patch("data.sources.census._fetch_with_retry")
def test_fetch_industry_by_revenue(mock_fetch):
    mock_fetch.return_value = MOCK_ECNSIZE_RESPONSE

    records = fetch_industry_by_revenue()
    assert len(records) == 3
    assert all(r.target_dimension == "revenueSize" for r in records)


@patch("data.sources.census.time.sleep")
@patch("data.sources.census.requests.get")
def test_fetch_retries_on_failure(mock_get, mock_sleep):
    """Should retry up to 3 times on HTTP errors."""
    mock_get.side_effect = [
        MagicMock(status_code=500, raise_for_status=MagicMock(side_effect=Exception("Server Error"))),
        MagicMock(status_code=500, raise_for_status=MagicMock(side_effect=Exception("Server Error"))),
        MagicMock(status_code=200, json=MagicMock(return_value=MOCK_ECNSIZE_RESPONSE), raise_for_status=MagicMock()),
    ]
    records = fetch_industry_by_revenue()
    assert len(records) == 3
    assert mock_get.call_count == 3
    assert mock_sleep.call_count == 2


def test_naics_labels_coverage():
    """20 NAICS sectors including Agriculture and Unclassified."""
    assert len(NAICS_LABELS) == 20
    assert "11" in NAICS_LABELS
    assert "55" in NAICS_LABELS
    assert "99" in NAICS_LABELS


def test_ecnsize_naics_coverage():
    """ecnsize has 17 sectors (no Agriculture, Management, Unclassified)."""
    assert len(ECNSIZE_NAICS) == 17
    assert "11" not in ECNSIZE_NAICS
    assert "55" not in ECNSIZE_NAICS
    assert "99" not in ECNSIZE_NAICS


def test_empsize_labels_coverage():
    """23 detailed employee size brackets from SUSB."""
    assert len(EMPSIZE_LABELS) == 23
    assert "02" in EMPSIZE_LABELS  # <5 employees
    assert "25" in EMPSIZE_LABELS  # 5,000+


def test_empsize_collapsed_coverage():
    """11 collapsed display buckets."""
    unique_buckets = set(EMPSIZE_COLLAPSED.values())
    assert len(unique_buckets) == 11
    assert "<5" in unique_buckets
    assert "5,000+" in unique_buckets
    # All detailed codes map to a bucket
    assert set(EMPSIZE_COLLAPSED.keys()) == set(EMPSIZE_LABELS.keys())


def test_rcpsize_labels_coverage():
    """10 revenue size brackets from ecnsize."""
    assert len(RCPSIZE_LABELS) == 10
    assert "410" in RCPSIZE_LABELS  # <$100K
    assert "455" in RCPSIZE_LABELS  # $100M+
