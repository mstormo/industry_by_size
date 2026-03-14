#!/usr/bin/env python3
"""One-time download of OECD SDBS data for all countries.

Run manually: python3 data/scripts/download_oecd.py
Downloads to: data/oecd/{COUNTRY_CODE}.csv

Rate limit: ~20 requests/minute — script sleeps 3s between requests.
Makes separate requests for ENTR (enterprises) and EMPE (employees) measures
because multi-value MEASURE filtering is unreliable.
Key format: FREQ.REF_AREA.MEASURE.ACTIVITY.SIZE_CLASS.UNIT_MEASURE (6 dims).
"""
import time
import sys
import io
import csv
from pathlib import Path

import requests

# Add project root to path so we can import data.regions
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from data.regions import REGIONS

OECD_API = "https://sdmx.oecd.org/public/rest/data"
DATASET = "OECD.SDD.TPS,DSD_SDBSBSC_ISIC4@DF_SDBS_ISIC4"
SIZE_FILTER = "S1T9+S10T19+S20T49+S50T249+S_GE250+_T"
MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 30]
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "oecd"


def _fetch_measure(code: str, measure: str) -> str | None:
    """Fetch one measure for a country. Returns CSV text or None."""
    url = f"{OECD_API}/{DATASET}/A.{code}.{measure}..{SIZE_FILTER}."
    params = {
        "format": "csvfilewithlabels",
        "dimensionAtObservation": "AllDimensions",
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=120)
            if resp.status_code in (404, 422):
                return None
            if resp.status_code == 429:
                wait = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)] * 3
                print(f"    {code}/{measure}: rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                print(f"    {code}/{measure}: error ({e}), retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"    {code}/{measure}: FAILED after {MAX_RETRIES} attempts: {e}")
                return None
    return None


def download_country(code: str, output_dir: Path) -> bool:
    """Download OECD SDBS data for a single country. Returns True on success."""
    entr_text = _fetch_measure(code, "ENTR")
    time.sleep(3)
    empe_text = _fetch_measure(code, "EMPE")

    if not entr_text and not empe_text:
        print(f"  {code}: no data available")
        return False

    # Merge the two CSVs: use ENTR header, append EMPE data rows
    parts = []
    if entr_text:
        parts.append(entr_text.strip())
    if empe_text:
        lines = empe_text.strip().split("\n")
        if entr_text:
            # Skip header from second file
            parts.append("\n".join(lines[1:]))
        else:
            parts.append("\n".join(lines))

    merged = "\n".join(parts) + "\n"
    out_path = output_dir / f"{code}.csv"
    out_path.write_text(merged, encoding="utf-8")
    rows = merged.strip().count("\n")  # minus header
    print(f"  {code}: {rows} rows")
    return True


def main() -> None:
    output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect unique country codes from all regions
    all_codes: set[str] = set()
    for region in REGIONS:
        all_codes.update(region.oecd_codes)

    codes = sorted(all_codes)
    print(f"Downloading OECD SDBS data for {len(codes)} countries to {output_dir}/")

    success = 0
    failed = 0
    skipped = 0
    for i, code in enumerate(codes):
        out_path = output_dir / f"{code}.csv"
        if out_path.exists():
            lines = out_path.read_text().strip().split("\n")
            print(f"  {code}: already exists ({len(lines) - 1} rows), skipping")
            skipped += 1
            continue
        if i > 0:
            time.sleep(3)
        result = download_country(code, output_dir)
        if result:
            success += 1
        else:
            failed += 1

    print(f"\nDone: {success} downloaded, {failed} failed/missing, {skipped} skipped (existing)")


if __name__ == "__main__":
    main()
