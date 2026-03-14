import type { SankeyNode, FilteredSankey, Metric, Dimension } from './types';
import { getMetricValue, sortNodes } from './data';

const DIMENSION_LABELS: Record<Dimension, string> = {
  industry: 'Industry',
  employeeSize: 'Employee Size',
  revenueSize: 'Revenue Size',
};

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

function createStatElement(
  label: string,
  value: string,
  opts: { selected?: boolean; hovered?: boolean; onClick?: () => void },
): HTMLElement {
  const stat = document.createElement('div');
  stat.className = 'sidebar-stat';
  if (opts.selected) stat.classList.add('sidebar-stat--selected');
  if (opts.hovered) stat.classList.add('sidebar-stat--hovered');
  if (opts.onClick) {
    stat.classList.add('sidebar-stat--clickable');
    stat.addEventListener('click', opts.onClick);
  }

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

export interface SidebarCallbacks {
  onToggleNode: (nodeId: string) => void;
  onClearSelection: () => void;
}

interface SidebarOptions {
  data: FilteredSankey;
  metric: Metric;
  selectedIds: Set<string>;
  hoveredNode: SankeyNode | null;
  callbacks: SidebarCallbacks;
}

function renderPanel(
  titleEl: HTMLElement | null,
  contentEl: HTMLElement | null,
  dimension: Dimension,
  opts: SidebarOptions,
): void {
  if (!titleEl || !contentEl) return;

  const { data, metric, selectedIds, hoveredNode, callbacks } = opts;

  // Build header with title and clear button
  while (titleEl.firstChild) titleEl.removeChild(titleEl.firstChild);
  const titleText = document.createElement('span');
  titleText.textContent = DIMENSION_LABELS[dimension];
  titleEl.appendChild(titleText);

  if (selectedIds.size > 0) {
    const clearBtn = document.createElement('button');
    clearBtn.className = 'clear-selection-btn';
    clearBtn.title = 'Clear all selections';
    clearBtn.textContent = '\u00d7'; // × character
    clearBtn.addEventListener('click', () => callbacks.onClearSelection());
    titleEl.appendChild(clearBtn);
  }

  while (contentEl.firstChild) contentEl.removeChild(contentEl.firstChild);

  if (data.nodes.length === 0) {
    const p = document.createElement('p');
    p.className = 'placeholder';
    p.textContent = 'No data to display';
    contentEl.appendChild(p);
    return;
  }

  const dimNodes = sortNodes(data.nodes.filter(n => n.dimension === dimension));
  const metricLabel = metric === 'firms' ? 'firms' : 'employees';

  // Determine which links to consider based on selection on the OTHER side
  const otherSelected = [...selectedIds].filter(id => {
    const node = data.nodes.find(n => n.id === id);
    return node && node.dimension !== dimension;
  });

  const relevantLinks = otherSelected.length > 0
    ? data.links.filter(l => otherSelected.some(id => l.source === id || l.target === id))
    : data.links;

  // Build totals for each node, preserving dimension-aware sort order
  const nodeTotals = dimNodes.map(n => {
    const nodeLinks = relevantLinks.filter(l => l.source === n.id || l.target === n.id);
    const total = nodeLinks.reduce((sum, l) => sum + getMetricValue(l, metric), 0);
    return { node: n, total };
  });

  const grandTotal = nodeTotals.reduce((sum, nt) => sum + nt.total, 0);

  // Show grand total (not clickable)
  contentEl.appendChild(createStatElement(
    `Total ${metricLabel}`,
    formatNumber(grandTotal),
    {},
  ));

  // Highlight hovered node if it's on this side
  const hoveredOnThisSide = hoveredNode && hoveredNode.dimension === dimension ? hoveredNode : null;

  // Show each node's stats (clickable to toggle)
  for (const { node, total } of nodeTotals) {
    if (total === 0) continue;
    const pct = grandTotal > 0 ? ((total / grandTotal) * 100).toFixed(1) : '0';
    const isSelected = selectedIds.has(node.id);
    const isHovered = hoveredOnThisSide?.id === node.id;
    contentEl.appendChild(createStatElement(
      node.label,
      `${formatNumber(total)} ${metricLabel} (${pct}%)`,
      {
        selected: isSelected,
        hovered: isHovered,
        onClick: () => callbacks.onToggleNode(node.id),
      },
    ));
  }
}

/**
 * Update both sidebar panels.
 * leftDim/rightDim correspond to the source/target dimensions of the current Sankey view.
 */
export function updateSidebars(
  leftDim: Dimension,
  rightDim: Dimension,
  opts: SidebarOptions,
): void {
  renderPanel(
    document.getElementById('sidebar-left-title'),
    document.getElementById('sidebar-left-content'),
    leftDim,
    opts,
  );
  renderPanel(
    document.getElementById('sidebar-right-title'),
    document.getElementById('sidebar-right-content'),
    rightDim,
    opts,
  );
}
