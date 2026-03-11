"""Fetch Census data and generate Sankey JSON."""
import argparse

from data.sources.census import fetch_industry_by_employment, fetch_industry_by_revenue
from data.export import generate_sankey_from_census, export_census_to_file


def run_pipeline(output_path: str) -> None:
    print("Fetching Industry x Employment Size from Census API...")
    emp_records = fetch_industry_by_employment()
    print(f"  Got {len(emp_records)} records")

    print("Fetching Industry x Revenue Size from Census API...")
    rev_records = fetch_industry_by_revenue()
    print(f"  Got {len(rev_records)} records")

    all_records = emp_records + rev_records
    print(f"Total records: {len(all_records)}")

    print("Generating Sankey data...")
    sankey = generate_sankey_from_census(all_records)
    print(f"  {len(sankey.nodes)} nodes, {len(sankey.links)} links")

    print(f"Exporting to {output_path}...")
    export_census_to_file(sankey, output_path)
    print("Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch Census data and generate Sankey JSON")
    parser.add_argument(
        "--output", default="../public/data/sankey-data.json",
        help="Output path for sankey-data.json",
    )
    args = parser.parse_args()
    run_pipeline(args.output)
