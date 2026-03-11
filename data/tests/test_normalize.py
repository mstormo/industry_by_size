from data.models import Company
from data.normalize import normalize_industry, deduplicate, normalize_companies

VALID_INDUSTRIES = [
    "Technology", "Healthcare", "Finance", "Manufacturing", "Retail",
    "Energy", "Transportation", "Telecommunications", "Real Estate",
    "Education", "Agriculture", "Entertainment", "Construction",
    "Professional Services",
]


def test_normalize_industry_exact_match():
    assert normalize_industry("Technology") == "Technology"


def test_normalize_industry_case_insensitive():
    assert normalize_industry("technology") == "Technology"
    assert normalize_industry("HEALTHCARE") == "Healthcare"


def test_normalize_industry_alias():
    assert normalize_industry("Tech") == "Technology"
    assert normalize_industry("Financial Services") == "Finance"
    assert normalize_industry("Banking") == "Finance"
    assert normalize_industry("Pharma") == "Healthcare"
    assert normalize_industry("Automotive") == "Manufacturing"


def test_normalize_industry_unknown():
    assert normalize_industry("Underwater Basket Weaving") == "Other"


def test_deduplicate_by_name():
    companies = [
        Company(id="a", name="Apple Inc.", industry="Technology",
                employeeCount=100, employeeBucket="50-99",
                revenue=None, revenueBucket=None, country="US", source="sec"),
        Company(id="b", name="Apple Inc.", industry="Technology",
                employeeCount=164000, employeeBucket="10K+",
                revenue=394e9, revenueBucket="$1B+", country="US", source="wiki"),
    ]
    result = deduplicate(companies)
    assert len(result) == 1
    # Prefer the record with more data (non-null fields)
    assert result[0].revenue == 394e9


def test_normalize_companies_applies_buckets_and_industry():
    companies = [
        Company(id="a", name="Test Corp", industry="tech",
                employeeCount=50, employeeBucket=None,
                revenue=2_000_000, revenueBucket=None,
                country="US", source="test"),
    ]
    result = normalize_companies(companies)
    assert result[0].industry == "Technology"
    assert result[0].employeeBucket == "50-99"
    assert result[0].revenueBucket == "$1-5M"
