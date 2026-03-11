# Census Data Migration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the individual-company scraping pipeline with US Census Bureau aggregate statistics covering all ~6.4 million US businesses.

**Architecture:** Two Census API calls (Industry × Employee Size, Industry × Revenue Size) produce `CensusRecord` lists that are directly converted to Sankey nodes/links. The frontend gains a metric toggle (firms/employees) and awareness of which dimension pairs have real data. Links are stored unidirectional (industry as source) and flipped at query time for reverse views.

**Tech Stack:** Python 3 + Pydantic + requests (backend), TypeScript + D3.js + d3-sankey (frontend), Vitest (frontend tests), pytest (backend tests)

**Spec:** `docs/superpowers/specs/2026-03-11-census-data-migration.md`

---

## Chunk 1: Python Backend — Models, Census Fetcher, Export, Pipeline

### Task 1: Update Python Data Models

**Files:**
- Modify: `data/models.py`
- Modify: `data/tests/test_models.py`

- [ ] **Step 1: Write failing tests for new models**

In `data/tests/test_models.py`, replace the existing content with tests for the new models:

```python
from data.models import CensusRecord, SankeyNode, SankeyLink, SankeyData


def test_census_record_creation():
    record = CensusRecord(
        source_dimension="industry",
        source_value="Manufacturing",
        target_dimension="employeeSize",
        target_value="100-249",
        firms=13573,
        employees=943335,
    )
    assert record.firms == 13573
    assert record.employees == 943335
    assert record.source_dimension == "industry"


def test_sankey_link_has_firms_and_employees():
    link = SankeyLink(
        source="industry:Manufacturing",
        target="employeeSize:100-249",
        firms=13573,
        employees=943335,
    )
    assert link.firms == 13573
    assert link.employees == 943335


def test_sankey_data_has_available_pairs():
    data = SankeyData(
        dimensions=["industry", "employeeSize", "revenueSize"],
        nodes=[],
        links=[],
        availablePairs=[("industry", "employeeSize"), ("industry", "revenueSize")],
    )
    assert len(data.availablePairs) == 2
    assert ("industry", "employeeSize") in data.availablePairs
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/marius/sources/industry/size-graph && python -m pytest data/tests/test_models.py -v`
Expected: FAIL — `CensusRecord` not defined, `SankeyLink` missing `firms`/`employees` fields

- [ ] **Step 3: Update models.py**

Replace `data/models.py` with:

```python
from pydantic import BaseModel


class CensusRecord(BaseModel):
    """A single cell from a Census cross-tabulation."""
    source_dimension: str
    source_value: str
    target_dimension: str
    target_value: str
    firms: int
    employees: int


class SankeyNode(BaseModel):
    id: str
    label: str
    dimension: str


class SankeyLink(BaseModel):
    source: str
    target: str
    firms: int
    employees: int


class SankeyData(BaseModel):
    dimensions: list[str]
    nodes: list[SankeyNode]
    links: list[SankeyLink]
    availablePairs: list[tuple[str, str]]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/marius/sources/industry/size-graph && python -m pytest data/tests/test_models.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add data/models.py data/tests/test_models.py
git commit -m "feat: update models for Census data (CensusRecord, firms/employees on links)"
```

---

### Task 2: Create Census API Fetcher

**Files:**
- Create: `data/sources/census.py`
- Create: `data/tests/test_census.py`

**Reference:** Census API endpoint: `https://api.census.gov/data/2022/ecnsize`

- [ ] **Step 1: Write failing tests for census.py**

Create `data/tests/test_census.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from data.sources.census import (
    fetch_industry_by_employment,
    fetch_industry_by_revenue,
    parse_census_response,
    NAICS_LABELS,
    EMPSIZE_LABELS,
    RCPSIZE_LABELS,
)


# Simulated Census API response (header row + data rows)
MOCK_EMP_RESPONSE = [
    ["NAICS2022", "NAICS2022_LABEL", "EMPSZFF", "EMPSZFF_LABEL", "FIRMPDEMP", "EMP", "RCPTOT"],
    ["31-33", "Manufacturing", "510", "Less than 5", "45000", "120000", "15000000"],
    ["31-33", "Manufacturing", "515", "5 to 9", "22000", "150000", "20000000"],
    ["51", "Information", "510", "Less than 5", "30000", "80000", "10000000"],
]

MOCK_RCV_RESPONSE = [
    ["NAICS2022", "NAICS2022_LABEL", "RCPSZFF", "RCPSZFF_LABEL", "FIRMPDEMP", "EMP", "RCPTOT"],
    ["31-33", "Manufacturing", "410", "Less than $100,000", "12000", "30000", "800000"],
    ["51", "Information", "430", "$1,000,000 to $2,499,999", "8000", "60000", "12000000"],
]


def test_parse_census_response_employment():
    records = parse_census_response(MOCK_EMP_RESPONSE, "employeeSize", "EMPSZFF", EMPSIZE_LABELS)
    assert len(records) == 3
    assert records[0].source_dimension == "industry"
    assert records[0].source_value == "Manufacturing"
    assert records[0].target_dimension == "employeeSize"
    assert records[0].target_value == "<5 employees"
    assert records[0].firms == 45000
    assert records[0].employees == 120000


def test_parse_census_response_revenue():
    records = parse_census_response(MOCK_RCV_RESPONSE, "revenueSize", "RCPSZFF", RCPSIZE_LABELS)
    assert len(records) == 2
    assert records[0].target_dimension == "revenueSize"
    assert records[0].target_value == "<$100K"
    assert records[1].target_value == "$1-2.5M"


def test_parse_census_response_suppressed_values():
    """Census returns 'D' for suppressed cells — should be treated as 0."""
    response = [
        ["NAICS2022", "NAICS2022_LABEL", "EMPSZFF", "EMPSZFF_LABEL", "FIRMPDEMP", "EMP", "RCPTOT"],
        ["55", "Management of companies", "550", "500 or more", "D", "D", "D"],
    ]
    records = parse_census_response(response, "employeeSize", "EMPSZFF", EMPSIZE_LABELS)
    assert len(records) == 1
    assert records[0].firms == 0
    assert records[0].employees == 0


def test_parse_census_response_skips_totals():
    """Rows with size code 001, 200, or 600 are totals/subtotals and should be skipped."""
    response = [
        ["NAICS2022", "NAICS2022_LABEL", "EMPSZFF", "EMPSZFF_LABEL", "FIRMPDEMP", "EMP", "RCPTOT"],
        ["31-33", "Manufacturing", "001", "All firms", "100000", "5000000", "900000000"],
        ["31-33", "Manufacturing", "510", "Less than 5", "45000", "120000", "15000000"],
    ]
    records = parse_census_response(response, "employeeSize", "EMPSZFF", EMPSIZE_LABELS)
    assert len(records) == 1
    assert records[0].target_value == "<5 employees"


@patch("data.sources.census.requests.get")
def test_fetch_industry_by_employment(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_EMP_RESPONSE
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    records = fetch_industry_by_employment()
    assert len(records) == 3
    assert all(r.target_dimension == "employeeSize" for r in records)
    mock_get.assert_called_once()


@patch("data.sources.census.requests.get")
def test_fetch_industry_by_revenue(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_RCV_RESPONSE
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    records = fetch_industry_by_revenue()
    assert len(records) == 2
    assert all(r.target_dimension == "revenueSize" for r in records)


@patch("data.sources.census.time.sleep")
@patch("data.sources.census.requests.get")
def test_fetch_retries_on_failure(mock_get, mock_sleep):
    """Should retry up to 3 times on HTTP errors."""
    mock_get.side_effect = [
        MagicMock(status_code=500, raise_for_status=MagicMock(side_effect=Exception("Server Error"))),
        MagicMock(status_code=500, raise_for_status=MagicMock(side_effect=Exception("Server Error"))),
        MagicMock(status_code=200, json=MagicMock(return_value=MOCK_EMP_RESPONSE), raise_for_status=MagicMock()),
    ]
    records = fetch_industry_by_employment()
    assert len(records) == 3
    assert mock_get.call_count == 3
    assert mock_sleep.call_count == 2


def test_naics_labels_coverage():
    """All 18 NAICS sectors should have labels."""
    assert len(NAICS_LABELS) == 18
    assert "31-33" in NAICS_LABELS
    assert "55" in NAICS_LABELS


def test_empsize_labels_coverage():
    """All 8 employment size brackets should have labels."""
    assert len(EMPSIZE_LABELS) == 8


def test_rcpsize_labels_coverage():
    """All 10 revenue size brackets should have labels."""
    assert len(RCPSIZE_LABELS) == 10
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/marius/sources/industry/size-graph && python -m pytest data/tests/test_census.py -v`
Expected: FAIL — `data.sources.census` module not found

- [ ] **Step 3: Implement census.py**

Create `data/sources/census.py`:

```python
"""Fetch aggregate business statistics from the US Census Bureau Economic Census."""
import logging
import time

import requests

from data.models import CensusRecord

logger = logging.getLogger(__name__)

API_BASE = "https://api.census.gov/data/2022/ecnsize"

# 18 NAICS sectors
NAICS_LABELS: dict[str, str] = {
    "21": "Mining, quarrying, and oil and gas extraction",
    "22": "Utilities",
    "23": "Construction",
    "31-33": "Manufacturing",
    "42": "Wholesale trade",
    "44-45": "Retail trade",
    "48-49": "Transportation and warehousing",
    "51": "Information",
    "52": "Finance and insurance",
    "53": "Real estate and rental and leasing",
    "54": "Professional, scientific, and technical services",
    "55": "Management of companies and enterprises",
    "56": "Administrative and support and waste management",
    "61": "Educational services",
    "62": "Health care and social assistance",
    "71": "Arts, entertainment, and recreation",
    "72": "Accommodation and food services",
    "81": "Other services (except public administration)",
}

# 8 employment size brackets (EMPSZFF codes)
EMPSIZE_LABELS: dict[str, str] = {
    "510": "<5 employees",
    "515": "5-9",
    "520": "10-19",
    "525": "20-49",
    "530": "50-99",
    "535": "100-249",
    "545": "250-499",
    "550": "500+",
}

# 10 revenue size brackets (RCPSZFF codes)
RCPSIZE_LABELS: dict[str, str] = {
    "410": "<$100K",
    "415": "$100-250K",
    "420": "$250-500K",
    "425": "$500K-1M",
    "430": "$1-2.5M",
    "435": "$2.5-5M",
    "440": "$5-10M",
    "445": "$10-25M",
    "450": "$25-100M",
    "455": "$100M+",
}

# Size codes that are totals/subtotals — skip these
SKIP_CODES = {"001", "200", "600"}

MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # seconds
REQUEST_TIMEOUT = 30  # seconds


def _safe_int(value: str) -> int:
    """Parse an integer from Census data, treating 'D' (suppressed) as 0."""
    if value == "D":
        return 0
    return int(value)


def _fetch_with_retry(url: str, params: dict) -> list[list[str]]:
    """Fetch Census API data with retry on failure."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAYS[attempt])
    raise last_error


def parse_census_response(
    rows: list[list[str]],
    target_dimension: str,
    size_field: str,
    size_labels: dict[str, str],
) -> list[CensusRecord]:
    """Parse Census API JSON response into CensusRecord list."""
    header = rows[0]
    naics_idx = header.index("NAICS2022")
    size_idx = header.index(size_field)
    firms_idx = header.index("FIRMPDEMP")
    emp_idx = header.index("EMP")

    records = []
    for row in rows[1:]:
        size_code = row[size_idx]
        if size_code in SKIP_CODES:
            continue
        if size_code not in size_labels:
            continue

        naics_code = row[naics_idx]
        if naics_code not in NAICS_LABELS:
            continue

        firms = _safe_int(row[firms_idx])
        employees = _safe_int(row[emp_idx])

        if firms == 0 and employees == 0:
            logger.warning("Suppressed cell: NAICS=%s, %s=%s", naics_code, size_field, size_code)

        records.append(CensusRecord(
            source_dimension="industry",
            source_value=NAICS_LABELS[naics_code],
            target_dimension=target_dimension,
            target_value=size_labels[size_code],
            firms=firms,
            employees=employees,
        ))

    return records


def fetch_industry_by_employment() -> list[CensusRecord]:
    """Fetch Industry x Employment Size cross-tabulation."""
    rows = _fetch_with_retry(API_BASE, {
        "get": "FIRMPDEMP,EMP,RCPTOT",
        "for": "us:*",
        "NAICS2022": "*",
        "EMPSZFF": "*",
    })
    return parse_census_response(rows, "employeeSize", "EMPSZFF", EMPSIZE_LABELS)


def fetch_industry_by_revenue() -> list[CensusRecord]:
    """Fetch Industry x Revenue Size cross-tabulation."""
    rows = _fetch_with_retry(API_BASE, {
        "get": "FIRMPDEMP,EMP,RCPTOT",
        "for": "us:*",
        "NAICS2022": "*",
        "RCPSZFF": "*",
    })
    return parse_census_response(rows, "revenueSize", "RCPSZFF", RCPSIZE_LABELS)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/marius/sources/industry/size-graph && python -m pytest data/tests/test_census.py -v`
Expected: 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add data/sources/census.py data/tests/test_census.py
git commit -m "feat: add Census Bureau API fetcher with retry and suppression handling"
```

---

### Task 3: Rewrite Export Module for Census Data

**Files:**
- Modify: `data/export.py`
- Modify: `data/tests/test_export.py`

- [ ] **Step 1: Write failing tests for new export**

Replace `data/tests/test_export.py` with:

```python
import json
from data.models import CensusRecord, SankeyData
from data.export import generate_sankey_from_census, export_census_to_file


SAMPLE_RECORDS = [
    CensusRecord(
        source_dimension="industry", source_value="Manufacturing",
        target_dimension="employeeSize", target_value="100-249",
        firms=13573, employees=943335,
    ),
    CensusRecord(
        source_dimension="industry", source_value="Manufacturing",
        target_dimension="employeeSize", target_value="500+",
        firms=3200, employees=2100000,
    ),
    CensusRecord(
        source_dimension="industry", source_value="Information",
        target_dimension="employeeSize", target_value="100-249",
        firms=8500, employees=590000,
    ),
    CensusRecord(
        source_dimension="industry", source_value="Manufacturing",
        target_dimension="revenueSize", target_value="$1-2.5M",
        firms=18000, employees=250000,
    ),
    CensusRecord(
        source_dimension="industry", source_value="Information",
        target_dimension="revenueSize", target_value="$100M+",
        firms=500, employees=800000,
    ),
]


def test_generate_sankey_has_correct_dimensions():
    data = generate_sankey_from_census(SAMPLE_RECORDS)
    assert data.dimensions == ["industry", "employeeSize", "revenueSize"]


def test_generate_sankey_nodes_created():
    data = generate_sankey_from_census(SAMPLE_RECORDS)
    node_ids = {n.id for n in data.nodes}
    assert "industry:Manufacturing" in node_ids
    assert "industry:Information" in node_ids
    assert "employeeSize:100-249" in node_ids
    assert "employeeSize:500+" in node_ids
    assert "revenueSize:$1-2.5M" in node_ids
    assert "revenueSize:$100M+" in node_ids


def test_generate_sankey_nodes_have_correct_dimension():
    data = generate_sankey_from_census(SAMPLE_RECORDS)
    for node in data.nodes:
        dim = node.id.split(":")[0]
        assert node.dimension == dim


def test_generate_sankey_links_have_firms_and_employees():
    data = generate_sankey_from_census(SAMPLE_RECORDS)
    link = next(
        l for l in data.links
        if l.source == "industry:Manufacturing" and l.target == "employeeSize:100-249"
    )
    assert link.firms == 13573
    assert link.employees == 943335


def test_generate_sankey_available_pairs():
    data = generate_sankey_from_census(SAMPLE_RECORDS)
    assert ("industry", "employeeSize") in data.availablePairs
    assert ("industry", "revenueSize") in data.availablePairs
    assert len(data.availablePairs) == 2


def test_generate_sankey_link_count():
    data = generate_sankey_from_census(SAMPLE_RECORDS)
    assert len(data.links) == 5  # one link per record


def test_export_census_to_file(tmp_path):
    data = generate_sankey_from_census(SAMPLE_RECORDS)
    output = tmp_path / "sankey-data.json"
    export_census_to_file(data, str(output))
    assert output.exists()

    loaded = json.loads(output.read_text())
    assert "availablePairs" in loaded
    assert "nodes" in loaded
    assert "links" in loaded
    # Verify links have firms/employees, not value
    assert "firms" in loaded["links"][0]
    assert "employees" in loaded["links"][0]
    assert "value" not in loaded["links"][0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/marius/sources/industry/size-graph && python -m pytest data/tests/test_export.py -v`
Expected: FAIL — `generate_sankey_from_census` not found

- [ ] **Step 3: Rewrite export.py**

Replace `data/export.py` with:

```python
import json
from pathlib import Path

from data.models import CensusRecord, SankeyData, SankeyNode, SankeyLink


def generate_sankey_from_census(records: list[CensusRecord]) -> SankeyData:
    """Build Sankey data directly from Census aggregate records."""
    nodes_set: set[tuple[str, str, str]] = set()  # (id, label, dimension)
    links: list[SankeyLink] = []
    available_pairs: set[tuple[str, str]] = set()

    for r in records:
        source_id = f"{r.source_dimension}:{r.source_value}"
        target_id = f"{r.target_dimension}:{r.target_value}"

        nodes_set.add((source_id, r.source_value, r.source_dimension))
        nodes_set.add((target_id, r.target_value, r.target_dimension))

        links.append(SankeyLink(
            source=source_id,
            target=target_id,
            firms=r.firms,
            employees=r.employees,
        ))

        available_pairs.add((r.source_dimension, r.target_dimension))

    nodes = [
        SankeyNode(id=nid, label=label, dimension=dim)
        for nid, label, dim in sorted(nodes_set)
    ]

    return SankeyData(
        dimensions=["industry", "employeeSize", "revenueSize"],
        nodes=nodes,
        links=links,
        availablePairs=sorted(available_pairs),
    )


def export_census_to_file(data: SankeyData, output_path: str) -> None:
    """Write Sankey data to a JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data.model_dump(), indent=2))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/marius/sources/industry/size-graph && python -m pytest data/tests/test_export.py -v`
Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add data/export.py data/tests/test_export.py
git commit -m "feat: rewrite export for Census aggregate data"
```

---

### Task 4: Rewrite Pipeline and Clean Up Old Code

**Files:**
- Modify: `data/pipeline.py`
- Modify: `data/tests/test_pipeline.py`
- Remove: `data/sources/sec_edgar.py`, `data/sources/wikidata.py`, `data/sources/opencorporates.py`
- Remove: `data/normalize.py`, `data/bucket.py`
- Remove: `data/tests/test_sec_edgar.py`, `data/tests/test_wikidata.py`, `data/tests/test_opencorporates.py`
- Remove: `data/tests/test_normalize.py`, `data/tests/test_bucket.py`

- [ ] **Step 1: Write failing test for new pipeline**

Replace `data/tests/test_pipeline.py` with:

```python
import json
from unittest.mock import patch
from data.pipeline import run_pipeline
from data.models import CensusRecord


def _mock_emp_records() -> list[CensusRecord]:
    return [
        CensusRecord(
            source_dimension="industry", source_value="Manufacturing",
            target_dimension="employeeSize", target_value="100-249",
            firms=13573, employees=943335,
        ),
        CensusRecord(
            source_dimension="industry", source_value="Information",
            target_dimension="employeeSize", target_value="500+",
            firms=1200, employees=890000,
        ),
    ]


def _mock_rev_records() -> list[CensusRecord]:
    return [
        CensusRecord(
            source_dimension="industry", source_value="Manufacturing",
            target_dimension="revenueSize", target_value="$1-2.5M",
            firms=18000, employees=250000,
        ),
    ]


@patch("data.pipeline.fetch_industry_by_revenue", return_value=_mock_rev_records())
@patch("data.pipeline.fetch_industry_by_employment", return_value=_mock_emp_records())
def test_run_pipeline_produces_sankey_json(mock_emp, mock_rev, tmp_path):
    run_pipeline(str(tmp_path / "sankey-data.json"))

    output = tmp_path / "sankey-data.json"
    assert output.exists()

    sankey = json.loads(output.read_text())
    assert len(sankey["nodes"]) > 0
    assert len(sankey["links"]) == 3
    assert "availablePairs" in sankey
    # Verify links have firms/employees
    assert "firms" in sankey["links"][0]
    assert "employees" in sankey["links"][0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/marius/sources/industry/size-graph && python -m pytest data/tests/test_pipeline.py -v`
Expected: FAIL — imports don't match

- [ ] **Step 3: Rewrite pipeline.py**

Replace `data/pipeline.py` with:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/marius/sources/industry/size-graph && python -m pytest data/tests/test_pipeline.py -v`
Expected: 1 test PASS

- [ ] **Step 5: Ensure __pycache__ is in .gitignore**

Check `.gitignore` for `__pycache__/`. If missing, add it:

```bash
grep -q '__pycache__' /home/marius/sources/industry/size-graph/.gitignore || echo '__pycache__/' >> /home/marius/sources/industry/size-graph/.gitignore
```

- [ ] **Step 6: Remove old files**

```bash
cd /home/marius/sources/industry/size-graph
git rm data/sources/sec_edgar.py data/sources/wikidata.py data/sources/opencorporates.py
git rm data/normalize.py data/bucket.py
git rm data/tests/test_sec_edgar.py data/tests/test_wikidata.py data/tests/test_opencorporates.py
git rm data/tests/test_normalize.py data/tests/test_bucket.py
```

- [ ] **Step 7: Run all Python tests to verify nothing is broken**

Run: `cd /home/marius/sources/industry/size-graph && python -m pytest data/tests/ -v`
Expected: All tests pass (test_models: 3, test_census: 10, test_export: 7, test_pipeline: 1 = 21 total)

- [ ] **Step 8: Commit**

```bash
cd /home/marius/sources/industry/size-graph
git add data/pipeline.py data/tests/test_pipeline.py .gitignore
git commit -m "feat: rewrite pipeline for Census data, remove old scrapers"
```

---

## Chunk 2: Frontend — Types, Data Layer, and Tests

### Task 5: Update TypeScript Types

**Files:**
- Modify: `src/types.ts`

- [ ] **Step 1: Update types.ts**

Replace `src/types.ts` with:

```typescript
export type Dimension = 'industry' | 'employeeSize' | 'revenueSize';

export type Metric = 'firms' | 'employees';

export interface SankeyNode {
  id: string;
  label: string;
  dimension: Dimension;
}

export interface SankeyLink {
  source: string;
  target: string;
  firms: number;
  employees: number;
}

export interface SankeyData {
  dimensions: Dimension[];
  nodes: SankeyNode[];
  links: SankeyLink[];
  availablePairs: [Dimension, Dimension][];
}

export interface FilteredSankey {
  nodes: SankeyNode[];
  links: SankeyLink[];
  unavailablePair?: boolean;
}

export interface DrillState {
  path: Dimension[];
  selections: string[];
}
```

- [ ] **Step 2: Commit**

```bash
git add src/types.ts
git commit -m "feat: update TypeScript types for Census data model"
```

---

### Task 6: Rewrite Data Module with availablePairs and Reverse Lookups

**Files:**
- Modify: `src/data.ts`
- Modify: `src/__tests__/data.test.ts`

- [ ] **Step 1: Write failing tests**

Replace `src/__tests__/data.test.ts` with:

```typescript
import { describe, it, expect } from 'vitest';
import { filterSankeyForDrill, getAvailableDimensions, getMetricValue } from '../data';
import type { SankeyData, SankeyLink, DrillState, Dimension } from '../types';

const MOCK_DATA: SankeyData = {
  dimensions: ['industry', 'employeeSize', 'revenueSize'],
  nodes: [
    { id: 'industry:Manufacturing', label: 'Manufacturing', dimension: 'industry' },
    { id: 'industry:Information', label: 'Information', dimension: 'industry' },
    { id: 'employeeSize:100-249', label: '100-249', dimension: 'employeeSize' },
    { id: 'employeeSize:500+', label: '500+', dimension: 'employeeSize' },
    { id: 'revenueSize:$1-2.5M', label: '$1-2.5M', dimension: 'revenueSize' },
    { id: 'revenueSize:$100M+', label: '$100M+', dimension: 'revenueSize' },
  ],
  links: [
    { source: 'industry:Manufacturing', target: 'employeeSize:100-249', firms: 13573, employees: 943335 },
    { source: 'industry:Manufacturing', target: 'employeeSize:500+', firms: 3200, employees: 2100000 },
    { source: 'industry:Information', target: 'employeeSize:100-249', firms: 8500, employees: 590000 },
    { source: 'industry:Manufacturing', target: 'revenueSize:$1-2.5M', firms: 18000, employees: 250000 },
    { source: 'industry:Information', target: 'revenueSize:$100M+', firms: 500, employees: 800000 },
  ],
  availablePairs: [['industry', 'employeeSize'], ['industry', 'revenueSize']],
};

describe('filterSankeyForDrill', () => {
  it('returns links between industry and employeeSize', () => {
    const state: DrillState = { path: ['industry', 'employeeSize'], selections: [] };
    const result = filterSankeyForDrill(MOCK_DATA, state);
    expect(result.links.length).toBe(3);
    expect(result.links.every(l => l.source.startsWith('industry:'))).toBe(true);
    expect(result.links.every(l => l.target.startsWith('employeeSize:'))).toBe(true);
  });

  it('returns links between industry and revenueSize', () => {
    const state: DrillState = { path: ['industry', 'revenueSize'], selections: [] };
    const result = filterSankeyForDrill(MOCK_DATA, state);
    expect(result.links.length).toBe(2);
  });

  it('reverses links for employeeSize -> industry', () => {
    const state: DrillState = { path: ['employeeSize', 'industry'], selections: [] };
    const result = filterSankeyForDrill(MOCK_DATA, state);
    expect(result.links.length).toBe(3);
    // Links should be flipped: source=employeeSize, target=industry
    expect(result.links.every(l => l.source.startsWith('employeeSize:'))).toBe(true);
    expect(result.links.every(l => l.target.startsWith('industry:'))).toBe(true);
  });

  it('returns empty with unavailablePair flag for unavailable pair', () => {
    const state: DrillState = { path: ['employeeSize', 'revenueSize'], selections: [] };
    const result = filterSankeyForDrill(MOCK_DATA, state);
    expect(result.nodes.length).toBe(0);
    expect(result.links.length).toBe(0);
    expect(result.unavailablePair).toBe(true);
  });

  it('filters by selection when drilling down', () => {
    const state: DrillState = {
      path: ['industry', 'employeeSize'],
      selections: ['Manufacturing'],
    };
    const result = filterSankeyForDrill(MOCK_DATA, state);
    expect(result.links.every(l => l.source === 'industry:Manufacturing')).toBe(true);
    expect(result.links.length).toBe(2);
  });

  it('filters by selection on reverse pair', () => {
    const state: DrillState = {
      path: ['employeeSize', 'industry'],
      selections: ['100-249'],
    };
    const result = filterSankeyForDrill(MOCK_DATA, state);
    expect(result.links.every(l => l.source === 'employeeSize:100-249')).toBe(true);
    expect(result.links.length).toBe(2);
  });
});

describe('getAvailableDimensions', () => {
  it('returns dimensions that form valid pairs with current path', () => {
    const result = getAvailableDimensions(['industry'], MOCK_DATA.availablePairs);
    expect(result).toContain('employeeSize');
    expect(result).toContain('revenueSize');
  });

  it('returns industry for employeeSize starting dimension', () => {
    const result = getAvailableDimensions(['employeeSize'], MOCK_DATA.availablePairs);
    expect(result).toEqual(['industry']);
  });

  it('does not return revenueSize for employeeSize', () => {
    const result = getAvailableDimensions(['employeeSize'], MOCK_DATA.availablePairs);
    expect(result).not.toContain('revenueSize');
  });

  it('returns empty when all pair-valid dimensions used', () => {
    const result = getAvailableDimensions(['industry', 'employeeSize'], MOCK_DATA.availablePairs);
    // After industry->employeeSize, could drill to revenueSize only if employeeSize->revenueSize is available (it's not)
    expect(result).toEqual([]);
  });
});

describe('getMetricValue', () => {
  it('returns firms for firms metric', () => {
    const link: SankeyLink = { source: 'a', target: 'b', firms: 100, employees: 5000 };
    expect(getMetricValue(link, 'firms')).toBe(100);
  });

  it('returns employees for employees metric', () => {
    const link: SankeyLink = { source: 'a', target: 'b', firms: 100, employees: 5000 };
    expect(getMetricValue(link, 'employees')).toBe(5000);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/marius/sources/industry/size-graph && npx vitest run src/__tests__/data.test.ts`
Expected: FAIL — old function signatures, missing `getMetricValue`

- [ ] **Step 3: Rewrite data.ts**

Replace `src/data.ts` with:

```typescript
import type { SankeyData, DrillState, Dimension, FilteredSankey, SankeyLink, Metric } from './types';

let cachedData: SankeyData | null = null;

export async function loadSankeyData(): Promise<SankeyData> {
  if (cachedData) return cachedData;
  const resp = await fetch('/data/sankey-data.json');
  if (!resp.ok) throw new Error(`Failed to load sankey data: ${resp.status} ${resp.statusText}`);
  cachedData = await resp.json();
  return cachedData!;
}

/**
 * Check if a dimension pair is available (in either direction).
 * Returns the canonical direction if found, or null.
 */
function findPairDirection(
  sourceDim: Dimension,
  targetDim: Dimension,
  availablePairs: [Dimension, Dimension][],
): 'forward' | 'reverse' | null {
  for (const [a, b] of availablePairs) {
    if (a === sourceDim && b === targetDim) return 'forward';
    if (a === targetDim && b === sourceDim) return 'reverse';
  }
  return null;
}

export function getAvailableDimensions(
  usedDimensions: Dimension[],
  availablePairs: [Dimension, Dimension][],
): Dimension[] {
  const lastDim = usedDimensions[usedDimensions.length - 1];
  const allDims: Dimension[] = ['industry', 'employeeSize', 'revenueSize'];

  return allDims.filter(d => {
    if (usedDimensions.includes(d)) return false;
    return findPairDirection(lastDim, d, availablePairs) !== null;
  });
}

export function getMetricValue(link: SankeyLink, metric: Metric): number {
  return link[metric];
}

export function filterSankeyForDrill(data: SankeyData, state: DrillState): FilteredSankey {
  const sourceDim = state.path[0];
  const targetDim = state.path[state.path.length - 1];

  const direction = findPairDirection(sourceDim, targetDim, data.availablePairs);
  if (direction === null) {
    return { nodes: [], links: [], unavailablePair: true };
  }

  let links: SankeyLink[];

  if (direction === 'forward') {
    // Data has source->target in the requested order
    links = data.links.filter(
      l => l.source.startsWith(`${sourceDim}:`) && l.target.startsWith(`${targetDim}:`)
    );
  } else {
    // Data has target->source, need to flip
    links = data.links
      .filter(l => l.source.startsWith(`${targetDim}:`) && l.target.startsWith(`${sourceDim}:`))
      .map(l => ({ ...l, source: l.target, target: l.source }));
  }

  // Apply selection filters
  for (let i = 0; i < state.selections.length; i++) {
    const dim = state.path[i];
    const selectedId = `${dim}:${state.selections[i]}`;
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/marius/sources/industry/size-graph && npx vitest run src/__tests__/data.test.ts`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/data.ts src/__tests__/data.test.ts
git commit -m "feat: rewrite data layer with availablePairs and reverse link support"
```

---

## Chunk 3: Frontend — Rendering, Controls, Sidebar, Main, HTML

### Task 7: Update Sankey Renderer for Metric Support

**Files:**
- Modify: `src/sankey.ts`
- Modify: `src/__tests__/sankey.test.ts`

- [ ] **Step 1: Update sankey.test.ts**

Replace `src/__tests__/sankey.test.ts` with:

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { renderSankey } from '../sankey';
import type { FilteredSankey, SankeyNode } from '../types';

const MOCK_FILTERED: FilteredSankey = {
  nodes: [
    { id: 'industry:Manufacturing', label: 'Manufacturing', dimension: 'industry' },
    { id: 'industry:Information', label: 'Information', dimension: 'industry' },
    { id: 'employeeSize:100-249', label: '100-249', dimension: 'employeeSize' },
    { id: 'employeeSize:500+', label: '500+', dimension: 'employeeSize' },
  ],
  links: [
    { source: 'industry:Manufacturing', target: 'employeeSize:100-249', firms: 13573, employees: 943335 },
    { source: 'industry:Manufacturing', target: 'employeeSize:500+', firms: 3200, employees: 2100000 },
    { source: 'industry:Information', target: 'employeeSize:100-249', firms: 8500, employees: 590000 },
  ],
};

function createSvgElement(): SVGSVGElement {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', '800');
  svg.setAttribute('height', '600');
  document.body.appendChild(svg);
  svg.getBoundingClientRect = () => ({
    width: 800, height: 600, top: 0, left: 0, bottom: 600, right: 800, x: 0, y: 0, toJSON: () => {},
  });
  return svg;
}

describe('renderSankey', () => {
  let svg: SVGSVGElement;

  beforeEach(() => {
    document.body.textContent = '';
    svg = createSvgElement();
  });

  it('renders nodes and links for valid data', () => {
    const callbacks = { onNodeClick: () => {}, onNodeHover: () => {} };
    renderSankey(svg, MOCK_FILTERED, callbacks, 'firms');

    const nodes = svg.querySelectorAll('.sankey-node');
    expect(nodes.length).toBe(4);

    const links = svg.querySelectorAll('.sankey-link');
    expect(links.length).toBe(3);
  });

  it('shows empty message when no data', () => {
    const callbacks = { onNodeClick: () => {}, onNodeHover: () => {} };
    renderSankey(svg, { nodes: [], links: [] }, callbacks, 'firms');

    const text = svg.querySelector('text');
    expect(text?.textContent).toBe('No data to display');
  });

  it('shows unavailable pair message when flagged', () => {
    const callbacks = { onNodeClick: () => {}, onNodeHover: () => {} };
    renderSankey(svg, { nodes: [], links: [], unavailablePair: true }, callbacks, 'firms');

    const text = svg.querySelector('text');
    expect(text?.textContent).toBe('This dimension combination is not available in Census data.');
  });

  it('fires onNodeClick callback', () => {
    let clickedNode: SankeyNode | null = null;
    const callbacks = {
      onNodeClick: (node: SankeyNode) => { clickedNode = node; },
      onNodeHover: () => {},
    };
    renderSankey(svg, MOCK_FILTERED, callbacks, 'firms');

    const rect = svg.querySelector('.sankey-node rect') as SVGRectElement;
    rect?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(clickedNode).not.toBeNull();
  });

  it('uses employees metric when specified', () => {
    const callbacks = { onNodeClick: () => {}, onNodeHover: () => {} };
    // Should not throw — just verifying it accepts the metric param
    renderSankey(svg, MOCK_FILTERED, callbacks, 'employees');
    const nodes = svg.querySelectorAll('.sankey-node');
    expect(nodes.length).toBe(4);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/marius/sources/industry/size-graph && npx vitest run src/__tests__/sankey.test.ts`
Expected: FAIL — `renderSankey` doesn't accept metric parameter, link data shape mismatch

- [ ] **Step 3: Update sankey.ts**

Update `src/sankey.ts` — key changes:
1. Add `Metric` import and `metric` parameter to `renderSankey`
2. Update `DIMENSION_COLORS` keys: `employeeBucket` → `employeeSize`, `revenueBucket` → `revenueSize`
3. Use `getMetricValue` to extract the value for link widths

```typescript
import * as d3 from 'd3';
import { sankey, sankeyLinkHorizontal, SankeyGraph } from 'd3-sankey';
import type { SankeyNode, FilteredSankey, Metric } from './types';
import { getMetricValue } from './data';

const DIMENSION_COLORS: Record<string, readonly string[]> = {
  industry: ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#7c3aed',
             '#4f46e5', '#5b21b6', '#7e22ce', '#9333ea', '#a855f7',
             '#6d28d9', '#4338ca', '#3730a3', '#312e81'],
  employeeSize: ['#22d3ee', '#06b6d4', '#0891b2', '#0e7490', '#155e75',
                  '#164e63', '#0d9488', '#14b8a6', '#2dd4bf', '#5eead4',
                  '#99f6e4'],
  revenueSize: ['#f59e0b', '#d97706', '#b45309', '#92400e', '#78350f',
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
  metric: Metric,
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
      .text(data.unavailablePair
        ? 'This dimension combination is not available in Census data.'
        : 'No data to display');
    return;
  }

  const nodeMap = new Map(data.nodes.map((n, i) => [n.id, i]));
  const graphNodes = data.nodes.map(n => ({ ...n }));
  const graphLinks = data.links
    .filter(l => nodeMap.has(l.source) && nodeMap.has(l.target))
    .map(l => ({
      source: nodeMap.get(l.source)!,
      target: nodeMap.get(l.target)!,
      value: getMetricValue(l, metric),
    }));

  const sankeyLayout = sankey<D3SankeyNode, any>()
    .nodeId(((_d: any, i: number) => i) as any)
    .nodeWidth(20)
    .nodePadding(12)
    .extent([[1, 1], [width - 1, height - 6]]);

  const graph = sankeyLayout({
    nodes: graphNodes,
    links: graphLinks,
  } as any) as unknown as SankeyGraph<D3SankeyNode, D3SankeyLink>;

  function getNodeColor(node: D3SankeyNode): string {
    const colors = DIMENSION_COLORS[node.dimension] || DIMENSION_COLORS.industry;
    const nodesInDim = graph.nodes.filter(n => n.dimension === node.dimension);
    const idx = nodesInDim.indexOf(node);
    return colors[idx % colors.length];
  }

  const linkGroup = svg.append('g').attr('class', 'links');
  const linkPaths = linkGroup.selectAll('.sankey-link')
    .data(graph.links)
    .join('path')
    .attr('class', 'sankey-link')
    .attr('d', sankeyLinkHorizontal())
    .attr('stroke', (d: D3SankeyLink) => getNodeColor(d.source))
    .attr('stroke-width', (d: D3SankeyLink) => Math.max(1, d.width || 1));

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
      linkPaths
        .classed('highlighted', (l: D3SankeyLink) => l.source === d || l.target === d)
        .classed('dimmed', (l: D3SankeyLink) => l.source !== d && l.target !== d);
      callbacks.onNodeHover(d);
    })
    .on('mouseleave', () => {
      linkPaths.classed('highlighted', false).classed('dimmed', false);
      callbacks.onNodeHover(null);
    });

  nodeElements.append('text')
    .attr('x', (d: D3SankeyNode) => (d.x0! < width / 2 ? sankeyLayout.nodeWidth() + 6 : -6))
    .attr('y', (d: D3SankeyNode) => (d.y1! - d.y0!) / 2)
    .attr('dy', '0.35em')
    .attr('text-anchor', (d: D3SankeyNode) => (d.x0! < width / 2 ? 'start' : 'end'))
    .text((d: D3SankeyNode) => d.label);
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/marius/sources/industry/size-graph && npx vitest run src/__tests__/sankey.test.ts`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/sankey.ts src/__tests__/sankey.test.ts
git commit -m "feat: add metric parameter to Sankey renderer"
```

---

### Task 8: Update Controls with Metric Toggle

**Files:**
- Modify: `src/controls.ts`
- Modify: `public/index.html`
- Modify: `src/style.css`

- [ ] **Step 1: Update controls.ts**

Replace `src/controls.ts` with:

```typescript
import type { Dimension, Metric, DrillState } from './types';

const DIMENSION_LABELS: Record<Dimension, string> = {
  industry: 'Industry',
  employeeSize: 'Company Size',
  revenueSize: 'Revenue',
};

interface ControlsCallbacks {
  onDimensionChange: (dimension: Dimension) => void;
  onMetricChange: (metric: Metric) => void;
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

  const metricBtns = document.querySelectorAll<HTMLButtonElement>('#metric-toggle .metric-btn');
  metricBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const metric = btn.dataset.metric as Metric;
      metricBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      callbacks.onMetricChange(metric);
    });
  });
}

export function updateBreadcrumb(state: DrillState, onClick: (level: number) => void): void {
  const container = document.getElementById('breadcrumb');
  if (!container) return;

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

- [ ] **Step 2: Update index.html — add metric toggle and update dimension names**

Replace `public/index.html` with:

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
        <button class="tab" data-dimension="employeeSize">Company Size</button>
        <button class="tab" data-dimension="revenueSize">Revenue</button>
      </nav>
      <div id="metric-toggle">
        <button class="metric-btn active" data-metric="firms">Firms</button>
        <button class="metric-btn" data-metric="employees">Employees</button>
      </div>
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

- [ ] **Step 3: Add metric toggle styles to style.css**

Append to the `#dimension-tabs` section in `src/style.css`:

```css
/* Metric toggle */
#metric-toggle {
  display: flex;
  gap: 4px;
  margin-left: 16px;
}

.metric-btn {
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.metric-btn:hover {
  border-color: var(--accent);
  color: var(--text);
}

.metric-btn.active {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}
```

- [ ] **Step 4: Commit**

```bash
git add src/controls.ts public/index.html src/style.css
git commit -m "feat: add metric toggle (firms/employees) to controls"
```

---

### Task 9: Update Sidebar for Dual Metrics

**Files:**
- Modify: `src/sidebar.ts`

- [ ] **Step 1: Update sidebar.ts**

Replace `src/sidebar.ts` with:

```typescript
import type { SankeyNode, FilteredSankey, Metric } from './types';
import { getMetricValue } from './data';

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

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

export function updateSidebar(data: FilteredSankey, hoveredNode: SankeyNode | null, metric: Metric): void {
  const content = document.getElementById('sidebar-content');
  if (!content) return;

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

  // Show both metrics in totals
  const totalFirms = data.links.reduce((sum, l) => sum + l.firms, 0);
  const totalEmployees = data.links.reduce((sum, l) => sum + l.employees, 0);
  content.appendChild(createStatElement('Total Firms', formatNumber(totalFirms)));
  content.appendChild(createStatElement('Total Employees', formatNumber(totalEmployees)));

  if (hoveredNode) {
    const connectedLinks = data.links.filter(
      l => l.source === hoveredNode.id || l.target === hoveredNode.id
    );
    const nodeMetric = connectedLinks.reduce((sum, l) => sum + getMetricValue(l, metric), 0);
    const totalMetric = data.links.reduce((sum, l) => sum + getMetricValue(l, metric), 0);
    const pct = totalMetric > 0 ? ((nodeMetric / totalMetric) * 100).toFixed(1) : '0';

    const metricLabel = metric === 'firms' ? 'firms' : 'employees';
    content.appendChild(createStatElement(
      hoveredNode.label,
      `${formatNumber(nodeMetric)} ${metricLabel} (${pct}%)`,
      'border-left: 3px solid var(--accent);'
    ));

    const breakdown = connectedLinks
      .map(l => {
        const otherId = l.source === hoveredNode.id ? l.target : l.source;
        const otherNode = data.nodes.find(n => n.id === otherId);
        return { label: otherNode?.label || otherId, value: getMetricValue(l, metric) };
      })
      .sort((a, b) => b.value - a.value);

    for (const item of breakdown.slice(0, 10)) {
      const itemPct = nodeMetric > 0 ? ((item.value / nodeMetric) * 100).toFixed(1) : '0';
      content.appendChild(createStatElement(
        item.label,
        `${formatNumber(item.value)} (${itemPct}%)`
      ));
    }
  } else {
    const nodeTotals = data.nodes.map(n => {
      const total = data.links
        .filter(l => l.source === n.id || l.target === n.id)
        .reduce((sum, l) => sum + getMetricValue(l, metric), 0);
      return { node: n, total };
    }).sort((a, b) => b.total - a.total);

    const metricLabel = metric === 'firms' ? 'firms' : 'employees';
    for (const { node, total } of nodeTotals.slice(0, 10)) {
      content.appendChild(createStatElement(
        node.label,
        `${formatNumber(total)} ${metricLabel}`
      ));
    }
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add src/sidebar.ts
git commit -m "feat: update sidebar with dual metrics and number formatting"
```

---

### Task 10: Wire Up Main Entry Point

**Files:**
- Modify: `src/main.ts`

- [ ] **Step 1: Rewrite main.ts**

Replace `src/main.ts` with:

```typescript
import { loadSankeyData, filterSankeyForDrill, getAvailableDimensions } from './data';
import { renderSankey } from './sankey';
import { initControls, updateBreadcrumb } from './controls';
import { updateSidebar } from './sidebar';
import type { SankeyData, SankeyNode, DrillState, Dimension, Metric, FilteredSankey } from './types';

let sankeyData: SankeyData;
let currentState: DrillState = {
  path: ['industry', 'employeeSize'],
  selections: [],
};
let currentMetric: Metric = 'firms';
let currentFiltered: FilteredSankey;

function getDefaultSecondDimension(startDim: Dimension): Dimension | undefined {
  const available = getAvailableDimensions([startDim], sankeyData.availablePairs);
  return available[0];
}

function refresh(): void {
  const svg = document.getElementById('sankey-svg') as unknown as SVGSVGElement;
  if (!svg || !sankeyData) return;

  currentFiltered = filterSankeyForDrill(sankeyData, currentState);
  renderSankey(svg, currentFiltered, {
    onNodeClick: handleNodeClick,
    onNodeHover: handleNodeHover,
  }, currentMetric);
  updateSidebar(currentFiltered, null, currentMetric);
  updateBreadcrumb(currentState, handleBreadcrumbClick);
}

function handleNodeClick(node: SankeyNode): void {
  const available = getAvailableDimensions(currentState.path, sankeyData.availablePairs);
  if (available.length === 0) return;

  currentState = {
    path: [...currentState.path, available[0]],
    selections: [...currentState.selections, node.label],
  };
  refresh();
}

function handleNodeHover(node: SankeyNode | null): void {
  updateSidebar(currentFiltered, node, currentMetric);
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
  if (!secondDim) return; // no valid pair for this dimension
  currentState = {
    path: [dimension, secondDim],
    selections: [],
  };
  refresh();
}

function handleMetricChange(metric: Metric): void {
  currentMetric = metric;
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
    onMetricChange: handleMetricChange,
  });

  let resizeTimer: ReturnType<typeof setTimeout>;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(refresh, 150);
  });

  refresh();
}

init();
```

- [ ] **Step 2: Run all frontend tests**

Run: `cd /home/marius/sources/industry/size-graph && npx vitest run`
Expected: All tests PASS

- [ ] **Step 3: Run TypeScript compilation check**

Run: `cd /home/marius/sources/industry/size-graph && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add src/main.ts
git commit -m "feat: wire up metric toggle and availablePairs in main entry"
```

---

### Task 11: Remove Old Data Files and Run Full Pipeline

**Files:**
- Remove: `public/data/companies.json` (no longer generated)

- [ ] **Step 1: Remove old data files**

```bash
rm -f /home/marius/sources/industry/size-graph/public/data/companies.json
rm -f /home/marius/sources/industry/size-graph/public/data/sankey-data.json
```

- [ ] **Step 2: Run the Census pipeline to generate fresh data**

Run: `cd /home/marius/sources/industry/size-graph/data && python pipeline.py`
Expected: Output showing records fetched from Census API and JSON exported

- [ ] **Step 3: Verify the output file looks correct**

Run: `cd /home/marius/sources/industry/size-graph && python -c "import json; d=json.load(open('public/data/sankey-data.json')); print(f'Nodes: {len(d[\"nodes\"])}, Links: {len(d[\"links\"])}, Pairs: {d[\"availablePairs\"]}')" `
Expected: ~28 nodes (18 industries + ~8 emp sizes + ~10 rev sizes, minus any fully suppressed), ~280+ links, availablePairs with 2 entries

- [ ] **Step 4: Run all tests (Python + Frontend)**

```bash
cd /home/marius/sources/industry/size-graph && python -m pytest data/tests/ -v && npx vitest run
```
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
cd /home/marius/sources/industry/size-graph
git rm public/data/companies.json 2>/dev/null; true
git add public/data/sankey-data.json
git commit -m "feat: generate Census data, remove old company data files"
```

