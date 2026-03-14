import { loadSankeyData, loadRegions, filterSankeyForDrill, getAvailableDimensions, getMetricValue } from './data';
import { renderSankey, SankeyHandle } from './sankey';
import { initControls, setRevenueTabEnabled, setActiveTab, updateBreadcrumb } from './controls';
import { updateSidebars } from './sidebar';
import type { SankeyData, SankeyNode, DrillState, Dimension, Metric, FilteredSankey, RegionsData, RegionInfo } from './types';

let sankeyData: SankeyData;
let regionsData: RegionsData;
let currentRegionId: string = 'us';
let currentState: DrillState = {
  path: ['industry', 'employeeSize'],
  selections: [],
};
let currentMetric: Metric = 'firms';
let currentFiltered: FilteredSankey;
let currentSelectedIds: Set<string> = new Set();
let sankeyHandle: SankeyHandle | null = null;

function getCurrentRegion(): RegionInfo | undefined {
  return regionsData?.regions.find(r => r.id === currentRegionId);
}

function leftDim(): Dimension {
  return currentState.path[0];
}

function rightDim(): Dimension {
  return currentState.path[currentState.path.length - 1];
}

function refreshSidebars(hoveredNode: SankeyNode | null): void {
  updateSidebars(leftDim(), rightDim(), {
    data: currentFiltered,
    metric: currentMetric,
    selectedIds: currentSelectedIds,
    hoveredNode,
    callbacks: {
      onToggleNode: toggleSelection,
      onClearSelection: clearSelection,
    },
  });
}

function toggleSelection(nodeId: string): void {
  if (nodeId === '__clear__') {
    clearSelection();
    return;
  }
  if (currentSelectedIds.has(nodeId)) {
    currentSelectedIds.delete(nodeId);
  } else {
    currentSelectedIds.add(nodeId);
  }
  sankeyHandle?.updateSelection(currentSelectedIds);
  refreshSidebars(null);
  updateSelectionSummary();
}

function clearSelection(): void {
  currentSelectedIds = new Set();
  sankeyHandle?.updateSelection(currentSelectedIds);
  refreshSidebars(null);
  updateSelectionSummary();
}

function formatCompact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

function setSummaryContent(el: HTMLElement, parts: { text: string; className: string }[]): void {
  while (el.firstChild) el.removeChild(el.firstChild);
  for (const part of parts) {
    const span = document.createElement('span');
    span.className = part.className;
    span.textContent = part.text;
    el.appendChild(span);
  }
}

function updateSelectionSummary(): void {
  const el = document.getElementById('selection-summary');
  if (!el) return;

  if (currentSelectedIds.size === 0) {
    el.textContent = '';
    return;
  }

  const metricLabel = currentMetric === 'firms' ? 'firms' : 'employees';
  const left = leftDim();
  const right = rightDim();

  const leftSelected = [...currentSelectedIds].filter(id => {
    const node = currentFiltered.nodes.find(n => n.id === id);
    return node && node.dimension === left;
  });
  const rightSelected = [...currentSelectedIds].filter(id => {
    const node = currentFiltered.nodes.find(n => n.id === id);
    return node && node.dimension === right;
  });

  if (leftSelected.length === 0 && rightSelected.length === 0) {
    el.textContent = '';
    return;
  }

  // Total = sum of links connected to left-side selections (or grand total if none)
  const totalLinks = leftSelected.length > 0
    ? currentFiltered.links.filter(l => leftSelected.some(id => l.source === id || l.target === id))
    : currentFiltered.links;
  const total = totalLinks.reduce((sum, l) => sum + getMetricValue(l, currentMetric), 0);

  if (leftSelected.length > 0 && rightSelected.length > 0) {
    // Selected = links connecting both sides
    const selected = totalLinks
      .filter(l => rightSelected.some(id => l.source === id || l.target === id))
      .reduce((sum, l) => sum + getMetricValue(l, currentMetric), 0);

    setSummaryContent(el, [
      { text: formatCompact(selected), className: 'summary-selected' },
      { text: ` of ${formatCompact(total)} ${metricLabel}`, className: 'summary-total' },
    ]);
  } else {
    // Only one side selected — show just the total for that side
    const sideSelected = leftSelected.length > 0 ? leftSelected : rightSelected;
    const sideTotal = currentFiltered.links
      .filter(l => sideSelected.some(id => l.source === id || l.target === id))
      .reduce((sum, l) => sum + getMetricValue(l, currentMetric), 0);

    setSummaryContent(el, [
      { text: `${formatCompact(sideTotal)} ${metricLabel}`, className: 'summary-selected' },
    ]);
  }
}

function updateSourceAttribution(): void {
  const el = document.getElementById('source-attribution');
  if (!el) return;
  if (currentRegionId === 'us') {
    const dim = rightDim();
    if (dim === 'employeeSize') {
      el.textContent = 'Source: SUSB 2022, Census Bureau';
    } else if (dim === 'revenueSize') {
      el.textContent = 'Source: Economic Census 2022, Census Bureau';
    } else {
      el.textContent = '';
    }
  } else {
    el.textContent = 'Source: OECD SDBS 2023';
  }
}

function refresh(): void {
  const svg = document.getElementById('sankey-svg') as unknown as SVGSVGElement;
  if (!svg || !sankeyData) return;

  currentSelectedIds = new Set();
  currentFiltered = filterSankeyForDrill(sankeyData, currentState);
  sankeyHandle = renderSankey(svg, currentFiltered, {
    onToggleNode: toggleSelection,
    onNodeDblClick: handleNodeDblClick,
    onNodeHover: handleNodeHover,
  }, currentMetric, currentSelectedIds);
  refreshSidebars(null);
  updateSelectionSummary();
  updateBreadcrumb(currentState, handleBreadcrumbClick);
  updateSourceAttribution();
}

function handleNodeDblClick(node: SankeyNode): void {
  const available = getAvailableDimensions(currentState.path, sankeyData.availablePairs);
  if (available.length === 0) return;

  currentState = {
    path: [...currentState.path, available[0]],
    selections: [...currentState.selections, node.label],
  };
  refresh();
}

function handleNodeHover(node: SankeyNode | null): void {
  refreshSidebars(node);
}

function handleBreadcrumbClick(level: number): void {
  currentState = {
    path: currentState.path.slice(0, level + 2),
    selections: currentState.selections.slice(0, level + 1),
  };
  refresh();
}

function handleDimensionChange(dimension: Dimension): void {
  // Industry is always on the left; the tab selects the right-side dimension.
  const rightDim = dimension === 'industry' ? 'employeeSize' : dimension;
  currentState = {
    path: ['industry', rightDim],
    selections: [],
  };
  refresh();
}

function handleMetricChange(metric: Metric): void {
  currentMetric = metric;
  refresh();
}

async function handleRegionChange(regionId: string): Promise<void> {
  const previousRegionId = currentRegionId;
  currentRegionId = regionId;
  const region = getCurrentRegion();

  // Update Revenue tab state
  setRevenueTabEnabled(region?.hasRevenue ?? false);

  // If on revenue tab and new region has no revenue, switch to employee size
  if (rightDim() === 'revenueSize' && !region?.hasRevenue) {
    currentState = { path: ['industry', 'employeeSize'], selections: [] };
    setActiveTab('industry');
  } else {
    currentState = { ...currentState, selections: [] };
  }

  try {
    sankeyData = await loadSankeyData(regionId);
    refresh();
  } catch (e) {
    console.error('Failed to load region data:', e);
    // Revert to previous region
    currentRegionId = previousRegionId;
    const regionSelect = document.getElementById('region-select') as HTMLSelectElement | null;
    if (regionSelect) regionSelect.value = previousRegionId;
    setRevenueTabEnabled(getCurrentRegion()?.hasRevenue ?? false);
    refresh();
  }
}

async function init(): Promise<void> {
  // Load regions data (fallback to US-only if unavailable)
  try {
    regionsData = await loadRegions();
  } catch {
    regionsData = {
      regions: [{ id: 'us', label: 'United States', group: null, hasRevenue: true }],
      groups: {},
    };
    // Hide region selector since we only have US
    const regionSelect = document.getElementById('region-select');
    if (regionSelect) regionSelect.style.display = 'none';
  }

  // Load initial sankey data
  try {
    sankeyData = await loadSankeyData('us');
  } catch {
    const container = document.getElementById('sankey-container');
    if (container) {
      const msg = document.createElement('div');
      msg.setAttribute('style', 'display:flex;align-items:center;justify-content:center;height:100%;color:#94a3b8;');
      const p = document.createElement('p');
      p.textContent = 'Failed to load data. Run the Python pipeline first: python3 -m data.pipeline';
      msg.appendChild(p);
      while (container.firstChild) container.removeChild(container.firstChild);
      container.appendChild(msg);
    }
    return;
  }

  initControls(regionsData, {
    onDimensionChange: handleDimensionChange,
    onMetricChange: handleMetricChange,
    onRegionChange: handleRegionChange,
    initialRegionId: currentRegionId,
  });

  let resizeTimer: ReturnType<typeof setTimeout>;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(refresh, 150);
  });

  refresh();
}

init();
