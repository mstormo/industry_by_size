"""Load OECD SDBS data from pre-downloaded CSV files.

Data source: OECD Structural and Demographic Business Statistics (SDBS)
Dataset: DSD_SDBSBSC_ISIC4@DF_SDBS_ISIC4
Downloaded via data/scripts/download_oecd.py
"""
import csv
import logging
from pathlib import Path

from data.models import CensusRecord

logger = logging.getLogger(__name__)

# ISIC Rev. 4 section codes → NAICS-style display labels
ISIC_TO_LABEL: dict[str, str] = {
    "ISIC4_A": "Agriculture, forestry, fishing and hunting",
    "ISIC4_B": "Mining, quarrying, and oil and gas extraction",
    "ISIC4_C": "Manufacturing",
    "ISIC4_D": "Utilities",
    "ISIC4_E": "Utilities",  # merged with D
    "ISIC4_F": "Construction",
    "ISIC4_G": "Wholesale and retail trade",
    "ISIC4_H": "Transportation and warehousing",
    "ISIC4_I": "Accommodation and food services",
    "ISIC4_J": "Information",
    "ISIC4_K": "Finance and insurance",
    "ISIC4_L": "Real estate and rental and leasing",
    "ISIC4_M": "Professional, scientific, and technical services",
    "ISIC4_N": "Administrative and support and waste management",
    "ISIC4_P": "Educational services",
    "ISIC4_Q": "Health care and social assistance",
    "ISIC4_R": "Arts, entertainment, and recreation",
    "ISIC4_S": "Other services (except public administration)",
}

# OECD size class codes → display labels
OECD_SIZE_LABELS: dict[str, str] = {
    "S1T9": "1-9",
    "S10T19": "10-19",
    "S20T49": "20-49",
    "S50T249": "50-249",
    "S_GE250": "250+",
}

# Size classes to skip (totals, subtotals)
OECD_SKIP_SIZES = {"_T", "S1T249", "S_GE10"}


def _parse_oecd_csv(path: Path) -> dict[tuple[str, str], tuple[int, int]]:
    """Parse an OECD CSV into {(industry_label, size_label): (firms, emp)}.

    Uses the most recent year available per cell.
    """
    raw: dict[tuple[str, str, str, str], float] = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            activity = row.get("ACTIVITY", "")
            measure = row.get("MEASURE", "")
            size_class = row.get("SIZE_CLASS", "")
            year = row.get("TIME_PERIOD", "")
            value_str = row.get("OBS_VALUE", "")

            if activity not in ISIC_TO_LABEL:
                continue
            if size_class in OECD_SKIP_SIZES or size_class not in OECD_SIZE_LABELS:
                continue
            if measure not in ("ENTR", "EMP"):
                continue
            if not value_str:
                continue

            try:
                value = float(value_str)
            except ValueError:
                continue

            raw[(activity, size_class, measure, year)] = value

    best: dict[tuple[str, str, str], tuple[str, float]] = {}
    for (act, sz, meas, yr), val in raw.items():
        key = (act, sz, meas)
        if key not in best or yr > best[key][0]:
            best[key] = (yr, val)

    cells: dict[tuple[str, str], tuple[int, int]] = {}
    for (act, sz, meas), (_, val) in best.items():
        label = ISIC_TO_LABEL[act]
        size_label = OECD_SIZE_LABELS[sz]
        key = (label, size_label)
        firms, emp = cells.get(key, (0, 0))
        if meas == "ENTR":
            firms += int(val)
        else:
            emp += int(val)
        cells[key] = (firms, emp)

    return cells


def load_oecd_by_employment(
    country_codes: list[str],
    oecd_data_dir: Path,
) -> list[CensusRecord]:
    """Load Industry x Employee Size from pre-downloaded OECD CSV files."""
    aggregate: dict[tuple[str, str], tuple[int, int]] = {}

    for code in country_codes:
        csv_path = oecd_data_dir / f"{code}.csv"
        if not csv_path.exists():
            logger.warning("OECD CSV not found: %s — skipping", csv_path)
            continue

        cells = _parse_oecd_csv(csv_path)
        for key, (firms, emp) in cells.items():
            prev_firms, prev_emp = aggregate.get(key, (0, 0))
            aggregate[key] = (prev_firms + firms, prev_emp + emp)

    records = []
    for (industry, size_label), (firms, emp) in aggregate.items():
        records.append(CensusRecord(
            source_dimension="industry",
            source_value=industry,
            target_dimension="employeeSize",
            target_value=size_label,
            firms=firms,
            employees=emp,
        ))

    return records
