# Industry Size Graph — Design Spec

## Overview

An interactive web application that visualizes companies across industries by employee count and revenue using Sankey diagrams. Users start from any of three dimensions (industry, company size, revenue), select a bucket, and drill down through successive levels to explore how companies distribute across the other dimensions.

## Architecture

**Approach:** Full TypeScript SPA with D3.js frontend + Python data pipeline producing static JSON.

- **Frontend:** Vite + TypeScript + D3.js (d3-sankey)
- **Data pipeline:** Python scripts fetch and normalize data from public APIs into static JSON
- **Deployment:** Static files — no runtime server required

## Data Sources

Layered approach — free/open government data as foundation, commercial APIs later:

1. **SEC EDGAR** (US) — public company filings with revenue and employee counts
2. **EU Open Data / Companies House (UK)** — European company registries
3. **Wikidata / Wikipedia** — broad coverage of company metadata (industry, size, HQ)
4. **OpenCorporates API** (free tier) — aggregated global registry data

## Data Pipeline

### Pipeline Steps

1. **Fetch** — Python scripts per source, output raw JSON/CSV per source into `data/raw/` (gitignored)
2. **Normalize** — Deduplicate, standardize industry codes to a unified set of 12-15 industries (Technology, Healthcare, Finance, Manufacturing, Retail, Energy, etc.)
3. **Bucket** — Assign each company to employee-size and revenue buckets
4. **Export** — Generate `companies.json` and `sankey-data.json` into `public/data/`

### Bucket Definitions

**Employee size buckets:**
- <5, 5-9, 10-19, 20-49, 50-99, 100-249, 250-499, 500-999, 1K-4.9K, 5K-9.9K, 10K+

**Revenue buckets:**
- <$1M, $1-5M, $5-10M, $10-50M, $50-100M, $100-500M, $500M-1B, $1B+

### Industries (initial set, ~12-15)

Technology, Healthcare, Finance, Manufacturing, Retail, Energy, Transportation, Telecommunications, Real Estate, Education, Agriculture, Entertainment, Construction, Professional Services

## Data Model

### Company Record (`companies.json`)

```typescript
interface Company {
  id: string;              // unique identifier
  name: string;            // company name
  industry: string;        // normalized industry (e.g., "Technology")
  employeeCount: number;   // raw count
  employeeBucket: string;  // e.g., "100-249"
  revenue: number | null;  // USD, null if unknown
  revenueBucket: string | null; // e.g., "$10-50M"
  country: string;         // ISO country code
  source: string;          // data provenance (e.g., "sec-edgar")
}
```

### Sankey Aggregates (`sankey-data.json`)

```typescript
interface SankeyData {
  dimensions: string[];    // ["industry", "employeeBucket", "revenueBucket"]
  nodes: SankeyNode[];
  links: SankeyLink[];
}

interface SankeyNode {
  id: string;              // e.g., "industry:Technology"
  label: string;           // e.g., "Technology"
  dimension: string;       // e.g., "industry"
}

interface SankeyLink {
  source: string;          // node id
  target: string;          // node id
  value: number;           // count of companies
}
```

Pre-computed aggregates for each dimension pair (industry->size, industry->revenue, size->revenue) and three-level chains (industry->size->revenue). Frontend filters these by current selection rather than computing on the fly.

## UI Design

### Layout: Dashboard

- **Top bar:** App title left, dimension selector tabs right (Industry / Company Size / Revenue)
- **Main area:** D3 Sankey diagram filling the central space
- **Right sidebar:** Selection details panel showing counts and context for current selection

### Interaction Flow

1. **Choose starting dimension** — Click a tab (Industry, Size, or Revenue) to set the left column of the Sankey
2. **View initial Sankey** — Shows flow from the selected dimension to the next dimension (e.g., Industry -> Size)
3. **Click a node** — Click "Technology" on the left to filter: Sankey now shows how Tech companies distribute across size buckets
4. **Drill deeper** — Click "250-499" on the right: third level appears showing revenue breakdown for mid-size tech companies
5. **Breadcrumb navigation** — Breadcrumb trail at the top shows the drill-down path (e.g., "Industry > Technology > 250-499"), click any breadcrumb to jump back

### Sidebar Behavior

- Shows summary stats for current view (total companies, breakdown counts)
- On node hover: highlights connected flows, shows tooltip with count and percentage
- On node click: updates to show details of the selected bucket

## Project Structure

```
size-graph/
├── data/                    # Python data pipeline
│   ├── sources/             # One fetcher per data source
│   │   ├── sec_edgar.py
│   │   ├── wikidata.py
│   │   └── opencorporates.py
│   ├── normalize.py         # Dedup, standardize industries
│   ├── bucket.py            # Assign size/revenue buckets
│   ├── export.py            # Generate JSON for frontend
│   ├── requirements.txt
│   └── raw/                 # Raw fetched data (gitignored)
├── src/                     # TypeScript frontend
│   ├── main.ts              # App entry point
│   ├── sankey.ts            # D3 Sankey rendering & transitions
│   ├── controls.ts          # Dimension tabs, breadcrumb nav
│   ├── sidebar.ts           # Selection details panel
│   ├── types.ts             # Shared TypeScript types
│   └── style.css            # Styles
├── public/
│   ├── index.html
│   └── data/                # Generated JSON (from pipeline)
│       ├── companies.json
│       └── sankey-data.json
├── package.json
├── tsconfig.json
├── vite.config.ts
└── .gitignore
```

## Deferred Features

- **ML/AI headcount dimension** — data scientist/ML/CV/DL employee counts. Deferred until a reliable data source is identified. The architecture supports adding a fourth dimension later.

## Success Criteria

1. Data pipeline successfully fetches and normalizes company data from at least 2 sources
2. Sankey diagram renders with smooth transitions between drill-down levels
3. All three starting dimensions work (industry, size, revenue)
4. Multi-level drill-down works to at least 3 levels deep
5. Sidebar updates contextually with selection details
6. App loads from static files with no runtime server dependency
