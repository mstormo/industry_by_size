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
        CensusRecord(
            source_dimension="industry", source_value="Information",
            target_dimension="employeeSize", target_value="500+",
            firms=1200, employees=890000,
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


@patch("data.pipeline.fetch_industry_by_revenue", return_value=_mock_rev_records())
@patch("data.pipeline.fetch_industry_by_employment", return_value=_mock_emp_records())
def test_run_pipeline_produces_sankey_json(mock_emp, mock_rev, tmp_path):
    run_pipeline(str(tmp_path / "sankey-data.json"))

    output = tmp_path / "sankey-data.json"
    assert output.exists()

    sankey = json.loads(output.read_text())
    assert len(sankey["nodes"]) > 0
    assert len(sankey["links"]) == 3
    assert "availablePairs" in sankey
    # Verify links have firms/employees
    assert "firms" in sankey["links"][0]
    assert "employees" in sankey["links"][0]
