# Industry Size Graph Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an interactive Sankey diagram web app that visualizes companies by industry, employee count, and revenue with multi-level drill-down.

**Architecture:** Python data pipeline fetches company data from public APIs (SEC EDGAR, Wikidata, OpenCorporates), normalizes and buckets it into static JSON. TypeScript SPA with Vite + D3.js renders an interactive dashboard with Sankey diagrams, dimension switching, and breadcrumb-driven drill-down.

**Tech Stack:** Python 3.11+ (requests, pytest), TypeScript, Vite, D3.js (d3-sankey), Vitest

---

## File Structure

### Python Data Pipeline (`data/`)

| File | Responsibility |
|------|---------------|
| `data/models.py` | Pydantic models for Company, SankeyNode, SankeyLink, SankeyData |
| `data/bucket.py` | Assign employee-size and revenue buckets to raw counts |
| `data/normalize.py` | Deduplicate companies, standardize industry names |
| `data/export.py` | Generate `companies.json` and `sankey-data.json` from normalized data |
| `data/sources/sec_edgar.py` | Fetch company data from SEC EDGAR XBRL API |
| `data/sources/wikidata.py` | Fetch company data from Wikidata SPARQL endpoint |
| `data/sources/opencorporates.py` | Fetch company data from OpenCorporates API |
| `data/pipeline.py` | Orchestrate fetch -> normalize -> bucket -> export |
| `data/requirements.txt` | Python dependencies |
| `data/tests/test_bucket.py` | Tests for bucketing logic |
| `data/tests/test_normalize.py` | Tests for normalization/dedup |
| `data/tests/test_export.py` | Tests for Sankey aggregate generation |
| `data/tests/test_models.py` | Tests for data models |

### TypeScript Frontend (`src/`)

| File | Responsibility |
|------|---------------|
| `src/types.ts` | TypeScript interfaces matching the JSON data model |
| `src/data.ts` | Load and filter JSON data, provide query functions |
| `src/sankey.ts` | D3 Sankey rendering: layout, draw, transitions, hover highlights |
| `src/controls.ts` | Dimension tab switching + breadcrumb navigation |
| `src/sidebar.ts` | Selection details panel: stats, counts, drill-down context |
| `src/main.ts` | App entry: wire up controls, sankey, sidebar; load data |
| `src/style.css` | All styles: dashboard layout, tabs, sidebar, Sankey colors |
| `public/index.html` | HTML shell with dashboard structure |
| `src/__tests__/data.test.ts` | Tests for data loading and filtering |
| `src/__tests__/sankey.test.ts` | Tests for Sankey node/link computation |

### Config

| File | Responsibility |
|------|---------------|
| `package.json` | Node deps, scripts (dev, build, test) |
| `tsconfig.json` | TypeScript config |
| `vite.config.ts` | Vite config |
| `.gitignore` | Ignore raw data, node_modules, dist |

---

## Chunk 1: Project Scaffolding + Python Data Models & Bucketing

### Task 1: Initialize project scaffolding

**Files:**
- Create: `data/requirements.txt`
- Create: `data/tests/__init__.py`
- Create: `data/__init__.py`
- Create: `data/sources/__init__.py`
- Create: `package.json`
- Create: `tsconfig.json`
- Create: `vite.config.ts`
- Modify: `.gitignore`

- [ ] **Step 1: Create Python data pipeline structure**

```bash
mkdir -p data/sources data/tests data/raw
touch data/__init__.py data/sources/__init__.py data/tests/__init__.py
```

- [ ] **Step 2: Write `data/requirements.txt`**

```
requests>=2.31.0
pydantic>=2.5.0
pytest>=7.4.0
```

- [ ] **Step 3: Create Python virtualenv and install deps**

```bash
cd data && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

- [ ] **Step 4: Initialize Node project**

```bash
npm init -y
npm install d3 d3-sankey
npm install -D typescript vite vitest @types/d3 @types/d3-sankey jsdom
```

- [ ] **Step 5: Write `tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "dist",
    "rootDir": "src",
    "types": ["vitest/globals"]
  },
  "include": ["src"]
}
```

- [ ] **Step 6: Write `vite.config.ts`**

```typescript
import { defineConfig } from 'vite';

export default defineConfig({
  root: '.',
  publicDir: 'public',
  build: {
    outDir: 'dist',
  },
});
```

- [ ] **Step 7: Add scripts to `package.json`**

Add to scripts section:
```json
{
  "dev": "vite",
  "build": "tsc && vite build",
  "test": "vitest run",
  "test:watch": "vitest"
}
```

Add vitest config:
```json
{
  "vitest": {
    "environment": "jsdom"
  }
}
```

- [ ] **Step 8: Update `.gitignore`**

```
.superpowers/
data/raw/
data/.venv/
node_modules/
dist/
public/data/companies.json
public/data/sankey-data.json
```

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: initialize project scaffolding with Python pipeline and Vite frontend"
```

---

### Task 2: Python data models

**Files:**
- Create: `data/models.py`
- Create: `data/tests/test_models.py`

- [ ] **Step 1: Write failing test for Company model**

`data/tests/test_models.py`:
```python
from data.models import Company


def test_company_with_all_fields():
    c = Company(
        id="sec-AAPL",
        name="Apple Inc.",
        industry="Technology",
        employeeCount=164000,
        employeeBucket="10K+",
        revenue=394328000000,
        revenueBucket="$1B+",
        country="US",
        source="sec-edgar",
    )
    assert c.name == "Apple Inc."
    assert c.industry == "Technology"
    assert c.employeeBucket == "10K+"


def test_company_with_null_fields():
    c = Company(
        id="wiki-123",
        name="Small Corp",
        industry="Retail",
        employeeCount=None,
        employeeBucket=None,
        revenue=None,
        revenueBucket=None,
        country="DE",
        source="wikidata",
    )
    assert c.employeeCount is None
    assert c.revenue is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd data && source .venv/bin/activate && python -m pytest tests/test_models.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'data.models'`

- [ ] **Step 3: Implement Company model**

`data/models.py`:
```python
from pydantic import BaseModel


class Company(BaseModel):
    id: str
    name: str
    industry: str
    employeeCount: int | None
    employeeBucket: str | None
    revenue: float | None
    revenueBucket: str | None
    country: str
    source: str


class SankeyNode(BaseModel):
    id: str
    label: str
    dimension: str


class SankeyLink(BaseModel):
    source: str
    target: str
    value: int


class SankeyData(BaseModel):
    dimensions: list[str]
    nodes: list[SankeyNode]
    links: list[SankeyLink]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd data && source .venv/bin/activate && python -m pytest tests/test_models.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add data/models.py data/tests/test_models.py
git commit -m "feat: add Pydantic data models for Company and Sankey types"
```

---

### Task 3: Bucketing logic

**Files:**
- Create: `data/bucket.py`
- Create: `data/tests/test_bucket.py`

- [ ] **Step 1: Write failing tests for employee bucketing**

`data/tests/test_bucket.py`:
```python
from data.bucket import assign_employee_bucket, assign_revenue_bucket


def test_employee_bucket_under_5():
    assert assign_employee_bucket(3) == "<5"


def test_employee_bucket_5_to_9():
    assert assign_employee_bucket(5) == "5-9"
    assert assign_employee_bucket(9) == "5-9"


def test_employee_bucket_10_to_19():
    assert assign_employee_bucket(10) == "10-19"
    assert assign_employee_bucket(19) == "10-19"


def test_employee_bucket_20_to_49():
    assert assign_employee_bucket(20) == "20-49"


def test_employee_bucket_50_to_99():
    assert assign_employee_bucket(50) == "50-99"


def test_employee_bucket_100_to_249():
    assert assign_employee_bucket(100) == "100-249"


def test_employee_bucket_250_to_499():
    assert assign_employee_bucket(250) == "250-499"


def test_employee_bucket_500_to_999():
    assert assign_employee_bucket(500) == "500-999"


def test_employee_bucket_1k_to_4999():
    assert assign_employee_bucket(1000) == "1K-4.9K"
    assert assign_employee_bucket(4999) == "1K-4.9K"


def test_employee_bucket_5k_to_9999():
    assert assign_employee_bucket(5000) == "5K-9.9K"


def test_employee_bucket_10k_plus():
    assert assign_employee_bucket(10000) == "10K+"
    assert assign_employee_bucket(500000) == "10K+"


def test_employee_bucket_none():
    assert assign_employee_bucket(None) is None


def test_revenue_bucket_under_1m():
    assert assign_revenue_bucket(500_000) == "<$1M"


def test_revenue_bucket_1_to_5m():
    assert assign_revenue_bucket(1_000_000) == "$1-5M"
    assert assign_revenue_bucket(4_999_999) == "$1-5M"


def test_revenue_bucket_5_to_10m():
    assert assign_revenue_bucket(5_000_000) == "$5-10M"


def test_revenue_bucket_10_to_50m():
    assert assign_revenue_bucket(10_000_000) == "$10-50M"


def test_revenue_bucket_50_to_100m():
    assert assign_revenue_bucket(50_000_000) == "$50-100M"


def test_revenue_bucket_100_to_500m():
    assert assign_revenue_bucket(100_000_000) == "$100-500M"


def test_revenue_bucket_500m_to_1b():
    assert assign_revenue_bucket(500_000_000) == "$500M-1B"


def test_revenue_bucket_1b_plus():
    assert assign_revenue_bucket(1_000_000_000) == "$1B+"
    assert assign_revenue_bucket(400_000_000_000) == "$1B+"


def test_revenue_bucket_none():
    assert assign_revenue_bucket(None) is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd data && source .venv/bin/activate && python -m pytest tests/test_bucket.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'data.bucket'`

- [ ] **Step 3: Implement bucketing functions**

`data/bucket.py`:
```python
EMPLOYEE_BUCKETS = [
    (5, "<5"),
    (10, "5-9"),
    (20, "10-19"),
    (50, "20-49"),
    (100, "50-99"),
    (250, "100-249"),
    (500, "250-499"),
    (1000, "500-999"),
    (5000, "1K-4.9K"),
    (10000, "5K-9.9K"),
]

REVENUE_BUCKETS = [
    (1_000_000, "<$1M"),
    (5_000_000, "$1-5M"),
    (10_000_000, "$5-10M"),
    (50_000_000, "$10-50M"),
    (100_000_000, "$50-100M"),
    (500_000_000, "$100-500M"),
    (1_000_000_000, "$500M-1B"),
]


def assign_employee_bucket(count: int | None) -> str | None:
    if count is None:
        return None
    for threshold, label in EMPLOYEE_BUCKETS:
        if count < threshold:
            return label
    return "10K+"


def assign_revenue_bucket(revenue: float | None) -> str | None:
    if revenue is None:
        return None
    for threshold, label in REVENUE_BUCKETS:
        if revenue < threshold:
            return label
    return "$1B+"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd data && source .venv/bin/activate && python -m pytest tests/test_bucket.py -v
```

Expected: All 20 tests pass

- [ ] **Step 5: Commit**

```bash
git add data/bucket.py data/tests/test_bucket.py
git commit -m "feat: add employee size and revenue bucketing logic"
```

---

### Task 4: Normalization logic

**Files:**
- Create: `data/normalize.py`
- Create: `data/tests/test_normalize.py`

- [ ] **Step 1: Write failing tests for industry normalization and dedup**

`data/tests/test_normalize.py`:
```python
from data.models import Company
from data.normalize import normalize_industry, deduplicate, normalize_companies

VALID_INDUSTRIES = [
    "Technology", "Healthcare", "Finance", "Manufacturing", "Retail",
    "Energy", "Transportation", "Telecommunications", "Real Estate",
    "Education", "Agriculture", "Entertainment", "Construction",
    "Professional Services",
]


def test_normalize_industry_exact_match():
    assert normalize_industry("Technology") == "Technology"


def test_normalize_industry_case_insensitive():
    assert normalize_industry("technology") == "Technology"
    assert normalize_industry("HEALTHCARE") == "Healthcare"


def test_normalize_industry_alias():
    assert normalize_industry("Tech") == "Technology"
    assert normalize_industry("Financial Services") == "Finance"
    assert normalize_industry("Banking") == "Finance"
    assert normalize_industry("Pharma") == "Healthcare"
    assert normalize_industry("Automotive") == "Manufacturing"


def test_normalize_industry_unknown():
    assert normalize_industry("Underwater Basket Weaving") == "Other"


def test_deduplicate_by_name():
    companies = [
        Company(id="a", name="Apple Inc.", industry="Technology",
                employeeCount=100, employeeBucket="50-99",
                revenue=None, revenueBucket=None, country="US", source="sec"),
        Company(id="b", name="Apple Inc.", industry="Technology",
                employeeCount=164000, employeeBucket="10K+",
                revenue=394e9, revenueBucket="$1B+", country="US", source="wiki"),
    ]
    result = deduplicate(companies)
    assert len(result) == 1
    # Prefer the record with more data (non-null fields)
    assert result[0].revenue == 394e9


def test_normalize_companies_applies_buckets_and_industry():
    companies = [
        Company(id="a", name="Test Corp", industry="tech",
                employeeCount=50, employeeBucket=None,
                revenue=2_000_000, revenueBucket=None,
                country="US", source="test"),
    ]
    result = normalize_companies(companies)
    assert result[0].industry == "Technology"
    assert result[0].employeeBucket == "50-99"
    assert result[0].revenueBucket == "$1-5M"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd data && source .venv/bin/activate && python -m pytest tests/test_normalize.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement normalization**

`data/normalize.py`:
```python
from data.models import Company
from data.bucket import assign_employee_bucket, assign_revenue_bucket

VALID_INDUSTRIES = [
    "Technology", "Healthcare", "Finance", "Manufacturing", "Retail",
    "Energy", "Transportation", "Telecommunications", "Real Estate",
    "Education", "Agriculture", "Entertainment", "Construction",
    "Professional Services",
]

INDUSTRY_ALIASES: dict[str, str] = {
    "tech": "Technology",
    "software": "Technology",
    "information technology": "Technology",
    "it": "Technology",
    "financial services": "Finance",
    "banking": "Finance",
    "insurance": "Finance",
    "pharma": "Healthcare",
    "pharmaceutical": "Healthcare",
    "biotech": "Healthcare",
    "medical": "Healthcare",
    "automotive": "Manufacturing",
    "industrial": "Manufacturing",
    "ecommerce": "Retail",
    "e-commerce": "Retail",
    "oil": "Energy",
    "oil & gas": "Energy",
    "utilities": "Energy",
    "media": "Entertainment",
    "telecom": "Telecommunications",
    "logistics": "Transportation",
    "shipping": "Transportation",
    "consulting": "Professional Services",
    "legal": "Professional Services",
    "accounting": "Professional Services",
    "property": "Real Estate",
    "farming": "Agriculture",
    "food": "Agriculture",
}

_INDUSTRY_LOOKUP: dict[str, str] = {
    name.lower(): name for name in VALID_INDUSTRIES
}
_INDUSTRY_LOOKUP.update({k.lower(): v for k, v in INDUSTRY_ALIASES.items()})


def normalize_industry(raw: str) -> str:
    return _INDUSTRY_LOOKUP.get(raw.lower().strip(), "Other")


def deduplicate(companies: list[Company]) -> list[Company]:
    by_name: dict[str, Company] = {}
    for c in companies:
        key = c.name.lower().strip()
        if key in by_name:
            existing = by_name[key]
            existing_nulls = sum(1 for v in [existing.employeeCount, existing.revenue] if v is None)
            new_nulls = sum(1 for v in [c.employeeCount, c.revenue] if v is None)
            if new_nulls < existing_nulls:
                by_name[key] = c
        else:
            by_name[key] = c
    return list(by_name.values())


def normalize_companies(companies: list[Company]) -> list[Company]:
    result = []
    for c in companies:
        normalized = c.model_copy(update={
            "industry": normalize_industry(c.industry),
            "employeeBucket": assign_employee_bucket(c.employeeCount),
            "revenueBucket": assign_revenue_bucket(c.revenue),
        })
        # Drop companies missing both employee count and revenue
        if normalized.employeeCount is None and normalized.revenue is None:
            continue
        result.append(normalized)
    return deduplicate(result)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd data && source .venv/bin/activate && python -m pytest tests/test_normalize.py -v
```

Expected: All 7 tests pass

- [ ] **Step 5: Commit**

```bash
git add data/normalize.py data/tests/test_normalize.py
git commit -m "feat: add industry normalization, aliasing, and deduplication"
```

---

### Task 5: Export / Sankey aggregate generation

**Files:**
- Create: `data/export.py`
- Create: `data/tests/test_export.py`

- [ ] **Step 1: Write failing tests for Sankey export**

`data/tests/test_export.py`:
```python
import json
from data.models import Company, SankeyData
from data.export import generate_sankey_data, export_to_files

SAMPLE_COMPANIES = [
    Company(id="1", name="TechCo", industry="Technology",
            employeeCount=150, employeeBucket="100-249",
            revenue=50_000_000, revenueBucket="$10-50M",
            country="US", source="test"),
    Company(id="2", name="TechSmall", industry="Technology",
            employeeCount=8, employeeBucket="5-9",
            revenue=2_000_000, revenueBucket="$1-5M",
            country="US", source="test"),
    Company(id="3", name="HealthBig", industry="Healthcare",
            employeeCount=5000, employeeBucket="1K-4.9K",
            revenue=500_000_000, revenueBucket="$100-500M",
            country="US", source="test"),
    Company(id="4", name="NoRevenue", industry="Technology",
            employeeCount=20, employeeBucket="10-19",
            revenue=None, revenueBucket=None,
            country="US", source="test"),
]


def test_generate_sankey_data_has_all_dimensions():
    data = generate_sankey_data(SAMPLE_COMPANIES)
    assert set(data.dimensions) == {"industry", "employeeBucket", "revenueBucket"}


def test_generate_sankey_data_nodes_include_industries():
    data = generate_sankey_data(SAMPLE_COMPANIES)
    node_ids = {n.id for n in data.nodes}
    assert "industry:Technology" in node_ids
    assert "industry:Healthcare" in node_ids


def test_generate_sankey_data_nodes_include_buckets():
    data = generate_sankey_data(SAMPLE_COMPANIES)
    node_ids = {n.id for n in data.nodes}
    assert "employeeBucket:100-249" in node_ids
    assert "revenueBucket:$10-50M" in node_ids


def test_generate_sankey_data_links_count():
    data = generate_sankey_data(SAMPLE_COMPANIES)
    # Find link from Technology -> 100-249 employees
    link = next(
        (l for l in data.links
         if l.source == "industry:Technology" and l.target == "employeeBucket:100-249"),
        None,
    )
    assert link is not None
    assert link.value == 1


def test_generate_sankey_data_excludes_null_from_relevant_links():
    data = generate_sankey_data(SAMPLE_COMPANIES)
    # NoRevenue company (id=4) should not appear in revenue links
    revenue_links = [l for l in data.links if "revenueBucket:" in l.target or "revenueBucket:" in l.source]
    total_revenue_companies = sum(l.value for l in revenue_links if l.source.startswith("industry:"))
    # Only 3 companies have revenue (not NoRevenue)
    assert total_revenue_companies == 3


def test_export_to_files(tmp_path):
    export_to_files(SAMPLE_COMPANIES, str(tmp_path))
    companies_path = tmp_path / "companies.json"
    sankey_path = tmp_path / "sankey-data.json"
    assert companies_path.exists()
    assert sankey_path.exists()

    companies = json.loads(companies_path.read_text())
    assert len(companies) == 4

    sankey = json.loads(sankey_path.read_text())
    assert "nodes" in sankey
    assert "links" in sankey
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd data && source .venv/bin/activate && python -m pytest tests/test_export.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement export logic**

`data/export.py`:
```python
import json
from pathlib import Path
from collections import defaultdict
from itertools import permutations

from data.models import Company, SankeyData, SankeyNode, SankeyLink

DIMENSION_FIELDS = {
    "industry": "industry",
    "employeeBucket": "employeeBucket",
    "revenueBucket": "revenueBucket",
}


def _get_value(company: Company, dimension: str) -> str | None:
    return getattr(company, DIMENSION_FIELDS[dimension])


def generate_sankey_data(companies: list[Company]) -> SankeyData:
    nodes_set: set[tuple[str, str, str]] = set()  # (id, label, dimension)
    link_counts: defaultdict[tuple[str, str], int] = defaultdict(int)

    dims = list(DIMENSION_FIELDS.keys())

    # Generate links for all pairs and triples
    for perm in permutations(dims, 2):
        source_dim, target_dim = perm
        for c in companies:
            source_val = _get_value(c, source_dim)
            target_val = _get_value(c, target_dim)
            if source_val is None or target_val is None:
                continue
            source_id = f"{source_dim}:{source_val}"
            target_id = f"{target_dim}:{target_val}"
            nodes_set.add((source_id, source_val, source_dim))
            nodes_set.add((target_id, target_val, target_dim))
            link_counts[(source_id, target_id)] += 1

    nodes = [SankeyNode(id=nid, label=label, dimension=dim) for nid, label, dim in sorted(nodes_set)]
    links = [SankeyLink(source=s, target=t, value=v) for (s, t), v in sorted(link_counts.items())]

    return SankeyData(dimensions=dims, nodes=nodes, links=links)


def export_to_files(companies: list[Company], output_dir: str) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Write companies.json
    companies_data = [c.model_dump() for c in companies]
    (out / "companies.json").write_text(json.dumps(companies_data, indent=2))

    # Write sankey-data.json
    sankey = generate_sankey_data(companies)
    (out / "sankey-data.json").write_text(json.dumps(sankey.model_dump(), indent=2))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd data && source .venv/bin/activate && python -m pytest tests/test_export.py -v
```

Expected: All 6 tests pass

- [ ] **Step 5: Commit**

```bash
git add data/export.py data/tests/test_export.py
git commit -m "feat: add Sankey aggregate generation and JSON export"
```

---

## Chunk 2: Data Source Fetchers + Pipeline Orchestration

### Task 6: SEC EDGAR fetcher

**Files:**
- Create: `data/sources/sec_edgar.py`
- Create: `data/tests/test_sec_edgar.py`

- [ ] **Step 1: Write failing test for SEC EDGAR parser**

`data/tests/test_sec_edgar.py`:
```python
from data.sources.sec_edgar import parse_edgar_company
from data.models import Company

SAMPLE_FILING = {
    "cik": "0000320193",
    "entityName": "Apple Inc.",
    "sic": "3571",
    "sicDescription": "Electronic Computers",
    "facts": {
        "dei": {
            "EntityCommonStockSharesOutstanding": {},
        },
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"val": 394328000000, "fy": 2022, "form": "10-K"}
                    ]
                }
            },
            "EntityNumberOfEmployees": {
                "units": {
                    "pure": [
                        {"val": 164000, "fy": 2022, "form": "10-K"}
                    ]
                }
            },
        }
    }
}


def test_parse_edgar_company():
    result = parse_edgar_company(SAMPLE_FILING)
    assert result is not None
    assert result.name == "Apple Inc."
    assert result.employeeCount == 164000
    assert result.revenue == 394328000000
    assert result.source == "sec-edgar"
    assert result.industry == "Technology"  # Mapped from SIC 3571


def test_parse_edgar_company_missing_revenue():
    filing = {
        "cik": "0000001234",
        "entityName": "NoRev Corp",
        "sic": "9999",
        "facts": {"us-gaap": {}},
    }
    result = parse_edgar_company(filing)
    assert result is not None
    assert result.revenue is None
    assert result.industry == "Other"  # Unknown SIC maps to Other
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd data && source .venv/bin/activate && python -m pytest tests/test_sec_edgar.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement SEC EDGAR fetcher**

`data/sources/sec_edgar.py`:
```python
"""Fetch company data from SEC EDGAR XBRL company facts API.

SEC EDGAR provides free access to company filings. The companyfacts endpoint
returns structured XBRL data including revenue and employee counts from 10-K filings.

API docs: https://www.sec.gov/edgar/sec-api-documentation
Rate limit: 10 requests/second, requires User-Agent header.
"""
import time
import requests
from data.models import Company

EDGAR_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
EDGAR_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
USER_AGENT = "IndustrySizeGraph/1.0 (research@example.com)"

# Map SIC code prefixes (first 2 digits) to normalized industry names
SIC_TO_INDUSTRY: dict[str, str] = {
    "01": "Agriculture", "02": "Agriculture", "07": "Agriculture", "08": "Agriculture", "09": "Agriculture",
    "10": "Energy", "12": "Energy", "13": "Energy", "14": "Energy", "29": "Energy",
    "15": "Construction", "16": "Construction", "17": "Construction",
    "20": "Manufacturing", "21": "Manufacturing", "22": "Manufacturing", "23": "Manufacturing",
    "24": "Manufacturing", "25": "Manufacturing", "26": "Manufacturing", "27": "Manufacturing",
    "30": "Manufacturing", "31": "Manufacturing", "32": "Manufacturing", "33": "Manufacturing",
    "34": "Manufacturing", "37": "Manufacturing", "38": "Manufacturing", "39": "Manufacturing",
    "35": "Technology", "36": "Technology", "73": "Technology",
    "28": "Healthcare", "80": "Healthcare",
    "40": "Transportation", "41": "Transportation", "42": "Transportation",
    "44": "Transportation", "45": "Transportation", "46": "Transportation", "47": "Transportation",
    "48": "Telecommunications",
    "49": "Energy",
    "50": "Retail", "51": "Retail", "52": "Retail", "53": "Retail",
    "54": "Retail", "55": "Retail", "56": "Retail", "57": "Retail", "58": "Retail", "59": "Retail",
    "60": "Finance", "61": "Finance", "62": "Finance", "63": "Finance", "64": "Finance", "67": "Finance",
    "65": "Real Estate",
    "70": "Entertainment", "78": "Entertainment", "79": "Entertainment",
    "82": "Education",
    "87": "Professional Services", "89": "Professional Services",
}


def _sic_to_industry(sic: str) -> str:
    """Map a 4-digit SIC code to a normalized industry name."""
    prefix = sic[:2]
    return SIC_TO_INDUSTRY.get(prefix, "Other")


def _extract_latest_10k_value(facts: dict, namespace: str, field: str) -> float | None:
    """Extract the most recent 10-K value for a given XBRL field."""
    ns_data = facts.get(namespace, {})
    field_data = ns_data.get(field, {})
    units = field_data.get("units", {})
    for unit_type in units.values():
        ten_k_values = [e for e in unit_type if e.get("form") == "10-K"]
        if ten_k_values:
            latest = max(ten_k_values, key=lambda e: e.get("fy", 0))
            return latest["val"]
    return None


def parse_edgar_company(filing: dict) -> Company | None:
    """Parse a single SEC EDGAR company facts response into a Company."""
    cik = str(filing.get("cik", "")).lstrip("0")
    name = filing.get("entityName", "Unknown")
    facts = filing.get("facts", {})

    # Map SIC code to industry
    sic = str(filing.get("sic", ""))
    industry = _sic_to_industry(sic) if sic else "Other"

    revenue = (
        _extract_latest_10k_value(facts, "us-gaap", "Revenues")
        or _extract_latest_10k_value(facts, "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax")
        or _extract_latest_10k_value(facts, "us-gaap", "SalesRevenueNet")
    )

    employee_count_raw = _extract_latest_10k_value(facts, "dei", "EntityNumberOfEmployees")
    if employee_count_raw is None:
        employee_count_raw = _extract_latest_10k_value(facts, "us-gaap", "EntityNumberOfEmployees")
    employee_count = int(employee_count_raw) if employee_count_raw is not None else None

    return Company(
        id=f"sec-{cik}",
        name=name,
        industry=industry,
        employeeCount=employee_count,
        employeeBucket=None,
        revenue=revenue,
        revenueBucket=None,
        country="US",
        source="sec-edgar",
    )


def fetch_edgar_companies(max_companies: int = 500) -> list[Company]:
    """Fetch company data from SEC EDGAR. Returns list of Company objects."""
    headers = {"User-Agent": USER_AGENT}

    # Get list of company CIKs
    resp = requests.get(EDGAR_COMPANY_TICKERS_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    tickers = resp.json()

    companies: list[Company] = []
    for _key, info in list(tickers.items())[:max_companies]:
        cik = str(info["cik_str"]).zfill(10)
        try:
            facts_resp = requests.get(
                EDGAR_COMPANY_FACTS_URL.format(cik=cik),
                headers=headers,
                timeout=30,
            )
            if facts_resp.status_code != 200:
                continue
            filing = facts_resp.json()
            # SIC code may come from tickers list or filing itself
            if "sic" not in filing and "sic" in info:
                filing["sic"] = str(info["sic"])
            company = parse_edgar_company(filing)
            if company is not None:
                companies.append(company)
        except (requests.RequestException, KeyError, ValueError):
            continue
        time.sleep(0.12)  # Respect 10 req/sec rate limit

    return companies
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd data && source .venv/bin/activate && python -m pytest tests/test_sec_edgar.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add data/sources/sec_edgar.py data/tests/test_sec_edgar.py
git commit -m "feat: add SEC EDGAR data fetcher with XBRL parsing"
```

---

### Task 7: Wikidata fetcher

**Files:**
- Create: `data/sources/wikidata.py`
- Create: `data/tests/test_wikidata.py`

- [ ] **Step 1: Write failing test for Wikidata result parser**

`data/tests/test_wikidata.py`:
```python
from data.sources.wikidata import parse_wikidata_result
from data.models import Company

SAMPLE_RESULT = {
    "company": {"value": "http://www.wikidata.org/entity/Q312"},
    "companyLabel": {"value": "Apple Inc."},
    "industryLabel": {"value": "technology company"},
    "employees": {"value": "164000"},
    "revenue": {"value": "394328000000"},
    "countryLabel": {"value": "United States of America"},
}


def test_parse_wikidata_result():
    result = parse_wikidata_result(SAMPLE_RESULT)
    assert result.name == "Apple Inc."
    assert result.employeeCount == 164000
    assert result.revenue == 394328000000
    assert result.source == "wikidata"
    assert result.id == "wiki-Q312"


def test_parse_wikidata_result_missing_optional():
    minimal = {
        "company": {"value": "http://www.wikidata.org/entity/Q999"},
        "companyLabel": {"value": "SmallCo"},
        "industryLabel": {"value": "retail"},
        "countryLabel": {"value": "Germany"},
    }
    result = parse_wikidata_result(minimal)
    assert result.employeeCount is None
    assert result.revenue is None
    assert result.country == "Germany"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd data && source .venv/bin/activate && python -m pytest tests/test_wikidata.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement Wikidata fetcher**

`data/sources/wikidata.py`:
```python
"""Fetch company data from Wikidata SPARQL endpoint.

Wikidata provides structured data about companies including industry,
employee count, revenue, and country. Uses the public SPARQL endpoint.
"""
import requests
from data.models import Company

WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"

SPARQL_QUERY = """
SELECT ?company ?companyLabel ?industryLabel ?employees ?revenue ?countryLabel WHERE {
  ?company wdt:P31 wd:Q4830453.       # instance of business enterprise
  ?company wdt:P452 ?industry.         # industry
  ?company wdt:P17 ?country.           # country
  OPTIONAL { ?company wdt:P1128 ?employees. }  # employees
  OPTIONAL { ?company wdt:P2139 ?revenue. }    # revenue
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT %d
"""

COUNTRY_CODES: dict[str, str] = {
    "United States of America": "US",
    "United Kingdom": "GB",
    "Germany": "DE",
    "France": "FR",
    "Japan": "JP",
    "China": "CN",
    "Canada": "CA",
    "Australia": "AU",
    "India": "IN",
    "Brazil": "BR",
}


def parse_wikidata_result(result: dict) -> Company:
    """Parse a single Wikidata SPARQL result binding into a Company."""
    entity_url = result["company"]["value"]
    entity_id = entity_url.split("/")[-1]
    name = result["companyLabel"]["value"]
    industry = result.get("industryLabel", {}).get("value", "Other")
    country_name = result.get("countryLabel", {}).get("value", "Unknown")
    country_code = COUNTRY_CODES.get(country_name, country_name)

    employees_raw = result.get("employees", {}).get("value")
    employee_count = int(float(employees_raw)) if employees_raw else None

    revenue_raw = result.get("revenue", {}).get("value")
    revenue = float(revenue_raw) if revenue_raw else None

    return Company(
        id=f"wiki-{entity_id}",
        name=name,
        industry=industry,
        employeeCount=employee_count,
        employeeBucket=None,
        revenue=revenue,
        revenueBucket=None,
        country=country_code,
        source="wikidata",
    )


def fetch_wikidata_companies(limit: int = 2000) -> list[Company]:
    """Fetch company data from Wikidata SPARQL endpoint."""
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": "IndustrySizeGraph/1.0",
    }
    params = {"query": SPARQL_QUERY % limit}

    resp = requests.get(WIKIDATA_SPARQL_URL, headers=headers, params=params, timeout=60)
    resp.raise_for_status()
    results = resp.json().get("results", {}).get("bindings", [])

    companies = []
    for r in results:
        try:
            companies.append(parse_wikidata_result(r))
        except (KeyError, ValueError):
            continue
    return companies
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd data && source .venv/bin/activate && python -m pytest tests/test_wikidata.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add data/sources/wikidata.py data/tests/test_wikidata.py
git commit -m "feat: add Wikidata SPARQL fetcher"
```

---

### Task 8: OpenCorporates fetcher

**Files:**
- Create: `data/sources/opencorporates.py`
- Create: `data/tests/test_opencorporates.py`

- [ ] **Step 1: Write failing test for OpenCorporates parser**

`data/tests/test_opencorporates.py`:
```python
from data.sources.opencorporates import parse_oc_company
from data.models import Company

SAMPLE_COMPANY = {
    "company": {
        "company_number": "00445790",
        "name": "Tesco PLC",
        "jurisdiction_code": "gb",
        "industry_codes": [
            {"code": "47110", "description": "Retail sale in non-specialised stores"}
        ],
        "number_of_employees": "360000",
        "current_status": "Active",
    }
}


def test_parse_oc_company():
    result = parse_oc_company(SAMPLE_COMPANY["company"])
    assert result.name == "Tesco PLC"
    assert result.employeeCount == 360000
    assert result.country == "GB"
    assert result.source == "opencorporates"


def test_parse_oc_company_no_employees():
    company = {
        "company_number": "999",
        "name": "Mystery Corp",
        "jurisdiction_code": "us_ca",
        "industry_codes": [],
    }
    result = parse_oc_company(company)
    assert result.employeeCount is None
    assert result.country == "US"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd data && source .venv/bin/activate && python -m pytest tests/test_opencorporates.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement OpenCorporates fetcher**

`data/sources/opencorporates.py`:
```python
"""Fetch company data from OpenCorporates API.

OpenCorporates aggregates company registry data globally. Free tier allows
basic company searches. API docs: https://api.opencorporates.com/documentation
"""
import requests
from data.models import Company

OC_SEARCH_URL = "https://api.opencorporates.com/v0.4/companies/search"


def parse_oc_company(company: dict) -> Company:
    """Parse a single OpenCorporates company object into a Company."""
    name = company.get("name", "Unknown")
    number = company.get("company_number", "0")
    jurisdiction = company.get("jurisdiction_code", "")

    # Extract country code from jurisdiction (e.g., "gb" -> "GB", "us_ca" -> "US")
    country = jurisdiction.split("_")[0].upper() if jurisdiction else "XX"

    # Extract industry from industry codes if available
    industry_codes = company.get("industry_codes", [])
    industry = "Other"
    if industry_codes:
        industry = industry_codes[0].get("description", "Other")

    employees_raw = company.get("number_of_employees")
    employee_count = int(employees_raw) if employees_raw else None

    return Company(
        id=f"oc-{jurisdiction}-{number}",
        name=name,
        industry=industry,
        employeeCount=employee_count,
        employeeBucket=None,
        revenue=None,  # OpenCorporates doesn't provide revenue
        revenueBucket=None,
        country=country,
        source="opencorporates",
    )


def fetch_oc_companies(max_pages: int = 10) -> list[Company]:
    """Fetch company data from OpenCorporates search API."""
    companies: list[Company] = []
    for page in range(1, max_pages + 1):
        try:
            resp = requests.get(
                OC_SEARCH_URL,
                params={"q": "*", "page": page, "per_page": 100},
                timeout=30,
            )
            if resp.status_code != 200:
                break
            results = resp.json().get("results", {}).get("companies", [])
            if not results:
                break
            for item in results:
                try:
                    companies.append(parse_oc_company(item["company"]))
                except (KeyError, ValueError):
                    continue
        except requests.RequestException:
            break
    return companies
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd data && source .venv/bin/activate && python -m pytest tests/test_opencorporates.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add data/sources/opencorporates.py data/tests/test_opencorporates.py
git commit -m "feat: add OpenCorporates data fetcher"
```

---

### Task 9: Pipeline orchestrator

**Files:**
- Create: `data/pipeline.py`
- Create: `data/tests/test_pipeline.py`

- [ ] **Step 1: Write failing test for pipeline with mocked fetchers**

`data/tests/test_pipeline.py`:
```python
import json
from unittest.mock import patch
from data.pipeline import run_pipeline
from data.models import Company


def _mock_companies(source: str, count: int) -> list[Company]:
    return [
        Company(
            id=f"{source}-{i}", name=f"{source} Corp {i}", industry="Technology",
            employeeCount=100 * (i + 1), employeeBucket=None,
            revenue=1_000_000 * (i + 1), revenueBucket=None,
            country="US", source=source,
        )
        for i in range(count)
    ]


@patch("data.pipeline.fetch_oc_companies", return_value=_mock_companies("oc", 2))
@patch("data.pipeline.fetch_wikidata_companies", return_value=_mock_companies("wiki", 3))
@patch("data.pipeline.fetch_edgar_companies", return_value=_mock_companies("edgar", 2))
def test_run_pipeline_produces_output_files(mock_edgar, mock_wiki, mock_oc, tmp_path):
    run_pipeline(str(tmp_path), max_edgar=2, max_wikidata=3, max_oc_pages=1)

    assert (tmp_path / "companies.json").exists()
    assert (tmp_path / "sankey-data.json").exists()

    companies = json.loads((tmp_path / "companies.json").read_text())
    assert len(companies) == 7  # 2 + 3 + 2, no duplicates

    sankey = json.loads((tmp_path / "sankey-data.json").read_text())
    assert len(sankey["nodes"]) > 0
    assert len(sankey["links"]) > 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd data && source .venv/bin/activate && python -m pytest tests/test_pipeline.py -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement pipeline orchestrator**

`data/pipeline.py`:
```python
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
```

- [ ] **Step 2: Run all Python tests to ensure nothing is broken**

```bash
cd data && source .venv/bin/activate && python -m pytest -v
```

Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add data/pipeline.py data/tests/test_pipeline.py
git commit -m "feat: add pipeline orchestrator for fetch-normalize-export flow"
```

---

## Chunk 3: Frontend - Types, Data Layer, HTML Shell, Styles

### Task 10: TypeScript types and data layer

**Files:**
- Create: `src/types.ts`
- Create: `src/data.ts`
- Create: `src/__tests__/data.test.ts`

- [ ] **Step 1: Write TypeScript types**

`src/types.ts`:
```typescript
export interface Company {
  id: string;
  name: string;
  industry: string;
  employeeCount: number | null;
  employeeBucket: string | null;
  revenue: number | null;
  revenueBucket: string | null;
  country: string;
  source: string;
}

export interface SankeyNode {
  id: string;
  label: string;
  dimension: string;
}

export interface SankeyLink {
  source: string;
  target: string;
  value: number;
}

export interface SankeyData {
  dimensions: string[];
  nodes: SankeyNode[];
  links: SankeyLink[];
}

export type Dimension = 'industry' | 'employeeBucket' | 'revenueBucket';

export interface DrillState {
  /** The ordered sequence of dimensions as the user drills down */
  path: Dimension[];
  /** The selected values at each level (e.g., ["Technology", "100-249"]) */
  selections: string[];
}
```

- [ ] **Step 2: Write failing test for data filtering**

`src/__tests__/data.test.ts`:
```typescript
import { describe, it, expect } from 'vitest';
import { filterSankeyForDrill, getAvailableDimensions } from '../data';
import type { SankeyData, DrillState } from '../types';

const MOCK_DATA: SankeyData = {
  dimensions: ['industry', 'employeeBucket', 'revenueBucket'],
  nodes: [
    { id: 'industry:Technology', label: 'Technology', dimension: 'industry' },
    { id: 'industry:Healthcare', label: 'Healthcare', dimension: 'industry' },
    { id: 'employeeBucket:100-249', label: '100-249', dimension: 'employeeBucket' },
    { id: 'employeeBucket:5-9', label: '5-9', dimension: 'employeeBucket' },
    { id: 'revenueBucket:$10-50M', label: '$10-50M', dimension: 'revenueBucket' },
    { id: 'revenueBucket:$1-5M', label: '$1-5M', dimension: 'revenueBucket' },
  ],
  links: [
    { source: 'industry:Technology', target: 'employeeBucket:100-249', value: 10 },
    { source: 'industry:Technology', target: 'employeeBucket:5-9', value: 5 },
    { source: 'industry:Healthcare', target: 'employeeBucket:100-249', value: 8 },
    { source: 'employeeBucket:100-249', target: 'revenueBucket:$10-50M', value: 12 },
    { source: 'employeeBucket:5-9', target: 'revenueBucket:$1-5M', value: 3 },
    { source: 'industry:Technology', target: 'revenueBucket:$10-50M', value: 7 },
    { source: 'industry:Technology', target: 'revenueBucket:$1-5M', value: 3 },
  ],
};

describe('filterSankeyForDrill', () => {
  it('returns top-level links between two dimensions', () => {
    const state: DrillState = { path: ['industry', 'employeeBucket'], selections: [] };
    const result = filterSankeyForDrill(MOCK_DATA, state);
    expect(result.links.length).toBe(3);
    expect(result.links.every(l => l.source.startsWith('industry:'))).toBe(true);
    expect(result.links.every(l => l.target.startsWith('employeeBucket:'))).toBe(true);
  });

  it('filters to selected node when drilling down', () => {
    const state: DrillState = {
      path: ['industry', 'revenueBucket'],
      selections: ['Technology'],
    };
    const result = filterSankeyForDrill(MOCK_DATA, state);
    expect(result.links.every(l => l.source === 'industry:Technology')).toBe(true);
    expect(result.links.every(l => l.target.startsWith('revenueBucket:'))).toBe(true);
  });
});

describe('getAvailableDimensions', () => {
  it('returns dimensions not yet in the path', () => {
    const result = getAvailableDimensions(['industry']);
    expect(result).toEqual(['employeeBucket', 'revenueBucket']);
  });

  it('returns one dimension when two are used', () => {
    const result = getAvailableDimensions(['industry', 'employeeBucket']);
    expect(result).toEqual(['revenueBucket']);
  });
});
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
npx vitest run src/__tests__/data.test.ts
```

Expected: FAIL with module not found

- [ ] **Step 4: Implement data layer**

`src/data.ts`:
```typescript
import type { SankeyData, SankeyNode, SankeyLink, DrillState, Dimension } from './types';

const ALL_DIMENSIONS: Dimension[] = ['industry', 'employeeBucket', 'revenueBucket'];

let cachedData: SankeyData | null = null;

export async function loadSankeyData(): Promise<SankeyData> {
  if (cachedData) return cachedData;
  const resp = await fetch('/data/sankey-data.json');
  cachedData = await resp.json();
  return cachedData!;
}

export function getAvailableDimensions(usedDimensions: Dimension[]): Dimension[] {
  return ALL_DIMENSIONS.filter(d => !usedDimensions.includes(d));
}

export interface FilteredSankey {
  nodes: SankeyNode[];
  links: SankeyLink[];
}

export function filterSankeyForDrill(data: SankeyData, state: DrillState): FilteredSankey {
  const sourceDim = state.path[0];
  const targetDim = state.path[state.path.length - 1];

  // Get links between source and target dimensions
  let links = data.links.filter(
    l => l.source.startsWith(`${sourceDim}:`) && l.target.startsWith(`${targetDim}:`)
  );

  // Apply selection filters
  for (let i = 0; i < state.selections.length; i++) {
    const dim = state.path[i];
    const selectedValue = state.selections[i];
    const selectedId = `${dim}:${selectedValue}`;
    links = links.filter(l => l.source === selectedId || l.target === selectedId);
  }

  // Collect referenced nodes
  const nodeIds = new Set<string>();
  for (const l of links) {
    nodeIds.add(l.source);
    nodeIds.add(l.target);
  }
  const nodes = data.nodes.filter(n => nodeIds.has(n.id));

  return { nodes, links };
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
npx vitest run src/__tests__/data.test.ts
```

Expected: All 4 tests pass

- [ ] **Step 6: Commit**

```bash
git add src/types.ts src/data.ts src/__tests__/data.test.ts
git commit -m "feat: add TypeScript types and data filtering layer"
```

---

### Task 11: HTML shell and CSS styles

**Files:**
- Create: `public/index.html`
- Create: `src/style.css`

- [ ] **Step 1: Write HTML shell**

`public/index.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Industry Size Graph</title>
  <link rel="stylesheet" href="/src/style.css" />
</head>
<body>
  <div id="app">
    <header id="topbar">
      <h1>Industry Size Graph</h1>
      <nav id="dimension-tabs">
        <button class="tab active" data-dimension="industry">Industry</button>
        <button class="tab" data-dimension="employeeBucket">Company Size</button>
        <button class="tab" data-dimension="revenueBucket">Revenue</button>
      </nav>
    </header>
    <div id="breadcrumb"></div>
    <main id="content">
      <div id="sankey-container">
        <svg id="sankey-svg"></svg>
      </div>
      <aside id="sidebar">
        <h2>Details</h2>
        <div id="sidebar-content">
          <p class="placeholder">Select a node to see details</p>
        </div>
      </aside>
    </main>
  </div>
  <script type="module" src="/src/main.ts"></script>
</body>
</html>
```

- [ ] **Step 2: Write CSS styles**

`src/style.css`:
```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  --bg: #0f172a;
  --surface: #1e293b;
  --border: #334155;
  --text: #e2e8f0;
  --text-muted: #94a3b8;
  --accent: #6366f1;
  --accent-hover: #818cf8;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
}

#app {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

/* Top bar */
#topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}

#topbar h1 {
  font-size: 18px;
  font-weight: 600;
}

#dimension-tabs {
  display: flex;
  gap: 8px;
}

.tab {
  padding: 6px 16px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.tab:hover {
  border-color: var(--accent);
  color: var(--text);
}

.tab.active {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

/* Breadcrumb */
#breadcrumb {
  padding: 8px 24px;
  font-size: 13px;
  color: var(--text-muted);
  display: flex;
  gap: 8px;
  align-items: center;
  min-height: 36px;
}

#breadcrumb .crumb {
  cursor: pointer;
  color: var(--accent);
  transition: color 0.2s;
}

#breadcrumb .crumb:hover {
  color: var(--accent-hover);
}

#breadcrumb .separator {
  color: var(--border);
}

/* Main content */
#content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

#sankey-container {
  flex: 1;
  padding: 24px;
  overflow: hidden;
}

#sankey-svg {
  width: 100%;
  height: 100%;
}

/* Sankey node styles */
.sankey-node rect {
  cursor: pointer;
  transition: opacity 0.2s;
}

.sankey-node rect:hover {
  opacity: 0.8;
}

.sankey-node text {
  fill: var(--text);
  font-size: 12px;
  pointer-events: none;
}

.sankey-link {
  fill: none;
  stroke-opacity: 0.3;
  transition: stroke-opacity 0.2s;
}

.sankey-link:hover {
  stroke-opacity: 0.6;
}

.sankey-link.highlighted {
  stroke-opacity: 0.6;
}

.sankey-link.dimmed {
  stroke-opacity: 0.1;
}

/* Tooltip */
.tooltip {
  position: absolute;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
  pointer-events: none;
  z-index: 100;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.tooltip .label {
  font-weight: 600;
}

.tooltip .value {
  color: var(--text-muted);
}

/* Sidebar */
#sidebar {
  width: 260px;
  border-left: 1px solid var(--border);
  background: var(--surface);
  padding: 20px;
  overflow-y: auto;
}

#sidebar h2 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
}

.placeholder {
  color: var(--text-muted);
  font-size: 14px;
}

.sidebar-stat {
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  margin-bottom: 8px;
}

.sidebar-stat .stat-label {
  font-size: 13px;
  font-weight: 500;
}

.sidebar-stat .stat-value {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

/* Responsive */
@media (max-width: 768px) {
  #content {
    flex-direction: column;
  }
  #sidebar {
    width: 100%;
    border-left: none;
    border-top: 1px solid var(--border);
    max-height: 200px;
  }
}
```

- [ ] **Step 3: Create placeholder data directory**

```bash
mkdir -p public/data
```

- [ ] **Step 4: Verify dev server starts**

```bash
npx vite --open
```

Expected: Browser opens showing the dark dashboard layout with header, tabs, empty Sankey area, and sidebar. Stop the server after verifying.

- [ ] **Step 5: Commit**

```bash
git add public/index.html src/style.css
git commit -m "feat: add dashboard HTML shell and dark theme styles"
```

---

## Chunk 4: Frontend - Sankey Rendering, Controls, Sidebar, App Wiring

### Task 12: Sankey rendering with D3

**Files:**
- Create: `src/sankey.ts`

- [ ] **Step 1: Implement Sankey renderer**

`src/sankey.ts`:
```typescript
import * as d3 from 'd3';
import { sankey, sankeyLinkHorizontal, SankeyGraph } from 'd3-sankey';
import type { SankeyNode } from './types';
import type { FilteredSankey } from './data';

// Color palette for dimensions
const DIMENSION_COLORS: Record<string, readonly string[]> = {
  industry: ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#7c3aed',
             '#4f46e5', '#5b21b6', '#7e22ce', '#9333ea', '#a855f7',
             '#6d28d9', '#4338ca', '#3730a3', '#312e81'],
  employeeBucket: ['#22d3ee', '#06b6d4', '#0891b2', '#0e7490', '#155e75',
                    '#164e63', '#0d9488', '#14b8a6', '#2dd4bf', '#5eead4',
                    '#99f6e4'],
  revenueBucket: ['#f59e0b', '#d97706', '#b45309', '#92400e', '#78350f',
                  '#f97316', '#ea580c', '#c2410c'],
};

interface SankeyCallbacks {
  onNodeClick: (node: SankeyNode) => void;
  onNodeHover: (node: SankeyNode | null) => void;
}

interface D3SankeyNode extends SankeyNode {
  x0?: number;
  x1?: number;
  y0?: number;
  y1?: number;
}

interface D3SankeyLink {
  source: D3SankeyNode;
  target: D3SankeyNode;
  value: number;
  width?: number;
}

export function renderSankey(
  svgElement: SVGSVGElement,
  data: FilteredSankey,
  callbacks: SankeyCallbacks,
): void {
  const svg = d3.select(svgElement);
  const { width, height } = svgElement.getBoundingClientRect();

  if (width === 0 || height === 0) return;

  svg.selectAll('*').remove();

  if (data.nodes.length === 0 || data.links.length === 0) {
    svg.append('text')
      .attr('x', width / 2)
      .attr('y', height / 2)
      .attr('text-anchor', 'middle')
      .attr('fill', '#94a3b8')
      .text('No data to display');
    return;
  }

  const nodeMap = new Map(data.nodes.map((n, i) => [n.id, i]));
  const graphNodes = data.nodes.map(n => ({ ...n }));
  const graphLinks = data.links
    .filter(l => nodeMap.has(l.source) && nodeMap.has(l.target))
    .map(l => ({
      source: nodeMap.get(l.source)!,
      target: nodeMap.get(l.target)!,
      value: l.value,
    }));

  const sankeyLayout = sankey<D3SankeyNode, any>()
    .nodeId((_d: any, i: number) => i)
    .nodeWidth(20)
    .nodePadding(12)
    .extent([[1, 1], [width - 1, height - 6]]);

  const graph = sankeyLayout({
    nodes: graphNodes,
    links: graphLinks,
  } as any) as SankeyGraph<D3SankeyNode, D3SankeyLink>;

  function getNodeColor(node: D3SankeyNode): string {
    const colors = DIMENSION_COLORS[node.dimension] || DIMENSION_COLORS.industry;
    const nodesInDim = graph.nodes.filter(n => n.dimension === node.dimension);
    const idx = nodesInDim.indexOf(node);
    return colors[idx % colors.length];
  }

  // Draw links
  const linkGroup = svg.append('g').attr('class', 'links');
  const linkPaths = linkGroup.selectAll('.sankey-link')
    .data(graph.links)
    .join('path')
    .attr('class', 'sankey-link')
    .attr('d', sankeyLinkHorizontal())
    .attr('stroke', (d: D3SankeyLink) => getNodeColor(d.source))
    .attr('stroke-width', (d: D3SankeyLink) => Math.max(1, d.width || 1));

  // Draw nodes
  const nodeGroup = svg.append('g').attr('class', 'nodes');
  const nodeElements = nodeGroup.selectAll('.sankey-node')
    .data(graph.nodes)
    .join('g')
    .attr('class', 'sankey-node')
    .attr('transform', (d: D3SankeyNode) => `translate(${d.x0},${d.y0})`);

  nodeElements.append('rect')
    .attr('height', (d: D3SankeyNode) => (d.y1! - d.y0!))
    .attr('width', sankeyLayout.nodeWidth())
    .attr('fill', (d: D3SankeyNode) => getNodeColor(d))
    .attr('rx', 3)
    .on('click', (_event: MouseEvent, d: D3SankeyNode) => {
      callbacks.onNodeClick(d);
    })
    .on('mouseenter', (_event: MouseEvent, d: D3SankeyNode) => {
      // Highlight connected links
      linkPaths
        .classed('highlighted', (l: D3SankeyLink) => l.source === d || l.target === d)
        .classed('dimmed', (l: D3SankeyLink) => l.source !== d && l.target !== d);
      callbacks.onNodeHover(d);
    })
    .on('mouseleave', () => {
      linkPaths.classed('highlighted', false).classed('dimmed', false);
      callbacks.onNodeHover(null);
    });

  // Add labels
  nodeElements.append('text')
    .attr('x', (d: D3SankeyNode) => (d.x0! < width / 2 ? sankeyLayout.nodeWidth() + 6 : -6))
    .attr('y', (d: D3SankeyNode) => (d.y1! - d.y0!) / 2)
    .attr('dy', '0.35em')
    .attr('text-anchor', (d: D3SankeyNode) => (d.x0! < width / 2 ? 'start' : 'end'))
    .text((d: D3SankeyNode) => d.label);
}
```

- [ ] **Step 2: Commit**

```bash
git add src/sankey.ts
git commit -m "feat: add D3 Sankey diagram renderer with hover highlights"
```

---

### Task 12b: Sankey rendering tests

**Files:**
- Create: `src/__tests__/sankey.test.ts`

- [ ] **Step 1: Write Sankey rendering tests**

`src/__tests__/sankey.test.ts`:
```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { renderSankey } from '../sankey';
import type { FilteredSankey } from '../data';
import type { SankeyNode } from '../types';

const MOCK_FILTERED: FilteredSankey = {
  nodes: [
    { id: 'industry:Technology', label: 'Technology', dimension: 'industry' },
    { id: 'industry:Healthcare', label: 'Healthcare', dimension: 'industry' },
    { id: 'employeeBucket:100-249', label: '100-249', dimension: 'employeeBucket' },
    { id: 'employeeBucket:10K+', label: '10K+', dimension: 'employeeBucket' },
  ],
  links: [
    { source: 'industry:Technology', target: 'employeeBucket:100-249', value: 25 },
    { source: 'industry:Technology', target: 'employeeBucket:10K+', value: 8 },
    { source: 'industry:Healthcare', target: 'employeeBucket:100-249', value: 15 },
  ],
};

describe('renderSankey', () => {
  let svg: SVGSVGElement;

  beforeEach(() => {
    document.body.innerHTML = '<svg id="test-svg" width="800" height="600"></svg>';
    svg = document.getElementById('test-svg') as unknown as SVGSVGElement;
    // Mock getBoundingClientRect since jsdom doesn't compute layout
    svg.getBoundingClientRect = () => ({
      width: 800, height: 600, top: 0, left: 0, bottom: 600, right: 800, x: 0, y: 0, toJSON: () => {},
    });
  });

  it('renders nodes and links for valid data', () => {
    const callbacks = { onNodeClick: () => {}, onNodeHover: () => {} };
    renderSankey(svg, MOCK_FILTERED, callbacks);

    const nodes = svg.querySelectorAll('.sankey-node');
    expect(nodes.length).toBe(4);

    const links = svg.querySelectorAll('.sankey-link');
    expect(links.length).toBe(3);
  });

  it('shows empty message when no data', () => {
    const callbacks = { onNodeClick: () => {}, onNodeHover: () => {} };
    renderSankey(svg, { nodes: [], links: [] }, callbacks);

    const text = svg.querySelector('text');
    expect(text?.textContent).toBe('No data to display');
  });

  it('fires onNodeClick callback', () => {
    let clickedNode: SankeyNode | null = null;
    const callbacks = {
      onNodeClick: (node: SankeyNode) => { clickedNode = node; },
      onNodeHover: () => {},
    };
    renderSankey(svg, MOCK_FILTERED, callbacks);

    const rect = svg.querySelector('.sankey-node rect') as SVGRectElement;
    rect?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(clickedNode).not.toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
npx vitest run src/__tests__/sankey.test.ts
```

Expected: 3 passed

- [ ] **Step 3: Commit**

```bash
git add src/__tests__/sankey.test.ts
git commit -m "test: add Sankey rendering tests"
```

---

### Task 13: Controls (tabs + breadcrumb)

**Files:**
- Create: `src/controls.ts`

- [ ] **Step 1: Implement controls**

`src/controls.ts`:
```typescript
import type { Dimension, DrillState } from './types';

const DIMENSION_LABELS: Record<Dimension, string> = {
  industry: 'Industry',
  employeeBucket: 'Company Size',
  revenueBucket: 'Revenue',
};

interface ControlsCallbacks {
  onDimensionChange: (dimension: Dimension) => void;
  onBreadcrumbClick: (level: number) => void;
}

export function initControls(callbacks: ControlsCallbacks): void {
  const tabs = document.querySelectorAll<HTMLButtonElement>('#dimension-tabs .tab');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const dim = tab.dataset.dimension as Dimension;
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      callbacks.onDimensionChange(dim);
    });
  });
}

export function updateBreadcrumb(state: DrillState, onClick: (level: number) => void): void {
  const container = document.getElementById('breadcrumb');
  if (!container) return;

  // Clear previous breadcrumbs using DOM methods
  while (container.firstChild) {
    container.removeChild(container.firstChild);
  }

  if (state.selections.length === 0) return;

  for (let i = 0; i < state.path.length; i++) {
    if (i > 0) {
      const sep = document.createElement('span');
      sep.className = 'separator';
      sep.textContent = '>';
      container.appendChild(sep);
    }

    const dimLabel = DIMENSION_LABELS[state.path[i]];

    if (i < state.selections.length) {
      const crumb = document.createElement('span');
      crumb.className = 'crumb';
      crumb.textContent = `${dimLabel}: ${state.selections[i]}`;
      const level = i;
      crumb.addEventListener('click', () => onClick(level));
      container.appendChild(crumb);
    } else {
      const current = document.createElement('span');
      current.textContent = dimLabel;
      container.appendChild(current);
    }
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add src/controls.ts
git commit -m "feat: add dimension tab switching and breadcrumb navigation"
```

---

### Task 14: Sidebar

**Files:**
- Create: `src/sidebar.ts`

- [ ] **Step 1: Implement sidebar**

`src/sidebar.ts`:
```typescript
import type { SankeyNode } from './types';
import type { FilteredSankey } from './data';

function createStatElement(label: string, value: string, style?: string): HTMLElement {
  const stat = document.createElement('div');
  stat.className = 'sidebar-stat';
  if (style) stat.setAttribute('style', style);

  const labelEl = document.createElement('div');
  labelEl.className = 'stat-label';
  labelEl.textContent = label;
  stat.appendChild(labelEl);

  const valueEl = document.createElement('div');
  valueEl.className = 'stat-value';
  valueEl.textContent = value;
  stat.appendChild(valueEl);

  return stat;
}

export function updateSidebar(data: FilteredSankey, hoveredNode: SankeyNode | null): void {
  const content = document.getElementById('sidebar-content');
  if (!content) return;

  // Clear previous content using DOM methods
  while (content.firstChild) {
    content.removeChild(content.firstChild);
  }

  if (data.nodes.length === 0) {
    const p = document.createElement('p');
    p.className = 'placeholder';
    p.textContent = 'No data to display';
    content.appendChild(p);
    return;
  }

  const totalValue = data.links.reduce((sum, l) => sum + l.value, 0);

  // Total companies stat
  content.appendChild(createStatElement('Total Companies', totalValue.toLocaleString()));

  if (hoveredNode) {
    const connectedLinks = data.links.filter(
      l => l.source === hoveredNode.id || l.target === hoveredNode.id
    );
    const nodeTotal = connectedLinks.reduce((sum, l) => sum + l.value, 0);
    const pct = totalValue > 0 ? ((nodeTotal / totalValue) * 100).toFixed(1) : '0';

    // Highlighted node stat
    content.appendChild(createStatElement(
      hoveredNode.label,
      `${nodeTotal.toLocaleString()} companies (${pct}%)`,
      'border-left: 3px solid var(--accent);'
    ));

    // Show breakdown of connected nodes
    const isSource = connectedLinks.some(l => l.source === hoveredNode.id);
    const breakdown = connectedLinks
      .map(l => {
        const otherId = isSource ? l.target : l.source;
        const otherNode = data.nodes.find(n => n.id === otherId);
        return { label: otherNode?.label || otherId, value: l.value };
      })
      .sort((a, b) => b.value - a.value);

    for (const item of breakdown.slice(0, 10)) {
      const itemPct = nodeTotal > 0 ? ((item.value / nodeTotal) * 100).toFixed(1) : '0';
      content.appendChild(createStatElement(
        item.label,
        `${item.value.toLocaleString()} (${itemPct}%)`
      ));
    }
  } else {
    // Show top nodes by total value
    const nodeTotals = data.nodes.map(n => {
      const total = data.links
        .filter(l => l.source === n.id || l.target === n.id)
        .reduce((sum, l) => sum + l.value, 0);
      return { node: n, total };
    }).sort((a, b) => b.total - a.total);

    for (const { node, total } of nodeTotals.slice(0, 10)) {
      content.appendChild(createStatElement(
        node.label,
        `${total.toLocaleString()} companies`
      ));
    }
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add src/sidebar.ts
git commit -m "feat: add sidebar with stats, hover details, and breakdown"
```

---

### Task 15: Wire everything together in main.ts

**Files:**
- Create: `src/main.ts`

- [ ] **Step 1: Implement app entry point**

`src/main.ts`:
```typescript
import { loadSankeyData, filterSankeyForDrill, getAvailableDimensions } from './data';
import { renderSankey } from './sankey';
import { initControls, updateBreadcrumb } from './controls';
import { updateSidebar } from './sidebar';
import type { SankeyData, SankeyNode, DrillState, Dimension } from './types';
import type { FilteredSankey } from './data';

let sankeyData: SankeyData;
let currentState: DrillState = {
  path: ['industry', 'employeeBucket'],
  selections: [],
};
let currentFiltered: FilteredSankey;

function getDefaultSecondDimension(startDim: Dimension): Dimension {
  const available = getAvailableDimensions([startDim]);
  return available[0];
}

function refresh(): void {
  const svg = document.getElementById('sankey-svg') as unknown as SVGSVGElement;
  if (!svg || !sankeyData) return;

  currentFiltered = filterSankeyForDrill(sankeyData, currentState);
  renderSankey(svg, currentFiltered, {
    onNodeClick: handleNodeClick,
    onNodeHover: handleNodeHover,
  });
  updateSidebar(currentFiltered, null);
  updateBreadcrumb(currentState, handleBreadcrumbClick);
}

function handleNodeClick(node: SankeyNode): void {
  const available = getAvailableDimensions(currentState.path);
  if (available.length === 0) return; // Already at max depth

  currentState = {
    path: [...currentState.path, available[0]],
    selections: [...currentState.selections, node.label],
  };
  refresh();
}

function handleNodeHover(node: SankeyNode | null): void {
  updateSidebar(currentFiltered, node);
}

function handleBreadcrumbClick(level: number): void {
  currentState = {
    path: currentState.path.slice(0, level + 2),
    selections: currentState.selections.slice(0, level + 1),
  };
  refresh();
}

function handleDimensionChange(dimension: Dimension): void {
  const secondDim = getDefaultSecondDimension(dimension);
  currentState = {
    path: [dimension, secondDim],
    selections: [],
  };
  refresh();
}

async function init(): Promise<void> {
  try {
    sankeyData = await loadSankeyData();
  } catch {
    const container = document.getElementById('sankey-container');
    if (container) {
      const msg = document.createElement('div');
      msg.setAttribute('style', 'display:flex;align-items:center;justify-content:center;height:100%;color:#94a3b8;');
      const p = document.createElement('p');
      p.textContent = 'Failed to load data. Run the Python pipeline first: cd data && python pipeline.py';
      msg.appendChild(p);
      while (container.firstChild) container.removeChild(container.firstChild);
      container.appendChild(msg);
    }
    return;
  }

  initControls({
    onDimensionChange: handleDimensionChange,
    onBreadcrumbClick: handleBreadcrumbClick,
  });

  window.addEventListener('resize', () => refresh());

  refresh();
}

init();
```

- [ ] **Step 2: Create sample data file for testing**

`public/data/sankey-data.json`:
```json
{
  "dimensions": ["industry", "employeeBucket", "revenueBucket"],
  "nodes": [
    {"id": "industry:Technology", "label": "Technology", "dimension": "industry"},
    {"id": "industry:Healthcare", "label": "Healthcare", "dimension": "industry"},
    {"id": "industry:Finance", "label": "Finance", "dimension": "industry"},
    {"id": "industry:Manufacturing", "label": "Manufacturing", "dimension": "industry"},
    {"id": "industry:Retail", "label": "Retail", "dimension": "industry"},
    {"id": "employeeBucket:<5", "label": "<5", "dimension": "employeeBucket"},
    {"id": "employeeBucket:5-9", "label": "5-9", "dimension": "employeeBucket"},
    {"id": "employeeBucket:10-19", "label": "10-19", "dimension": "employeeBucket"},
    {"id": "employeeBucket:50-99", "label": "50-99", "dimension": "employeeBucket"},
    {"id": "employeeBucket:100-249", "label": "100-249", "dimension": "employeeBucket"},
    {"id": "employeeBucket:250-499", "label": "250-499", "dimension": "employeeBucket"},
    {"id": "employeeBucket:1K-4.9K", "label": "1K-4.9K", "dimension": "employeeBucket"},
    {"id": "employeeBucket:10K+", "label": "10K+", "dimension": "employeeBucket"},
    {"id": "revenueBucket:<$1M", "label": "<$1M", "dimension": "revenueBucket"},
    {"id": "revenueBucket:$1-5M", "label": "$1-5M", "dimension": "revenueBucket"},
    {"id": "revenueBucket:$10-50M", "label": "$10-50M", "dimension": "revenueBucket"},
    {"id": "revenueBucket:$100-500M", "label": "$100-500M", "dimension": "revenueBucket"},
    {"id": "revenueBucket:$1B+", "label": "$1B+", "dimension": "revenueBucket"}
  ],
  "links": [
    {"source": "industry:Technology", "target": "employeeBucket:<5", "value": 45},
    {"source": "industry:Technology", "target": "employeeBucket:10-19", "value": 30},
    {"source": "industry:Technology", "target": "employeeBucket:100-249", "value": 25},
    {"source": "industry:Technology", "target": "employeeBucket:1K-4.9K", "value": 15},
    {"source": "industry:Technology", "target": "employeeBucket:10K+", "value": 8},
    {"source": "industry:Healthcare", "target": "employeeBucket:50-99", "value": 20},
    {"source": "industry:Healthcare", "target": "employeeBucket:250-499", "value": 18},
    {"source": "industry:Healthcare", "target": "employeeBucket:1K-4.9K", "value": 12},
    {"source": "industry:Finance", "target": "employeeBucket:100-249", "value": 22},
    {"source": "industry:Finance", "target": "employeeBucket:1K-4.9K", "value": 16},
    {"source": "industry:Finance", "target": "employeeBucket:10K+", "value": 10},
    {"source": "industry:Manufacturing", "target": "employeeBucket:250-499", "value": 14},
    {"source": "industry:Manufacturing", "target": "employeeBucket:1K-4.9K", "value": 20},
    {"source": "industry:Retail", "target": "employeeBucket:5-9", "value": 35},
    {"source": "industry:Retail", "target": "employeeBucket:50-99", "value": 15},
    {"source": "industry:Technology", "target": "revenueBucket:<$1M", "value": 40},
    {"source": "industry:Technology", "target": "revenueBucket:$10-50M", "value": 30},
    {"source": "industry:Technology", "target": "revenueBucket:$1B+", "value": 8},
    {"source": "industry:Healthcare", "target": "revenueBucket:$10-50M", "value": 15},
    {"source": "industry:Healthcare", "target": "revenueBucket:$100-500M", "value": 20},
    {"source": "industry:Finance", "target": "revenueBucket:$100-500M", "value": 25},
    {"source": "industry:Finance", "target": "revenueBucket:$1B+", "value": 12},
    {"source": "industry:Manufacturing", "target": "revenueBucket:$10-50M", "value": 18},
    {"source": "industry:Retail", "target": "revenueBucket:$1-5M", "value": 30},
    {"source": "industry:Retail", "target": "revenueBucket:$10-50M", "value": 12},
    {"source": "employeeBucket:<5", "target": "revenueBucket:<$1M", "value": 38},
    {"source": "employeeBucket:5-9", "target": "revenueBucket:<$1M", "value": 10},
    {"source": "employeeBucket:5-9", "target": "revenueBucket:$1-5M", "value": 25},
    {"source": "employeeBucket:10-19", "target": "revenueBucket:$1-5M", "value": 15},
    {"source": "employeeBucket:10-19", "target": "revenueBucket:$10-50M", "value": 12},
    {"source": "employeeBucket:50-99", "target": "revenueBucket:$10-50M", "value": 20},
    {"source": "employeeBucket:100-249", "target": "revenueBucket:$10-50M", "value": 25},
    {"source": "employeeBucket:100-249", "target": "revenueBucket:$100-500M", "value": 15},
    {"source": "employeeBucket:250-499", "target": "revenueBucket:$100-500M", "value": 20},
    {"source": "employeeBucket:1K-4.9K", "target": "revenueBucket:$100-500M", "value": 30},
    {"source": "employeeBucket:1K-4.9K", "target": "revenueBucket:$1B+", "value": 10},
    {"source": "employeeBucket:10K+", "target": "revenueBucket:$1B+", "value": 15}
  ]
}
```

- [ ] **Step 3: Verify app runs end-to-end**

```bash
npx vite --open
```

Expected: Browser shows the Sankey diagram with Industry on the left flowing to Company Size on the right. Clicking tabs switches dimensions. Clicking nodes drills down. Sidebar shows stats. Stop after verifying.

- [ ] **Step 4: Run all tests**

```bash
npx vitest run
```

Expected: All frontend tests pass

- [ ] **Step 5: Commit**

```bash
git add src/main.ts public/data/sankey-data.json
git commit -m "feat: wire up app entry point with drill-down, tab switching, and sample data"
```

---

### Task 16: Final verification

- [ ] **Step 1: Run all Python tests**

```bash
cd data && source .venv/bin/activate && python -m pytest -v
```

Expected: All tests pass

- [ ] **Step 2: Run all frontend tests**

```bash
npx vitest run
```

Expected: All tests pass

- [ ] **Step 3: Build for production**

```bash
npx vite build
```

Expected: Build succeeds, output in `dist/`

- [ ] **Step 4: Manual smoke test**

```bash
npx vite preview
```

Verify in browser:
1. Dashboard loads with Industry to Company Size Sankey
2. Click "Company Size" tab: Sankey switches to Size to Industry
3. Click "Revenue" tab: Sankey switches to Revenue to Industry
4. Click a node: Sankey drills down to show next dimension
5. Click another node: Third level appears
6. Breadcrumb shows path, clicking a crumb navigates back
7. Sidebar shows stats, hover shows connected details

- [ ] **Step 5: Final commit if any fixes needed**
