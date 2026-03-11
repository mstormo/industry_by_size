import { describe, it, expect, beforeEach } from 'vitest';
import { renderSankey } from '../sankey';
import type { FilteredSankey, SankeyNode } from '../types';

const MOCK_FILTERED: FilteredSankey = {
  nodes: [
    { id: 'industry:Technology', label: 'Technology', dimension: 'industry' },
    { id: 'industry:Healthcare', label: 'Healthcare', dimension: 'industry' },
    { id: 'employeeBucket:100-249', label: '100-249', dimension: 'employeeBucket' },
    { id: 'employeeBucket:10K+', label: '10K+', dimension: 'employeeBucket' },
  ],
  links: [
    { source: 'industry:Technology', target: 'employeeBucket:100-249', value: 25 },
    { source: 'industry:Technology', target: 'employeeBucket:10K+', value: 8 },
    { source: 'industry:Healthcare', target: 'employeeBucket:100-249', value: 15 },
  ],
};

function createSvgElement(): SVGSVGElement {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', '800');
  svg.setAttribute('height', '600');
  document.body.appendChild(svg);
  svg.getBoundingClientRect = () => ({
    width: 800, height: 600, top: 0, left: 0, bottom: 600, right: 800, x: 0, y: 0, toJSON: () => {},
  });
  return svg;
}

describe('renderSankey', () => {
  let svg: SVGSVGElement;

  beforeEach(() => {
    document.body.textContent = '';
    svg = createSvgElement();
  });

  it('renders nodes and links for valid data', () => {
    const callbacks = { onNodeClick: () => {}, onNodeHover: () => {} };
    renderSankey(svg, MOCK_FILTERED, callbacks);

    const nodes = svg.querySelectorAll('.sankey-node');
    expect(nodes.length).toBe(4);

    const links = svg.querySelectorAll('.sankey-link');
    expect(links.length).toBe(3);
  });

  it('shows empty message when no data', () => {
    const callbacks = { onNodeClick: () => {}, onNodeHover: () => {} };
    renderSankey(svg, { nodes: [], links: [] }, callbacks);

    const text = svg.querySelector('text');
    expect(text?.textContent).toBe('No data to display');
  });

  it('fires onNodeClick callback', () => {
    let clickedNode: SankeyNode | null = null;
    const callbacks = {
      onNodeClick: (node: SankeyNode) => { clickedNode = node; },
      onNodeHover: () => {},
    };
    renderSankey(svg, MOCK_FILTERED, callbacks);

    const rect = svg.querySelector('.sankey-node rect') as SVGRectElement;
    rect?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(clickedNode).not.toBeNull();
  });
});
