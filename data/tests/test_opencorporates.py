from data.sources.opencorporates import parse_oc_company
from data.models import Company

SAMPLE_COMPANY = {
    "company": {
        "company_number": "00445790",
        "name": "Tesco PLC",
        "jurisdiction_code": "gb",
        "industry_codes": [
            {"code": "47110", "description": "Retail sale in non-specialised stores"}
        ],
        "number_of_employees": "360000",
        "current_status": "Active",
    }
}


def test_parse_oc_company():
    result = parse_oc_company(SAMPLE_COMPANY["company"])
    assert result.name == "Tesco PLC"
    assert result.employeeCount == 360000
    assert result.country == "GB"
    assert result.source == "opencorporates"


def test_parse_oc_company_no_employees():
    company = {
        "company_number": "999",
        "name": "Mystery Corp",
        "jurisdiction_code": "us_ca",
        "industry_codes": [],
    }
    result = parse_oc_company(company)
    assert result.employeeCount is None
    assert result.country == "US"
