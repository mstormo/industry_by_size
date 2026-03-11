"""Fetch aggregate business statistics from the US Census Bureau Economic Census."""
import logging
import time

import requests

from data.models import CensusRecord

logger = logging.getLogger(__name__)

API_BASE = "https://api.census.gov/data/2022/ecnsize"

# 18 NAICS sectors
NAICS_LABELS: dict[str, str] = {
    "21": "Mining, quarrying, and oil and gas extraction",
    "22": "Utilities",
    "23": "Construction",
    "31-33": "Manufacturing",
    "42": "Wholesale trade",
    "44-45": "Retail trade",
    "48-49": "Transportation and warehousing",
    "51": "Information",
    "52": "Finance and insurance",
    "53": "Real estate and rental and leasing",
    "54": "Professional, scientific, and technical services",
    "55": "Management of companies and enterprises",
    "56": "Administrative and support and waste management",
    "61": "Educational services",
    "62": "Health care and social assistance",
    "71": "Arts, entertainment, and recreation",
    "72": "Accommodation and food services",
    "81": "Other services (except public administration)",
}

# 8 employment size brackets (EMPSZFF codes)
EMPSIZE_LABELS: dict[str, str] = {
    "510": "<5 employees",
    "515": "5-9",
    "520": "10-19",
    "525": "20-49",
    "530": "50-99",
    "535": "100-249",
    "545": "250-499",
    "550": "500+",
}

# 10 revenue size brackets (RCPSZFF codes)
RCPSIZE_LABELS: dict[str, str] = {
    "410": "<$100K",
    "415": "$100-250K",
    "420": "$250-500K",
    "425": "$500K-1M",
    "430": "$1-2.5M",
    "435": "$2.5-5M",
    "440": "$5-10M",
    "445": "$10-25M",
    "450": "$25-100M",
    "455": "$100M+",
}

# Size codes that are totals/subtotals — skip these
SKIP_CODES = {"001", "200", "600"}

MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # seconds
REQUEST_TIMEOUT = 30  # seconds


def _safe_int(value: str) -> int:
    """Parse an integer from Census data, treating 'D' (suppressed) as 0."""
    if value == "D":
        return 0
    return int(value)


def _fetch_with_retry(url: str, params: dict) -> list[list[str]]:
    """Fetch Census API data with retry on failure."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
    raise last_error


def parse_census_response(
    rows: list[list[str]],
    target_dimension: str,
    size_field: str,
    size_labels: dict[str, str],
) -> list[CensusRecord]:
    """Parse Census API JSON response into CensusRecord list."""
    header = rows[0]
    naics_idx = header.index("NAICS2022")
    size_idx = header.index(size_field)
    firms_idx = header.index("FIRMPDEMP")
    emp_idx = header.index("EMP")

    records = []
    for row in rows[1:]:
        size_code = row[size_idx]
        if size_code in SKIP_CODES:
            continue
        if size_code not in size_labels:
            continue

        naics_code = row[naics_idx]
        if naics_code not in NAICS_LABELS:
            continue

        firms = _safe_int(row[firms_idx])
        employees = _safe_int(row[emp_idx])

        if firms == 0 and employees == 0:
            logger.warning("Suppressed cell: NAICS=%s, %s=%s", naics_code, size_field, size_code)

        records.append(CensusRecord(
            source_dimension="industry",
            source_value=NAICS_LABELS[naics_code],
            target_dimension=target_dimension,
            target_value=size_labels[size_code],
            firms=firms,
            employees=employees,
        ))

    return records


def fetch_industry_by_employment() -> list[CensusRecord]:
    """Fetch Industry x Employment Size cross-tabulation."""
    rows = _fetch_with_retry(API_BASE, {
        "get": "FIRMPDEMP,EMP,RCPTOT",
        "for": "us:*",
        "NAICS2022": "*",
        "EMPSZFF": "*",
    })
    return parse_census_response(rows, "employeeSize", "EMPSZFF", EMPSIZE_LABELS)


def fetch_industry_by_revenue() -> list[CensusRecord]:
    """Fetch Industry x Revenue Size cross-tabulation."""
    rows = _fetch_with_retry(API_BASE, {
        "get": "FIRMPDEMP,EMP,RCPTOT",
        "for": "us:*",
        "NAICS2022": "*",
        "RCPSZFF": "*",
    })
    return parse_census_response(rows, "revenueSize", "RCPSZFF", RCPSIZE_LABELS)
