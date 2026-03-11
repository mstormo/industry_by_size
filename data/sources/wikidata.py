"""Fetch company data from Wikidata SPARQL endpoint."""
import requests
from data.models import Company

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"

SPARQL_QUERY = """
SELECT ?company ?companyLabel ?industryLabel ?employees ?revenue ?countryLabel WHERE {
  ?company wdt:P31 wd:Q4830453.       # instance of business enterprise
  ?company wdt:P452 ?industry.         # industry
  ?company wdt:P17 ?country.           # country
  OPTIONAL { ?company wdt:P1128 ?employees. }  # employees
  OPTIONAL { ?company wdt:P2139 ?revenue. }    # revenue
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT %d
"""

COUNTRY_CODES: dict[str, str] = {
    "United States of America": "US",
    "United Kingdom": "GB",
    "Germany": "DE",
    "France": "FR",
    "Japan": "JP",
    "China": "CN",
    "Canada": "CA",
    "Australia": "AU",
    "India": "IN",
    "Brazil": "BR",
}


def parse_wikidata_result(result: dict) -> Company:
    entity_url = result["company"]["value"]
    entity_id = entity_url.split("/")[-1]
    name = result["companyLabel"]["value"]
    industry = result.get("industryLabel", {}).get("value", "Other")
    country_name = result.get("countryLabel", {}).get("value", "Unknown")
    country_code = COUNTRY_CODES.get(country_name, country_name)

    employees_raw = result.get("employees", {}).get("value")
    employee_count = int(float(employees_raw)) if employees_raw else None

    revenue_raw = result.get("revenue", {}).get("value")
    revenue = float(revenue_raw) if revenue_raw else None

    return Company(
        id=f"wiki-{entity_id}",
        name=name,
        industry=industry,
        employeeCount=employee_count,
        employeeBucket=None,
        revenue=revenue,
        revenueBucket=None,
        country=country_code,
        source="wikidata",
    )


def fetch_wikidata_companies(limit: int = 2000) -> list[Company]:
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": "IndustrySizeGraph/1.0",
    }
    params = {"query": SPARQL_QUERY % limit}
    resp = requests.get(WIKIDATA_SPARQL_URL, headers=headers, params=params, timeout=60)
    resp.raise_for_status()
    results = resp.json().get("results", {}).get("bindings", [])

    companies = []
    for r in results:
        try:
            companies.append(parse_wikidata_result(r))
        except (KeyError, ValueError):
            continue
    return companies
