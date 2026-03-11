# Census Data Migration Design Spec

## Problem

The current data pipeline scrapes individual company records from SEC EDGAR, Wikidata, and OpenCorporates APIs. This produces a tiny, biased sample (~410 companies after normalization) that doesn't represent the US economy. Many Wikidata industry labels fall into "Other", and OpenCorporates returns 0 results.

## Solution

Replace the individual-company data pipeline with **US Census Bureau aggregate statistics** that cover all ~6.4 million US businesses. Use the **2022 Economic Census Size Statistics API** (`api.census.gov/data/2022/ecnsize`) as the primary data source.

## Data Source

**API Endpoint:** `https://api.census.gov/data/2022/ecnsize`

No API key required. Returns JSON arrays. Free, public, authoritative.

### Available Cross-Tabulations

| Query | Dimensions | Values per cell |
|-------|-----------|----------------|
| `EMPSZFF` by `NAICS2022` | Industry × Employee Size | FIRM count, EMP count, RCPTOT |
| `RCPSZFF` by `NAICS2022` | Industry × Revenue Size | FIRM count, EMP count, RCPTOT |

**NOT available:** Employee Size × Revenue Size (Census suppresses this three-way cross-tab for disclosure avoidance).

### NAICS Sectors (18)

| Code | Label |
|------|-------|
| 21 | Mining, quarrying, and oil and gas extraction |
| 22 | Utilities |
| 23 | Construction |
| 31-33 | Manufacturing |
| 42 | Wholesale trade |
| 44-45 | Retail trade |
| 48-49 | Transportation and warehousing |
| 51 | Information |
| 52 | Finance and insurance |
| 53 | Real estate and rental and leasing |
| 54 | Professional, scientific, and technical services |
| 55 | Management of companies and enterprises |
| 56 | Administrative and support and waste management |
| 61 | Educational services |
| 62 | Health care and social assistance |
| 71 | Arts, entertainment, and recreation |
| 72 | Accommodation and food services |
| 81 | Other services (except public administration) |

Note: Sector 55 data may be heavily suppressed. Include it if the API returns it; omit gracefully if all values are suppressed.

### Employment Size Codes (8 brackets, from EMPSZFF)

| Code | Label |
|------|-------|
| 510 | <5 employees |
| 515 | 5-9 |
| 520 | 10-19 |
| 525 | 20-49 |
| 530 | 50-99 |
| 535 | 100-249 |
| 545 | 250-499 |
| 550 | 500+ |

Excluded: `001` (All firms), `200` (Operated entire year), `600` (Not operated entire year) — these are totals/subtotals.

### Revenue Size Codes (10 brackets, from RCPSZFF)

| Code | Label |
|------|-------|
| 410 | <$100K |
| 415 | $100-250K |
| 420 | $250-500K |
| 425 | $500K-1M |
| 430 | $1-2.5M |
| 435 | $2.5-5M |
| 440 | $5-10M |
| 445 | $10-25M |
| 450 | $25-100M |
| 455 | $100M+ |

Excluded: `001`, `200`, `600` (same reason).

## Architecture Changes

### Data Model

Replace the individual-company model with an aggregate cross-tab model:

```python
class CensusRecord(BaseModel):
    """A single cell from a Census cross-tabulation."""
    source_dimension: str      # e.g., "industry"
    source_value: str          # e.g., "Manufacturing"
    target_dimension: str      # e.g., "employeeSize"
    target_value: str          # e.g., "100-249"
    firms: int                 # number of firms
    employees: int             # number of employees
```

`RCPTOT` (total revenue) is intentionally dropped — the Sankey visualizes firm count and employee count only. Revenue totals per cell are not needed for the current UI.

**Modified file:** `data/models.py`
- Add `CensusRecord` model (above)
- Update `SankeyLink`: add `employees: int` field
- Update `SankeyData`: add `availablePairs: list[tuple[str, str]]` field
- Remove `Company` model (no longer used)

### Pipeline Changes

**New file:** `data/sources/census.py`
- `fetch_industry_by_employment()` — calls ecnsize API with EMPSZFF × NAICS2022
- `fetch_industry_by_revenue()` — calls ecnsize API with RCPSZFF × NAICS2022
- Parse JSON responses into `CensusRecord` lists
- Map Census size codes to human-readable labels
- **Suppressed values:** Census returns `"D"` instead of a number when a cell is suppressed for disclosure avoidance. Treat suppressed values as 0 (the firms exist but we can't show the exact count). Log a warning with the suppressed cell coordinates.
- **Error handling:** Retry up to 3 times with exponential backoff (1s, 2s, 4s) on HTTP errors or timeouts. Raise after exhausting retries. Timeout: 30 seconds per request.

**Modified file:** `data/export.py`
- New function `generate_sankey_from_census(records)` that builds nodes and links directly from aggregate records
- Generates two sets of links: one for firm count, one for employee count
- Output format includes both metrics

**Removed/deprecated:**
- `data/sources/sec_edgar.py` — no longer needed
- `data/sources/wikidata.py` — no longer needed
- `data/sources/opencorporates.py` — no longer needed
- `data/normalize.py` — no longer needed (Census data is already normalized)
- `data/bucket.py` — no longer needed (Census data is already bucketed)

**Modified file:** `data/pipeline.py`
- Simplified to: fetch Census data → generate Sankey JSON → export

### Sankey Data Output Format

```json
{
  "dimensions": ["industry", "employeeSize", "revenueSize"],
  "nodes": [
    {"id": "industry:Manufacturing", "label": "Manufacturing", "dimension": "industry"},
    {"id": "employeeSize:100-249", "label": "100-249", "dimension": "employeeSize"},
    {"id": "revenueSize:$1-2.5M", "label": "$1-2.5M", "dimension": "revenueSize"}
  ],
  "links": [
    {
      "source": "industry:Manufacturing",
      "target": "employeeSize:100-249",
      "firms": 13573,
      "employees": 943335
    }
  ],
  "availablePairs": [
    ["industry", "employeeSize"],
    ["industry", "revenueSize"]
  ]
}
```

Key changes from current format:
- Each link now has `firms` (firm count) and `employees` (employee count) — no ambiguous `value` field
- New `availablePairs` field lists which dimension pairs have real data (stored as `[source, target]` with industry always as source)
- Dimension names change: `employeeBucket` → `employeeSize`, `revenueBucket` → `revenueSize`

### Reverse Links and Direction

Links are stored **unidirectional** with industry always as source: `industry → employeeSize` and `industry → revenueSize`. The data file does NOT contain reverse-direction links.

When the user selects a starting dimension that is NOT industry (e.g., starts at `employeeSize`), `filterSankeyForDrill` flips the lookup: it matches links where the **target** starts with the user's source dimension and the **source** starts with the user's target dimension, then swaps `source`/`target` in the returned links. This avoids doubling the data size.

Default metric on page load: **firms**.

### Frontend Changes

**`src/types.ts`:**
- Update `Dimension` type: `'industry' | 'employeeSize' | 'revenueSize'`
- Update `SankeyLink`: replace `value: number` with `firms: number` and `employees: number`
- Add `availablePairs: [Dimension, Dimension][]` to `SankeyData`
- Add `Metric` type: `'firms' | 'employees'`

**`src/data.ts`:**
- `filterSankeyForDrill` checks `availablePairs` for the requested source→target pair. If the pair is not available in either direction, returns empty `{ nodes: [], links: [] }`.
- For reverse pairs (e.g., user wants `employeeSize → industry` but data has `industry → employeeSize`), `filterSankeyForDrill` matches links by swapping source/target roles and returns links with source/target flipped.
- `getAvailableDimensions` updated to accept `availablePairs` and only return dimensions that form a valid pair with the current path.
- New `getMetricValue(link, metric)` helper: returns `link.firms` for `'firms'`, `link.employees` for `'employees'`.

**`src/controls.ts`:**
- Add metric toggle (Firms / Employees) to the top bar
- Disable dimension tab combinations that don't have data (Employee Size ↔ Revenue Size)

**`src/sankey.ts`:**
- Accept `metric` parameter to choose which value to use for link width
- Pass metric through to rendering

**`src/sidebar.ts`:**
- Show both metrics in stats (firms and employees)
- Format large numbers with appropriate suffixes (1.2M, 45K, etc.)

**`src/main.ts`:**
- Wire up metric toggle
- Pass metric through refresh cycle
- `handleNodeClick` checks `availablePairs` before allowing drill-down; if the next dimension would form an unavailable pair, skip it or show a message

**`public/index.html`:**
- Add metric toggle buttons to the top bar

## Dimension Pair Availability

| Source → Target | Available? |
|----------------|-----------|
| Industry → Employee Size | Yes |
| Industry → Revenue Size | Yes |
| Employee Size → Industry | Yes (reverse of above) |
| Revenue Size → Industry | Yes (reverse of above) |
| Employee Size → Revenue Size | No |
| Revenue Size → Employee Size | No |

When the user selects a combination that has no data, the app shows a message: "This dimension combination is not available in Census data."

## Testing

- `data/tests/test_census.py` — test API response parsing, label mapping, error handling
- `data/tests/test_export.py` — update to test new `generate_sankey_from_census`
- `data/tests/test_pipeline.py` — update with mocked Census fetcher
- Frontend tests updated for new types and metric toggle

## Migration Notes

- The `Company` model, `bucket.py`, `normalize.py`, and the three API fetchers can be removed entirely
- The `SankeyNode`/`SankeyLink`/`SankeyData` models evolve but keep the same structure
- The frontend dimension names change (`employeeBucket` → `employeeSize`, `revenueBucket` → `revenueSize`)
