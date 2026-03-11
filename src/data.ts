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
    links = data.links.filter(
      l => l.source.startsWith(`${sourceDim}:`) && l.target.startsWith(`${targetDim}:`)
    );
  } else {
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

  const nodeIds = new Set<string>();
  for (const l of links) {
    nodeIds.add(l.source);
    nodeIds.add(l.target);
  }
  const nodes = data.nodes.filter(n => nodeIds.has(n.id));

  return { nodes, links };
}
