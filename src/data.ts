import type { SankeyData, SankeyNode, DrillState, Dimension, FilteredSankey, SankeyLink, Metric, RegionsData } from './types';

const cache = new Map<string, SankeyData>();
let cachedRegions: RegionsData | null = null;

/** Explicit sort order for US employee size labels (smallest → largest). */
const EMPSIZE_ORDER: Record<string, number> = {
  '<5': 0,
  '5-9': 1,
  '10-24': 2,
  '25-49': 3,
  '50-99': 4,
  '100-249': 5,
  '250-499': 6,
  '500-999': 7,
  '1,000-2,499': 8,
  '2,500-4,999': 9,
  '5,000+': 10,
};

/** Explicit sort order for OECD employee size labels (smallest → largest). */
const OECD_EMPSIZE_ORDER: Record<string, number> = {
  '1-9': 0,
  '10-19': 1,
  '20-49': 2,
  '50-249': 3,
  '250+': 4,
};

/** Explicit sort order for revenue size labels (smallest → largest). */
const RCPSIZE_ORDER: Record<string, number> = {
  '<$100K': 0,
  '$100-250K': 1,
  '$250-500K': 2,
  '$500K-1M': 3,
  '$1-2.5M': 4,
  '$2.5-5M': 5,
  '$5-10M': 6,
  '$10-25M': 7,
  '$25-100M': 8,
  '$100M+': 9,
};

function getNodeSortKey(node: SankeyNode): string | number {
  if (node.dimension === 'employeeSize') {
    return EMPSIZE_ORDER[node.label] ?? OECD_EMPSIZE_ORDER[node.label] ?? 99;
  }
  if (node.dimension === 'revenueSize') {
    return RCPSIZE_ORDER[node.label] ?? 99;
  }
  // Industry: alphabetical by label
  return node.label;
}

export function sortNodes(nodes: SankeyNode[]): SankeyNode[] {
  return [...nodes].sort((a, b) => {
    const ka = getNodeSortKey(a);
    const kb = getNodeSortKey(b);
    if (typeof ka === 'number' && typeof kb === 'number') return ka - kb;
    return String(ka).localeCompare(String(kb));
  });
}

export async function loadRegions(): Promise<RegionsData> {
  if (cachedRegions) return cachedRegions;
  const resp = await fetch('/data/regions.json');
  if (!resp.ok) throw new Error(`Failed to load regions: ${resp.status}`);
  cachedRegions = await resp.json();
  return cachedRegions!;
}

export async function loadSankeyData(regionId: string): Promise<SankeyData> {
  const cached = cache.get(regionId);
  if (cached) return cached;
  const resp = await fetch(`/data/sankey-${regionId}.json`);
  if (!resp.ok) throw new Error(`Failed to load data for region ${regionId}: ${resp.status}`);
  const data: SankeyData = await resp.json();
  cache.set(regionId, data);
  return data;
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
  const nodes = sortNodes(data.nodes.filter(n => nodeIds.has(n.id)));

  return { nodes, links };
}
