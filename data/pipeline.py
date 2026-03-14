"""Fetch Census data and generate Sankey JSON for all regions."""
import argparse
from pathlib import Path

from data.sources.census import fetch_industry_by_employment, fetch_industry_by_revenue
from data.sources.oecd import load_oecd_by_employment
from data.export import generate_sankey_from_census, export_census_to_file
from data.regions import REGIONS, get_regions_json

OECD_DATA_DIR = Path(__file__).resolve().parent / "oecd"


def _generate_us(output_dir: str) -> None:
    """Generate US data from Census Bureau (SUSB + ecnsize)."""
    print("Fetching Industry x Employment Size from SUSB...")
    emp_records = fetch_industry_by_employment()
    print(f"  Got {len(emp_records)} records")

    print("Fetching Industry x Revenue Size from Census API...")
    rev_records = fetch_industry_by_revenue()
    print(f"  Got {len(rev_records)} records")

    all_records = emp_records + rev_records
    sankey = generate_sankey_from_census(all_records)
    print(f"  US: {len(sankey.nodes)} nodes, {len(sankey.links)} links")

    export_census_to_file(sankey, str(Path(output_dir) / "sankey-us.json"))


def _generate_oecd_region(region_id: str, oecd_codes: list[str], output_dir: str) -> None:
    """Generate data for an OECD region from pre-downloaded CSVs."""
    records = load_oecd_by_employment(oecd_codes, OECD_DATA_DIR)
    if not records:
        print(f"  {region_id}: no data — skipping")
        return

    sankey = generate_sankey_from_census(records)
    print(f"  {region_id}: {len(sankey.nodes)} nodes, {len(sankey.links)} links")

    export_census_to_file(sankey, str(Path(output_dir) / f"sankey-{region_id}.json"))


def run_pipeline(output_dir: str, regions: list[str] | None = None, skip_oecd: bool = False) -> None:
    """Generate Sankey JSON files for all (or selected) regions."""
    target_regions = REGIONS
    if regions:
        region_set = set(regions)
        target_regions = [r for r in REGIONS if r.id in region_set]

    generated_ids: set[str] = set()
    for region in target_regions:
        if region.source == "census":
            _generate_us(output_dir)
            generated_ids.add(region.id)
        elif region.source == "oecd" and not skip_oecd:
            _generate_oecd_region(region.id, region.oecd_codes, output_dir)
            # Check if file was actually created (skipped if no data)
            if (Path(output_dir) / f"sankey-{region.id}.json").exists():
                generated_ids.add(region.id)

    # Generate regions.json with only regions that have data
    regions_path = Path(output_dir) / "regions.json"
    regions_path.write_text(get_regions_json(only_ids=generated_ids))
    print(f"Wrote {regions_path} ({len(generated_ids)} regions)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Sankey JSON for all regions")
    parser.add_argument(
        "--output-dir", default="public/data",
        help="Output directory for sankey JSON files",
    )
    parser.add_argument(
        "--regions", nargs="*",
        help="Only generate specific regions (e.g., --regions us de fr)",
    )
    parser.add_argument(
        "--skip-oecd", action="store_true",
        help="Skip OECD regions, only generate US data",
    )
    args = parser.parse_args()
    run_pipeline(args.output_dir, regions=args.regions, skip_oecd=args.skip_oecd)
