import json
from data.models import Company, SankeyData
from data.export import generate_sankey_data, export_to_files

SAMPLE_COMPANIES = [
    Company(id="1", name="TechCo", industry="Technology",
            employeeCount=150, employeeBucket="100-249",
            revenue=50_000_000, revenueBucket="$10-50M",
            country="US", source="test"),
    Company(id="2", name="TechSmall", industry="Technology",
            employeeCount=8, employeeBucket="5-9",
            revenue=2_000_000, revenueBucket="$1-5M",
            country="US", source="test"),
    Company(id="3", name="HealthBig", industry="Healthcare",
            employeeCount=5000, employeeBucket="1K-4.9K",
            revenue=500_000_000, revenueBucket="$100-500M",
            country="US", source="test"),
    Company(id="4", name="NoRevenue", industry="Technology",
            employeeCount=20, employeeBucket="10-19",
            revenue=None, revenueBucket=None,
            country="US", source="test"),
]


def test_generate_sankey_data_has_all_dimensions():
    data = generate_sankey_data(SAMPLE_COMPANIES)
    assert set(data.dimensions) == {"industry", "employeeBucket", "revenueBucket"}


def test_generate_sankey_data_nodes_include_industries():
    data = generate_sankey_data(SAMPLE_COMPANIES)
    node_ids = {n.id for n in data.nodes}
    assert "industry:Technology" in node_ids
    assert "industry:Healthcare" in node_ids


def test_generate_sankey_data_nodes_include_buckets():
    data = generate_sankey_data(SAMPLE_COMPANIES)
    node_ids = {n.id for n in data.nodes}
    assert "employeeBucket:100-249" in node_ids
    assert "revenueBucket:$10-50M" in node_ids


def test_generate_sankey_data_links_count():
    data = generate_sankey_data(SAMPLE_COMPANIES)
    # Find link from Technology -> 100-249 employees
    link = next(
        (l for l in data.links
         if l.source == "industry:Technology" and l.target == "employeeBucket:100-249"),
        None,
    )
    assert link is not None
    assert link.value == 1


def test_generate_sankey_data_all_six_dimension_pairs():
    data = generate_sankey_data(SAMPLE_COMPANIES)
    links_by_pair = {}
    for link in data.links:
        src_dim = link.source.split(":")[0]
        tgt_dim = link.target.split(":")[0]
        pair = (src_dim, tgt_dim)
        links_by_pair.setdefault(pair, []).append(link)

    expected_pairs = [
        ("industry", "employeeBucket"),
        ("industry", "revenueBucket"),
        ("employeeBucket", "industry"),
        ("employeeBucket", "revenueBucket"),
        ("revenueBucket", "industry"),
        ("revenueBucket", "employeeBucket"),
    ]
    for pair in expected_pairs:
        assert pair in links_by_pair, f"Missing dimension pair: {pair[0]} -> {pair[1]}"
        assert len(links_by_pair[pair]) > 0, f"No links for pair: {pair[0]} -> {pair[1]}"


def test_generate_sankey_data_excludes_null_from_relevant_links():
    data = generate_sankey_data(SAMPLE_COMPANIES)
    # NoRevenue company (id=4) should not appear in revenue links
    revenue_links = [l for l in data.links if "revenueBucket:" in l.target or "revenueBucket:" in l.source]
    total_revenue_companies = sum(l.value for l in revenue_links if l.source.startswith("industry:"))
    # Only 3 companies have revenue (not NoRevenue)
    assert total_revenue_companies == 3


def test_export_to_files(tmp_path):
    export_to_files(SAMPLE_COMPANIES, str(tmp_path))
    companies_path = tmp_path / "companies.json"
    sankey_path = tmp_path / "sankey-data.json"
    assert companies_path.exists()
    assert sankey_path.exists()

    companies = json.loads(companies_path.read_text())
    assert len(companies) == 4

    sankey = json.loads(sankey_path.read_text())
    assert "nodes" in sankey
    assert "links" in sankey
