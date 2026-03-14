#!/usr/bin/env python3
"""One-time download of OECD SDBS data for all countries.

Run manually: python3 data/scripts/download_oecd.py
Downloads to: data/oecd/{COUNTRY_CODE}.csv

Rate limit: 60 requests/hour — script sleeps 3s between requests.
Uses SDMX REST v1 with multi-value key path (+ separator) for filtering.
Key format: FREQ.REF_AREA.MEASURE.ACTIVITY.SIZE_CLASS.UNIT_MEASURE (6 dims).
"""
import time
import sys
from pathlib import Path

import requests

# Add project root to path so we can import data.regions
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from data.regions import REGIONS

OECD_API = "https://sdmx.oecd.org/public/rest/data"
DATASET = "OECD.SDD.TPS,DSD_SDBSBSC_ISIC4@DF_SDBS_ISIC4"
MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 30]
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "oecd"


def download_country(code: str, output_dir: Path) -> bool:
    """Download OECD SDBS data for a single country. Returns True on success."""
    # Key format: FREQ.REF_AREA.MEASURE.ACTIVITY.SIZE_CLASS.UNIT_MEASURE
    # Use + for multi-value filtering in key path, . for wildcard
    url = f"{OECD_API}/{DATASET}/A.{code}.ENTR+EMPE..S1T9+S10T19+S20T49+S50T249+S_GE250+_T."
    params = {
        "format": "csvfilewithlabels",
        "dimensionAtObservation": "AllDimensions",
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=120)
            if resp.status_code == 404:
                print(f"  {code}: no data available (404)")
                return False
            if resp.status_code == 422:
                print(f"  {code}: unprocessable (422) — data may not be available")
                return False
            if resp.status_code == 429:
                wait = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)] * 3
                print(f"  {code}: rate limited (429), waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            out_path = output_dir / f"{code}.csv"
            out_path.write_text(resp.text, encoding="utf-8")
            lines = resp.text.strip().split("\n")
            print(f"  {code}: {len(lines) - 1} rows")
            return True
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                print(f"  {code}: error ({e}), retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"  {code}: FAILED after {MAX_RETRIES} attempts: {e}")
                return False
    return False


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
            time.sleep(3)  # Rate limit: ~20 req/min to stay safe
        result = download_country(code, output_dir)
        if result:
            success += 1
        else:
            failed += 1

    print(f"\nDone: {success} downloaded, {failed} failed/missing, {skipped} skipped (existing)")


if __name__ == "__main__":
    main()
