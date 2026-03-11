from data.sources.sec_edgar import parse_edgar_company
from data.models import Company

SAMPLE_FILING = {
    "cik": "0000320193",
    "entityName": "Apple Inc.",
    "sic": "3571",
    "sicDescription": "Electronic Computers",
    "facts": {
        "dei": {
            "EntityCommonStockSharesOutstanding": {},
        },
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"val": 394328000000, "fy": 2022, "form": "10-K"}
                    ]
                }
            },
            "EntityNumberOfEmployees": {
                "units": {
                    "pure": [
                        {"val": 164000, "fy": 2022, "form": "10-K"}
                    ]
                }
            },
        }
    }
}


def test_parse_edgar_company():
    result = parse_edgar_company(SAMPLE_FILING)
    assert result is not None
    assert result.name == "Apple Inc."
    assert result.employeeCount == 164000
    assert result.revenue == 394328000000
    assert result.source == "sec-edgar"
    assert result.industry == "Technology"  # Mapped from SIC 3571


def test_parse_edgar_company_missing_revenue():
    filing = {
        "cik": "0000001234",
        "entityName": "NoRev Corp",
        "sic": "9999",
        "facts": {"us-gaap": {}},
    }
    result = parse_edgar_company(filing)
    assert result is not None
    assert result.revenue is None
    assert result.industry == "Other"  # Unknown SIC maps to Other
