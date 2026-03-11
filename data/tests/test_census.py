import pytest
from unittest.mock import patch, MagicMock
from data.sources.census import (
    fetch_industry_by_employment,
    fetch_industry_by_revenue,
    parse_census_response,
    NAICS_LABELS,
    EMPSIZE_LABELS,
    RCPSIZE_LABELS,
)


# Simulated Census API response (header row + data rows)
MOCK_EMP_RESPONSE = [
    ["NAICS2022", "NAICS2022_LABEL", "EMPSZFF", "EMPSZFF_LABEL", "FIRM", "EMP", "RCPTOT"],
    ["31-33", "Manufacturing", "510", "Less than 5", "45000", "120000", "15000000"],
    ["31-33", "Manufacturing", "515", "5 to 9", "22000", "150000", "20000000"],
    ["51", "Information", "510", "Less than 5", "30000", "80000", "10000000"],
]

MOCK_RCV_RESPONSE = [
    ["NAICS2022", "NAICS2022_LABEL", "RCPSZFF", "RCPSZFF_LABEL", "FIRM", "EMP", "RCPTOT"],
    ["31-33", "Manufacturing", "410", "Less than $100,000", "12000", "30000", "800000"],
    ["51", "Information", "430", "$1,000,000 to $2,499,999", "8000", "60000", "12000000"],
]


def test_parse_census_response_employment():
    records = parse_census_response(MOCK_EMP_RESPONSE, "employeeSize", "EMPSZFF", EMPSIZE_LABELS)
    assert len(records) == 3
    assert records[0].source_dimension == "industry"
    assert records[0].source_value == "Manufacturing"
    assert records[0].target_dimension == "employeeSize"
    assert records[0].target_value == "<5 employees"
    assert records[0].firms == 45000
    assert records[0].employees == 120000


def test_parse_census_response_revenue():
    records = parse_census_response(MOCK_RCV_RESPONSE, "revenueSize", "RCPSZFF", RCPSIZE_LABELS)
    assert len(records) == 2
    assert records[0].target_dimension == "revenueSize"
    assert records[0].target_value == "<$100K"
    assert records[1].target_value == "$1-2.5M"


def test_parse_census_response_suppressed_values():
    """Census returns 'D' for suppressed cells — should be treated as 0."""
    response = [
        ["NAICS2022", "NAICS2022_LABEL", "EMPSZFF", "EMPSZFF_LABEL", "FIRM", "EMP", "RCPTOT"],
        ["55", "Management of companies", "550", "500 or more", "D", "D", "D"],
    ]
    records = parse_census_response(response, "employeeSize", "EMPSZFF", EMPSIZE_LABELS)
    assert len(records) == 1
    assert records[0].firms == 0
    assert records[0].employees == 0


def test_parse_census_response_skips_totals():
    """Rows with size code 001, 200, or 600 are totals/subtotals and should be skipped."""
    response = [
        ["NAICS2022", "NAICS2022_LABEL", "EMPSZFF", "EMPSZFF_LABEL", "FIRM", "EMP", "RCPTOT"],
        ["31-33", "Manufacturing", "001", "All firms", "100000", "5000000", "900000000"],
        ["31-33", "Manufacturing", "510", "Less than 5", "45000", "120000", "15000000"],
    ]
    records = parse_census_response(response, "employeeSize", "EMPSZFF", EMPSIZE_LABELS)
    assert len(records) == 1
    assert records[0].target_value == "<5 employees"


@patch("data.sources.census.requests.get")
def test_fetch_industry_by_employment(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_EMP_RESPONSE
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    records = fetch_industry_by_employment()
    assert len(records) == 3
    assert all(r.target_dimension == "employeeSize" for r in records)
    mock_get.assert_called_once()


@patch("data.sources.census.requests.get")
def test_fetch_industry_by_revenue(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_RCV_RESPONSE
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    records = fetch_industry_by_revenue()
    assert len(records) == 2
    assert all(r.target_dimension == "revenueSize" for r in records)


@patch("data.sources.census.time.sleep")
@patch("data.sources.census.requests.get")
def test_fetch_retries_on_failure(mock_get, mock_sleep):
    """Should retry up to 3 times on HTTP errors."""
    mock_get.side_effect = [
        MagicMock(status_code=500, raise_for_status=MagicMock(side_effect=Exception("Server Error"))),
        MagicMock(status_code=500, raise_for_status=MagicMock(side_effect=Exception("Server Error"))),
        MagicMock(status_code=200, json=MagicMock(return_value=MOCK_EMP_RESPONSE), raise_for_status=MagicMock()),
    ]
    records = fetch_industry_by_employment()
    assert len(records) == 3
    assert mock_get.call_count == 3
    assert mock_sleep.call_count == 2


def test_naics_labels_coverage():
    """All 18 NAICS sectors should have labels."""
    assert len(NAICS_LABELS) == 18
    assert "31-33" in NAICS_LABELS
    assert "55" in NAICS_LABELS


def test_empsize_labels_coverage():
    """All 8 employment size brackets should have labels."""
    assert len(EMPSIZE_LABELS) == 8


def test_rcpsize_labels_coverage():
    """All 10 revenue size brackets should have labels."""
    assert len(RCPSIZE_LABELS) == 10
