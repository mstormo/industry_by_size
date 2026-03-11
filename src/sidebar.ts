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
