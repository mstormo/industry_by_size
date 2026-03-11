"""Fetch company data from SEC EDGAR XBRL company facts API.

SEC EDGAR provides free access to company filings. The companyfacts endpoint
returns structured XBRL data including revenue and employee counts from 10-K filings.

API docs: https://www.sec.gov/edgar/sec-api-documentation
Rate limit: 10 requests/second, requires User-Agent header.
"""
import time
import requests
from data.models import Company

EDGAR_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
EDGAR_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
USER_AGENT = "IndustrySizeGraph/1.0 (research@example.com)"

SIC_TO_INDUSTRY: dict[str, str] = {
    "01": "Agriculture", "02": "Agriculture", "07": "Agriculture", "08": "Agriculture", "09": "Agriculture",
    "10": "Energy", "12": "Energy", "13": "Energy", "14": "Energy", "29": "Energy",
    "15": "Construction", "16": "Construction", "17": "Construction",
    "20": "Manufacturing", "21": "Manufacturing", "22": "Manufacturing", "23": "Manufacturing",
    "24": "Manufacturing", "25": "Manufacturing", "26": "Manufacturing", "27": "Manufacturing",
    "30": "Manufacturing", "31": "Manufacturing", "32": "Manufacturing", "33": "Manufacturing",
    "34": "Manufacturing", "37": "Manufacturing", "38": "Manufacturing", "39": "Manufacturing",
    "35": "Technology", "36": "Technology", "73": "Technology",
    "28": "Healthcare", "80": "Healthcare",
    "40": "Transportation", "41": "Transportation", "42": "Transportation",
    "44": "Transportation", "45": "Transportation", "46": "Transportation", "47": "Transportation",
    "48": "Telecommunications",
    "49": "Energy",
    "50": "Retail", "51": "Retail", "52": "Retail", "53": "Retail",
    "54": "Retail", "55": "Retail", "56": "Retail", "57": "Retail", "58": "Retail", "59": "Retail",
    "60": "Finance", "61": "Finance", "62": "Finance", "63": "Finance", "64": "Finance", "67": "Finance",
    "65": "Real Estate",
    "70": "Entertainment", "78": "Entertainment", "79": "Entertainment",
    "82": "Education",
    "87": "Professional Services", "89": "Professional Services",
}


def _sic_to_industry(sic: str) -> str:
    prefix = sic[:2]
    return SIC_TO_INDUSTRY.get(prefix, "Other")


def _extract_latest_10k_value(facts: dict, namespace: str, field: str, prefer_unit: str | None = None) -> float | None:
    """Extract the most recent 10-K value for a given XBRL field.

    If prefer_unit is specified (e.g., "USD"), try that unit type first to avoid
    returning values from an unrelated unit (e.g., shares instead of dollars).
    """
    ns_data = facts.get(namespace, {})
    field_data = ns_data.get(field, {})
    units = field_data.get("units", {})

    # Try preferred unit first, then fall back to any unit
    unit_order = []
    if prefer_unit and prefer_unit in units:
        unit_order.append(units[prefer_unit])
    for key, val in units.items():
        if key != prefer_unit:
            unit_order.append(val)

    for entries in unit_order:
        ten_k_values = [e for e in entries if e.get("form") == "10-K"]
        if ten_k_values:
            latest = max(ten_k_values, key=lambda e: e.get("fy", 0))
            return latest["val"]
    return None


def parse_edgar_company(filing: dict) -> Company | None:
    cik = str(filing.get("cik", "")).lstrip("0")
    name = filing.get("entityName", "Unknown")
    facts = filing.get("facts", {})
    sic = str(filing.get("sic", ""))
    industry = _sic_to_industry(sic) if sic else "Other"

    revenue = (
        _extract_latest_10k_value(facts, "us-gaap", "Revenues", prefer_unit="USD")
        or _extract_latest_10k_value(facts, "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", prefer_unit="USD")
        or _extract_latest_10k_value(facts, "us-gaap", "SalesRevenueNet", prefer_unit="USD")
    )

    employee_count_raw = _extract_latest_10k_value(facts, "dei", "EntityNumberOfEmployees", prefer_unit="pure")
    if employee_count_raw is None:
        employee_count_raw = _extract_latest_10k_value(facts, "us-gaap", "EntityNumberOfEmployees", prefer_unit="pure")
    employee_count = int(employee_count_raw) if employee_count_raw is not None else None

    return Company(
        id=f"sec-{cik}",
        name=name,
        industry=industry,
        employeeCount=employee_count,
        employeeBucket=None,
        revenue=revenue,
        revenueBucket=None,
        country="US",
        source="sec-edgar",
    )


def fetch_edgar_companies(max_companies: int = 500) -> list[Company]:
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(EDGAR_COMPANY_TICKERS_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    tickers = resp.json()

    companies: list[Company] = []
    for _key, info in list(tickers.items())[:max_companies]:
        cik = str(info["cik_str"]).zfill(10)
        try:
            facts_resp = requests.get(
                EDGAR_COMPANY_FACTS_URL.format(cik=cik),
                headers=headers,
                timeout=30,
            )
            if facts_resp.status_code != 200:
                continue
            filing = facts_resp.json()
            if "sic" not in filing and "sic" in info:
                filing["sic"] = str(info["sic"])
            company = parse_edgar_company(filing)
            if company is not None:
                companies.append(company)
        except (requests.RequestException, KeyError, ValueError):
            continue
        time.sleep(0.12)
    return companies
