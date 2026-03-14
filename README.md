# Industry by Size

Interactive Sankey diagram showing how businesses distribute across industries, employee size brackets, and revenue ranges — for 32 regions worldwide.

**Live demo:** [mstormo.github.io/industry_by_size](https://mstormo.github.io/industry_by_size/)

## Data Sources

- **United States** — [SUSB 2022](https://www.census.gov/programs-surveys/susb.html) (Census Bureau) for industry × employee size (20 NAICS sectors, 11 size brackets from <5 to 5,000+), and [Economic Census 2022](https://www.census.gov/programs-surveys/economic-census.html) for industry × revenue size (10 brackets from <$100K to $100M+)
- **International** — [OECD Structural and Demographic Business Statistics](https://www.oecd.org/en/data/datasets/structural-and-demographic-business-statistics-isic-rev-4.html) (SDBS, ISIC Rev. 4) for industry × employee size across 49 OECD member countries (5 brackets from 1–9 to 250+)

## Features

- Sankey diagram with d3-sankey, showing flows between industries and size brackets
- Region selector dropdown with 32 regions: global aggregate, US, Canada, 18 European countries, 4 Asia-Pacific, 5 Latin American, and 2 other OECD
- Two metrics: number of firms or number of employees
- Revenue tab available for US data (disabled with tooltip for non-US regions)
- Click nodes to select/highlight connected flows, double-click to drill down
- Dual sidebars with sorted breakdowns, cross-filtering, and selection state
- Breadcrumb navigation for drill-down levels

## Tech Stack

- **Frontend:** TypeScript, D3.js, d3-sankey, Vite
- **Data pipeline:** Python 3, requests, pydantic
- **Testing:** vitest (frontend), pytest (Python)
- **Deployment:** GitHub Actions → GitHub Pages

## Development

```bash
npm install
npm run dev          # Start Vite dev server
npm test             # Run frontend tests
```

### Data Pipeline

The Python pipeline fetches Census data and processes pre-downloaded OECD CSVs into per-region Sankey JSON files.

```bash
# Install Python dependencies
pip install requests pydantic

# Download OECD data (one-time, ~3 minutes)
python3 data/scripts/download_oecd.py

# Generate all region JSON files
python3 -m data.pipeline

# Generate specific regions only
python3 -m data.pipeline --regions us de fr

# US only (skip OECD)
python3 -m data.pipeline --skip-oecd
```

Output goes to `public/data/`:
- `sankey-{regionId}.json` — one per region (32 files)
- `regions.json` — region metadata for the dropdown

### Running Tests

```bash
npm test                           # Frontend (vitest)
python3 -m pytest data/tests/ -v   # Python pipeline
```

## Project Structure

```
├── src/
│   ├── main.ts          # App entry, region/selection state management
│   ├── sankey.ts         # D3 Sankey renderer with selection highlighting
│   ├── sidebar.ts        # Dual sidebar panels with sorted stats
│   ├── controls.ts       # Region dropdown, dimension tabs, metric toggle
│   ├── data.ts           # Data loading, filtering, sorting
│   └── types.ts          # Shared TypeScript types
├── data/
│   ├── pipeline.py       # Multi-region data generation orchestrator
│   ├── regions.py        # Region hierarchy (32 regions, OECD codes)
│   ├── sources/
│   │   ├── census.py     # US Census Bureau (SUSB + ecnsize)
│   │   └── oecd.py       # OECD SDBS CSV parser
│   ├── export.py         # CensusRecord → Sankey JSON conversion
│   ├── models.py         # Pydantic data models
│   └── scripts/
│       └── download_oecd.py  # One-time OECD data downloader
├── public/data/          # Generated JSON files (committed for GitHub Pages)
└── .github/workflows/
    └── deploy.yml        # Build + deploy to GitHub Pages
```
