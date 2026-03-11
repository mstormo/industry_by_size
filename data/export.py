import json
from pathlib import Path
from collections import defaultdict
from itertools import permutations

from data.models import Company, SankeyData, SankeyNode, SankeyLink

EXPORT_DIMENSIONS = ["industry", "employeeBucket", "revenueBucket"]


def generate_sankey_data(companies: list[Company]) -> SankeyData:
    nodes_set: set[tuple[str, str, str]] = set()  # (id, label, dimension)
    link_counts: defaultdict[tuple[str, str], int] = defaultdict(int)

    dims = EXPORT_DIMENSIONS

    # Generate links for all pairs and triples
    for perm in permutations(dims, 2):
        source_dim, target_dim = perm
        for c in companies:
            source_val: str | None = getattr(c, source_dim)
            target_val: str | None = getattr(c, target_dim)
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
