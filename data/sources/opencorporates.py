"""Fetch company data from OpenCorporates API."""
import requests
from data.models import Company

OC_SEARCH_URL = "https://api.opencorporates.com/v0.4/companies/search"


def parse_oc_company(company: dict) -> Company:
    name = company.get("name", "Unknown")
    number = company.get("company_number", "0")
    jurisdiction = company.get("jurisdiction_code", "")
    country = jurisdiction.split("_")[0].upper() if jurisdiction else "XX"

    industry_codes = company.get("industry_codes", [])
    industry = "Other"
    if industry_codes:
        industry = industry_codes[0].get("description", "Other")

    employees_raw = company.get("number_of_employees")
    employee_count = int(employees_raw) if employees_raw else None

    return Company(
        id=f"oc-{jurisdiction}-{number}",
        name=name,
        industry=industry,
        employeeCount=employee_count,
        employeeBucket=None,
        revenue=None,
        revenueBucket=None,
        country=country,
        source="opencorporates",
    )


def fetch_oc_companies(max_pages: int = 10) -> list[Company]:
    companies: list[Company] = []
    for page in range(1, max_pages + 1):
        try:
            resp = requests.get(
                OC_SEARCH_URL,
                params={"q": "*", "page": page, "per_page": 100},
                timeout=30,
            )
            if resp.status_code != 200:
                break
            results = resp.json().get("results", {}).get("companies", [])
            if not results:
                break
            for item in results:
                try:
                    companies.append(parse_oc_company(item["company"]))
                except (KeyError, ValueError):
                    continue
        except requests.RequestException:
            break
    return companies
