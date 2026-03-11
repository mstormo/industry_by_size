from data.models import CensusRecord, SankeyNode, SankeyLink, SankeyData


def test_census_record_creation():
    record = CensusRecord(
        source_dimension="industry",
        source_value="Manufacturing",
        target_dimension="employeeSize",
        target_value="100-249",
        firms=13573,
        employees=943335,
    )
    assert record.firms == 13573
    assert record.employees == 943335
    assert record.source_dimension == "industry"


def test_sankey_link_has_firms_and_employees():
    link = SankeyLink(
        source="industry:Manufacturing",
        target="employeeSize:100-249",
        firms=13573,
        employees=943335,
    )
    assert link.firms == 13573
    assert link.employees == 943335


def test_sankey_data_has_available_pairs():
    data = SankeyData(
        dimensions=["industry", "employeeSize", "revenueSize"],
        nodes=[],
        links=[],
        availablePairs=[("industry", "employeeSize"), ("industry", "revenueSize")],
    )
    assert len(data.availablePairs) == 2
    assert ("industry", "employeeSize") in data.availablePairs
