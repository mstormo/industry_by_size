"""Fetch aggregate business statistics from US Census Bureau data.

Uses two sources:
- SUSB (Statistics of US Businesses) 2022 for Industry × Employee Size
  (detailed size brackets from <5 up to 5,000+; firm-level counts; CSV download)
- Economic Census Size Statistics (ecnsize) 2022 for Industry × Revenue Size
  (10 revenue brackets; 17 of 20 sectors; API)
"""
import csv
import logging
import time
from pathlib import Path

import requests

from data.models import CensusRecord

logger = logging.getLogger(__name__)

ECNSIZE_API = "https://api.census.gov/data/2022/ecnsize"
SUSB_URL = "https://www2.census.gov/programs-surveys/susb/tables/2022/us_state_naics_detailedsizes_2022.txt"

# 20 NAICS sectors
NAICS_LABELS: dict[str, str] = {
    "11": "Agriculture, forestry, fishing and hunting",
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
    "99": "Unclassified",
}

# ecnsize has 17 sectors (no 11, 55 suppressed, no 99)
ECNSIZE_NAICS: dict[str, str] = {
    k: v for k, v in NAICS_LABELS.items() if k not in ("11", "55", "99")
}

# SUSB detailed employment size brackets (ENTRSIZE codes)
# Excludes totals (01) and subtotals (33=<20, 37=<500)
EMPSIZE_LABELS: dict[str, str] = {
    "02": "<5 employees",
    "03": "5-9",
    "04": "10-14",
    "05": "15-19",
    "06": "20-24",
    "07": "25-29",
    "08": "30-34",
    "09": "35-39",
    "10": "40-49",
    "11": "50-74",
    "12": "75-99",
    "13": "100-149",
    "14": "150-199",
    "15": "200-299",
    "16": "300-399",
    "17": "400-499",
    "18": "500-749",
    "19": "750-999",
    "31": "1,000-1,499",
    "22": "1,500-1,999",
    "23": "2,000-2,499",
    "24": "2,500-4,999",
    "25": "5,000+",
}

# Mapping from detailed SUSB codes → collapsed display buckets.
# Note: code "15" (200-299) is assigned to "100-249" — the SUSB boundary
# at 200 doesn't align perfectly with our 249/250 split.
EMPSIZE_COLLAPSED: dict[str, str] = {
    "02": "<5",
    "03": "5-9",
    "04": "10-24", "05": "10-24", "06": "10-24",
    "07": "25-49", "08": "25-49", "09": "25-49", "10": "25-49",
    "11": "50-99", "12": "50-99",
    "13": "100-249", "14": "100-249", "15": "100-249",
    "16": "250-499", "17": "250-499",
    "18": "500-999", "19": "500-999",
    "31": "1,000-2,499", "22": "1,000-2,499", "23": "1,000-2,499",
    "24": "2,500-4,999",
    "25": "5,000+",
}

# ecnsize revenue brackets (RCPSZFF codes)
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

# Backward-compatible aliases
CBP_NAICS = NAICS_LABELS
ABS_NAICS = NAICS_LABELS
CBP_EMPSIZE_LABELS = EMPSIZE_LABELS
ABS_RCPSIZE_LABELS = RCPSIZE_LABELS

# Size codes that are totals/subtotals
SUSB_SKIP_CODES = {"01", "33", "37"}
ECNSIZE_SKIP_CODES = {"001", "200", "600"}

MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # seconds
REQUEST_TIMEOUT = 30  # seconds


def _safe_int(value: str) -> int:
    """Parse an integer from Census data, treating 'D' (suppressed) as 0."""
    if value in ("D", ""):
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


def _download_susb(cache_path: Path | None = None) -> list[dict[str, str]]:
    """Download and parse the SUSB detailed sizes CSV file."""
    if cache_path and cache_path.exists():
        logger.info("Using cached SUSB file: %s", cache_path)
    else:
        logger.info("Downloading SUSB data from Census Bureau...")
        resp = requests.get(SUSB_URL, timeout=60)
        resp.raise_for_status()
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(resp.content)

    path = cache_path if cache_path else None
    if path:
        text = path.read_text(encoding="latin-1")
    else:
        text = resp.text

    rows = []
    reader = csv.DictReader(text.splitlines())
    for row in reader:
        rows.append({k.strip(): v.strip() for k, v in row.items()})
    return rows


def parse_census_response(
    rows: list[list[str]],
    target_dimension: str,
    size_field: str,
    size_labels: dict[str, str],
    naics_field: str = "NAICS2022",
    naics_labels: dict[str, str] | None = None,
    firms_field: str = "FIRM",
    emp_field: str = "EMP",
    skip_codes: set[str] | None = None,
) -> list[CensusRecord]:
    """Parse Census API JSON response into CensusRecord list."""
    if naics_labels is None:
        naics_labels = ECNSIZE_NAICS
    if skip_codes is None:
        skip_codes = ECNSIZE_SKIP_CODES

    header = rows[0]
    naics_idx = header.index(naics_field)
    size_idx = header.index(size_field)
    firms_idx = header.index(firms_field)
    emp_idx = header.index(emp_field)

    records = []
    for row in rows[1:]:
        size_code = row[size_idx]
        if size_code in skip_codes:
            continue
        if size_code not in size_labels:
            continue

        naics_code = row[naics_idx]
        if naics_code not in naics_labels:
            continue

        firms = _safe_int(row[firms_idx])
        employees = _safe_int(row[emp_idx])

        if firms == 0 and employees == 0:
            logger.warning("Suppressed cell: NAICS=%s, %s=%s", naics_code, size_field, size_code)

        records.append(CensusRecord(
            source_dimension="industry",
            source_value=naics_labels[naics_code],
            target_dimension=target_dimension,
            target_value=size_labels[size_code],
            firms=firms,
            employees=employees,
        ))

    return records


def fetch_industry_by_employment(cache_dir: Path | None = None) -> list[CensusRecord]:
    """Fetch Industry × Employee Size from SUSB (Statistics of US Businesses).

    SUSB provides 23 detailed employee size brackets which are collapsed into
    11 display buckets (<5 through 5,000+), covering all 20 NAICS sectors.
    """
    cache_path = cache_dir / "susb_detailed_2022.txt" if cache_dir else None
    susb_rows = _download_susb(cache_path)

    # Aggregate detailed SUSB brackets into collapsed buckets
    agg: dict[tuple[str, str], tuple[int, int]] = {}  # (industry, bucket) → (firms, emp)
    for row in susb_rows:
        state = row.get("STATE", "")
        if state != "00":
            continue

        naics = row.get("NAICS", "")
        if naics not in NAICS_LABELS:
            continue

        size_code = row.get("ENTRSIZE", "")
        if size_code in SUSB_SKIP_CODES:
            continue
        if size_code not in EMPSIZE_COLLAPSED:
            continue

        bucket = EMPSIZE_COLLAPSED[size_code]
        firms = _safe_int(row.get("FIRM", "0"))
        employees = _safe_int(row.get("EMPL", "0"))

        key = (naics, bucket)
        prev_firms, prev_emp = agg.get(key, (0, 0))
        agg[key] = (prev_firms + firms, prev_emp + employees)

    records = []
    for (naics, bucket), (firms, employees) in agg.items():
        records.append(CensusRecord(
            source_dimension="industry",
            source_value=NAICS_LABELS[naics],
            target_dimension="employeeSize",
            target_value=bucket,
            firms=firms,
            employees=employees,
        ))

    return records


def fetch_industry_by_revenue() -> list[CensusRecord]:
    """Fetch Industry × Revenue Size from Economic Census Size Statistics.

    ecnsize provides 10 revenue brackets from <$100K to $100M+,
    covering 17 of 20 NAICS sectors (no Agriculture, Management, Unclassified).
    """
    rows = _fetch_with_retry(ECNSIZE_API, {
        "get": "FIRM,EMP,RCPTOT,NAICS2022,RCPSZFF",
        "for": "us:*",
    })
    return parse_census_response(rows, "revenueSize", "RCPSZFF", RCPSIZE_LABELS)
