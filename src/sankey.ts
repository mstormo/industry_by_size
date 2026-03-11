import * as d3 from 'd3';
import { sankey, sankeyLinkHorizontal, SankeyGraph } from 'd3-sankey';
import type { SankeyNode, FilteredSankey } from './types';

// Color palette for dimensions
const DIMENSION_COLORS: Record<string, readonly string[]> = {
  industry: ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#7c3aed',
             '#4f46e5', '#5b21b6', '#7e22ce', '#9333ea', '#a855f7',
             '#6d28d9', '#4338ca', '#3730a3', '#312e81'],
  employeeBucket: ['#22d3ee', '#06b6d4', '#0891b2', '#0e7490', '#155e75',
                    '#164e63', '#0d9488', '#14b8a6', '#2dd4bf', '#5eead4',
                    '#99f6e4'],
  revenueBucket: ['#f59e0b', '#d97706', '#b45309', '#92400e', '#78350f',
                  '#f97316', '#ea580c', '#c2410c'],
};

interface SankeyCallbacks {
  onNodeClick: (node: SankeyNode) => void;
  onNodeHover: (node: SankeyNode | null) => void;
}

interface D3SankeyNode extends SankeyNode {
  x0?: number;
  x1?: number;
  y0?: number;
  y1?: number;
}

interface D3SankeyLink {
  source: D3SankeyNode;
  target: D3SankeyNode;
  value: number;
  width?: number;
}

export function renderSankey(
  svgElement: SVGSVGElement,
  data: FilteredSankey,
  callbacks: SankeyCallbacks,
): void {
  const svg = d3.select(svgElement);
  const { width, height } = svgElement.getBoundingClientRect();

  if (width === 0 || height === 0) return;

  svg.selectAll('*').remove();

  if (data.nodes.length === 0 || data.links.length === 0) {
    svg.append('text')
      .attr('x', width / 2)
      .attr('y', height / 2)
      .attr('text-anchor', 'middle')
      .attr('fill', '#94a3b8')
      .text('No data to display');
    return;
  }

  const nodeMap = new Map(data.nodes.map((n, i) => [n.id, i]));
  const graphNodes = data.nodes.map(n => ({ ...n }));
  const graphLinks = data.links
    .filter(l => nodeMap.has(l.source) && nodeMap.has(l.target))
    .map(l => ({
      source: nodeMap.get(l.source)!,
      target: nodeMap.get(l.target)!,
      value: l.value,
    }));

  const sankeyLayout = sankey<D3SankeyNode, any>()
    .nodeId(((_d: any, i: number) => i) as any)
    .nodeWidth(20)
    .nodePadding(12)
    .extent([[1, 1], [width - 1, height - 6]]);

  const graph = sankeyLayout({
    nodes: graphNodes,
    links: graphLinks,
  } as any) as unknown as SankeyGraph<D3SankeyNode, D3SankeyLink>;

  function getNodeColor(node: D3SankeyNode): string {
    const colors = DIMENSION_COLORS[node.dimension] || DIMENSION_COLORS.industry;
    const nodesInDim = graph.nodes.filter(n => n.dimension === node.dimension);
    const idx = nodesInDim.indexOf(node);
    return colors[idx % colors.length];
  }

  // Draw links
  const linkGroup = svg.append('g').attr('class', 'links');
  const linkPaths = linkGroup.selectAll('.sankey-link')
    .data(graph.links)
    .join('path')
    .attr('class', 'sankey-link')
    .attr('d', sankeyLinkHorizontal())
    .attr('stroke', (d: D3SankeyLink) => getNodeColor(d.source))
    .attr('stroke-width', (d: D3SankeyLink) => Math.max(1, d.width || 1));

  // Draw nodes
  const nodeGroup = svg.append('g').attr('class', 'nodes');
  const nodeElements = nodeGroup.selectAll('.sankey-node')
    .data(graph.nodes)
    .join('g')
    .attr('class', 'sankey-node')
    .attr('transform', (d: D3SankeyNode) => `translate(${d.x0},${d.y0})`);

  nodeElements.append('rect')
    .attr('height', (d: D3SankeyNode) => (d.y1! - d.y0!))
    .attr('width', sankeyLayout.nodeWidth())
    .attr('fill', (d: D3SankeyNode) => getNodeColor(d))
    .attr('rx', 3)
    .on('click', (_event: MouseEvent, d: D3SankeyNode) => {
      callbacks.onNodeClick(d);
    })
    .on('mouseenter', (_event: MouseEvent, d: D3SankeyNode) => {
      linkPaths
        .classed('highlighted', (l: D3SankeyLink) => l.source === d || l.target === d)
        .classed('dimmed', (l: D3SankeyLink) => l.source !== d && l.target !== d);
      callbacks.onNodeHover(d);
    })
    .on('mouseleave', () => {
      linkPaths.classed('highlighted', false).classed('dimmed', false);
      callbacks.onNodeHover(null);
    });

  // Add labels
  nodeElements.append('text')
    .attr('x', (d: D3SankeyNode) => (d.x0! < width / 2 ? sankeyLayout.nodeWidth() + 6 : -6))
    .attr('y', (d: D3SankeyNode) => (d.y1! - d.y0!) / 2)
    .attr('dy', '0.35em')
    .attr('text-anchor', (d: D3SankeyNode) => (d.x0! < width / 2 ? 'start' : 'end'))
    .text((d: D3SankeyNode) => d.label);
}
