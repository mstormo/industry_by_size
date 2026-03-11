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
  if (!secondDim) return;
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
