import json
from unittest.mock import patch
from data.pipeline import run_pipeline
from data.models import CensusRecord


def _mock_emp_records() -> list[CensusRecord]:
    return [
        CensusRecord(
            source_dimension="industry", source_value="Manufacturing",
            target_dimension="employeeSize", target_value="100-249",
            firms=13573, employees=943335,
        ),
    ]


def _mock_rev_records() -> list[CensusRecord]:
    return [
        CensusRecord(
            source_dimension="industry", source_value="Manufacturing",
            target_dimension="revenueSize", target_value="$1-2.5M",
            firms=18000, employees=250000,
        ),
    ]


def _mock_oecd_records(codes, data_dir) -> list[CensusRecord]:
    return [
        CensusRecord(
            source_dimension="industry", source_value="Manufacturing",
            target_dimension="employeeSize", target_value="1-9",
            firms=100000, employees=400000,
        ),
    ]


@patch("data.pipeline.fetch_industry_by_revenue", return_value=_mock_rev_records())
@patch("data.pipeline.fetch_industry_by_employment", return_value=_mock_emp_records())
@patch("data.pipeline.load_oecd_by_employment", side_effect=_mock_oecd_records)
def test_run_pipeline_produces_multi_region(mock_oecd, mock_emp, mock_rev, tmp_path):
    run_pipeline(str(tmp_path), regions=["us", "de"])

    # US file should exist with revenue data
    us_file = tmp_path / "sankey-us.json"
    assert us_file.exists()
    us_data = json.loads(us_file.read_text())
    assert "revenueSize" in us_data["dimensions"]
    assert ("industry", "revenueSize") in [tuple(p) for p in us_data["availablePairs"]]

    # Germany file should exist without revenue data
    de_file = tmp_path / "sankey-de.json"
    assert de_file.exists()
    de_data = json.loads(de_file.read_text())
    assert "revenueSize" not in de_data["dimensions"]

    # regions.json should exist
    regions_file = tmp_path / "regions.json"
    assert regions_file.exists()
    regions = json.loads(regions_file.read_text())
    assert "regions" in regions
    assert "groups" in regions
