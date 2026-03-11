import type { SankeyData, DrillState, Dimension, FilteredSankey } from './types';

const ALL_DIMENSIONS: Dimension[] = ['industry', 'employeeBucket', 'revenueBucket'];

let cachedData: SankeyData | null = null;

export async function loadSankeyData(): Promise<SankeyData> {
  if (cachedData) return cachedData;
  const resp = await fetch('/data/sankey-data.json');
  if (!resp.ok) throw new Error(`Failed to load sankey data: ${resp.status} ${resp.statusText}`);
  cachedData = await resp.json();
  return cachedData!;
}

export function getAvailableDimensions(usedDimensions: Dimension[]): Dimension[] {
  return ALL_DIMENSIONS.filter(d => !usedDimensions.includes(d));
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
