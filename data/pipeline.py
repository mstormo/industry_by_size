"""Orchestrate the full data pipeline: fetch -> normalize -> export."""
import argparse

from data.sources.sec_edgar import fetch_edgar_companies
from data.sources.wikidata import fetch_wikidata_companies
from data.sources.opencorporates import fetch_oc_companies
from data.normalize import normalize_companies
from data.export import export_to_files


def run_pipeline(
    output_dir: str,
    max_edgar: int = 500,
    max_wikidata: int = 2000,
    max_oc_pages: int = 10,
) -> None:
    print("Fetching from SEC EDGAR...")
    edgar = fetch_edgar_companies(max_companies=max_edgar)
    print(f"  Got {len(edgar)} companies from EDGAR")

    print("Fetching from Wikidata...")
    wiki = fetch_wikidata_companies(limit=max_wikidata)
    print(f"  Got {len(wiki)} companies from Wikidata")

    print("Fetching from OpenCorporates...")
    oc = fetch_oc_companies(max_pages=max_oc_pages)
    print(f"  Got {len(oc)} companies from OpenCorporates")

    all_companies = edgar + wiki + oc
    print(f"\nTotal raw: {len(all_companies)}")

    print("Normalizing...")
    normalized = normalize_companies(all_companies)
    print(f"After normalization: {len(normalized)}")

    print(f"Exporting to {output_dir}...")
    export_to_files(normalized, output_dir)
    print("Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the data pipeline")
    parser.add_argument(
        "--output", default="../public/data",
        help="Output directory for JSON files",
    )
    parser.add_argument("--max-edgar", type=int, default=500)
    parser.add_argument("--max-wikidata", type=int, default=2000)
    parser.add_argument("--max-oc-pages", type=int, default=10)
    args = parser.parse_args()

    run_pipeline(args.output, args.max_edgar, args.max_wikidata, args.max_oc_pages)
