from data.sources.wikidata import parse_wikidata_result
from data.models import Company

SAMPLE_RESULT = {
    "company": {"value": "http://www.wikidata.org/entity/Q312"},
    "companyLabel": {"value": "Apple Inc."},
    "industryLabel": {"value": "technology company"},
    "employees": {"value": "164000"},
    "revenue": {"value": "394328000000"},
    "countryLabel": {"value": "United States of America"},
}


def test_parse_wikidata_result():
    result = parse_wikidata_result(SAMPLE_RESULT)
    assert result.name == "Apple Inc."
    assert result.employeeCount == 164000
    assert result.revenue == 394328000000
    assert result.source == "wikidata"
    assert result.id == "wiki-Q312"


def test_parse_wikidata_result_missing_optional():
    minimal = {
        "company": {"value": "http://www.wikidata.org/entity/Q999"},
        "companyLabel": {"value": "SmallCo"},
        "industryLabel": {"value": "retail"},
        "countryLabel": {"value": "Germany"},
    }
    result = parse_wikidata_result(minimal)
    assert result.employeeCount is None
    assert result.revenue is None
    assert result.country == "DE"
