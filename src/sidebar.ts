import type { SankeyNode, FilteredSankey } from './types';

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

export function updateSidebar(data: FilteredSankey, hoveredNode: SankeyNode | null): void {
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

  const totalValue = data.links.reduce((sum, l) => sum + l.value, 0);
  content.appendChild(createStatElement('Total Companies', totalValue.toLocaleString()));

  if (hoveredNode) {
    const connectedLinks = data.links.filter(
      l => l.source === hoveredNode.id || l.target === hoveredNode.id
    );
    const nodeTotal = connectedLinks.reduce((sum, l) => sum + l.value, 0);
    const pct = totalValue > 0 ? ((nodeTotal / totalValue) * 100).toFixed(1) : '0';

    content.appendChild(createStatElement(
      hoveredNode.label,
      `${nodeTotal.toLocaleString()} companies (${pct}%)`,
      'border-left: 3px solid var(--accent);'
    ));

    const isSource = connectedLinks.some(l => l.source === hoveredNode.id);
    const breakdown = connectedLinks
      .map(l => {
        const otherId = isSource ? l.target : l.source;
        const otherNode = data.nodes.find(n => n.id === otherId);
        return { label: otherNode?.label || otherId, value: l.value };
      })
      .sort((a, b) => b.value - a.value);

    for (const item of breakdown.slice(0, 10)) {
      const itemPct = nodeTotal > 0 ? ((item.value / nodeTotal) * 100).toFixed(1) : '0';
      content.appendChild(createStatElement(
        item.label,
        `${item.value.toLocaleString()} (${itemPct}%)`
      ));
    }
  } else {
    const nodeTotals = data.nodes.map(n => {
      const total = data.links
        .filter(l => l.source === n.id || l.target === n.id)
        .reduce((sum, l) => sum + l.value, 0);
      return { node: n, total };
    }).sort((a, b) => b.total - a.total);

    for (const { node, total } of nodeTotals.slice(0, 10)) {
      content.appendChild(createStatElement(
        node.label,
        `${total.toLocaleString()} companies`
      ));
    }
  }
}
