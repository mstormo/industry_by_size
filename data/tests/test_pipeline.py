import json
from unittest.mock import patch
from data.pipeline import run_pipeline
from data.models import Company


def _mock_companies(source: str, count: int) -> list[Company]:
    return [
        Company(
            id=f"{source}-{i}", name=f"{source} Corp {i}", industry="Technology",
            employeeCount=100 * (i + 1), employeeBucket=None,
            revenue=1_000_000 * (i + 1), revenueBucket=None,
            country="US", source=source,
        )
        for i in range(count)
    ]


@patch("data.pipeline.fetch_oc_companies", return_value=_mock_companies("oc", 2))
@patch("data.pipeline.fetch_wikidata_companies", return_value=_mock_companies("wiki", 3))
@patch("data.pipeline.fetch_edgar_companies", return_value=_mock_companies("edgar", 2))
def test_run_pipeline_produces_output_files(mock_edgar, mock_wiki, mock_oc, tmp_path):
    run_pipeline(str(tmp_path), max_edgar=2, max_wikidata=3, max_oc_pages=1)

    assert (tmp_path / "companies.json").exists()
    assert (tmp_path / "sankey-data.json").exists()

    companies = json.loads((tmp_path / "companies.json").read_text())
    assert len(companies) == 7  # 2 + 3 + 2, no duplicates

    sankey = json.loads((tmp_path / "sankey-data.json").read_text())
    assert len(sankey["nodes"]) > 0
    assert len(sankey["links"]) > 0
