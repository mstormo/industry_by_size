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
