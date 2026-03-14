import json
from data.models import CensusRecord, SankeyData
from data.export import generate_sankey_from_census, export_census_to_file


SAMPLE_RECORDS = [
    CensusRecord(
        source_dimension="industry", source_value="Manufacturing",
        target_dimension="employeeSize", target_value="100-249",
        firms=13573, employees=943335,
    ),
    CensusRecord(
        source_dimension="industry", source_value="Manufacturing",
        target_dimension="employeeSize", target_value="500+",
        firms=3200, employees=2100000,
    ),
    CensusRecord(
        source_dimension="industry", source_value="Information",
        target_dimension="employeeSize", target_value="100-249",
        firms=8500, employees=590000,
    ),
    CensusRecord(
        source_dimension="industry", source_value="Manufacturing",
        target_dimension="revenueSize", target_value="$1-2.5M",
        firms=18000, employees=250000,
    ),
    CensusRecord(
        source_dimension="industry", source_value="Information",
        target_dimension="revenueSize", target_value="$100M+",
        firms=500, employees=800000,
    ),
]


def test_generate_sankey_has_correct_dimensions():
    data = generate_sankey_from_census(SAMPLE_RECORDS)
    assert "industry" in data.dimensions
    assert "employeeSize" in data.dimensions
    assert "revenueSize" in data.dimensions
    assert len(data.dimensions) == 3


def test_dimensions_derived_from_data():
    """Dimensions should be derived from records, not hardcoded."""
    emp_only = [
        CensusRecord(
            source_dimension="industry", source_value="Manufacturing",
            target_dimension="employeeSize", target_value="1-9",
            firms=100, employees=500,
        ),
    ]
    data = generate_sankey_from_census(emp_only)
    assert "revenueSize" not in data.dimensions
    assert "industry" in data.dimensions
    assert "employeeSize" in data.dimensions


def test_generate_sankey_nodes_created():
    data = generate_sankey_from_census(SAMPLE_RECORDS)
    node_ids = {n.id for n in data.nodes}
    assert "industry:Manufacturing" in node_ids
    assert "industry:Information" in node_ids
    assert "employeeSize:100-249" in node_ids
    assert "employeeSize:500+" in node_ids
    assert "revenueSize:$1-2.5M" in node_ids
    assert "revenueSize:$100M+" in node_ids


def test_generate_sankey_nodes_have_correct_dimension():
    data = generate_sankey_from_census(SAMPLE_RECORDS)
    for node in data.nodes:
        dim = node.id.split(":")[0]
        assert node.dimension == dim


def test_generate_sankey_links_have_firms_and_employees():
    data = generate_sankey_from_census(SAMPLE_RECORDS)
    link = next(
        l for l in data.links
        if l.source == "industry:Manufacturing" and l.target == "employeeSize:100-249"
    )
    assert link.firms == 13573
    assert link.employees == 943335


def test_generate_sankey_available_pairs():
    data = generate_sankey_from_census(SAMPLE_RECORDS)
    assert ("industry", "employeeSize") in data.availablePairs
    assert ("industry", "revenueSize") in data.availablePairs
    assert len(data.availablePairs) == 2


def test_generate_sankey_link_count():
    data = generate_sankey_from_census(SAMPLE_RECORDS)
    assert len(data.links) == 5  # one link per record


def test_export_census_to_file(tmp_path):
    data = generate_sankey_from_census(SAMPLE_RECORDS)
    output = tmp_path / "sankey-data.json"
    export_census_to_file(data, str(output))
    assert output.exists()

    loaded = json.loads(output.read_text())
    assert "availablePairs" in loaded
    assert "nodes" in loaded
    assert "links" in loaded
    # Verify links have firms/employees, not value
    assert "firms" in loaded["links"][0]
    assert "employees" in loaded["links"][0]
    assert "value" not in loaded["links"][0]
