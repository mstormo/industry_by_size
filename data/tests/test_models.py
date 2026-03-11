from data.models import Company


def test_company_with_all_fields():
    c = Company(
        id="sec-AAPL",
        name="Apple Inc.",
        industry="Technology",
        employeeCount=164000,
        employeeBucket="10K+",
        revenue=394328000000,
        revenueBucket="$1B+",
        country="US",
        source="sec-edgar",
    )
    assert c.name == "Apple Inc."
    assert c.industry == "Technology"
    assert c.employeeBucket == "10K+"


def test_company_with_null_fields():
    c = Company(
        id="wiki-123",
        name="Small Corp",
        industry="Retail",
        employeeCount=None,
        employeeBucket=None,
        revenue=None,
        revenueBucket=None,
        country="DE",
        source="wikidata",
    )
    assert c.employeeCount is None
    assert c.revenue is None
