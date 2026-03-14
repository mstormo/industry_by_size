import { describe, it, expect, beforeEach } from 'vitest';
import { renderSankey } from '../sankey';
import type { FilteredSankey } from '../types';

const MOCK_FILTERED: FilteredSankey = {
  nodes: [
    { id: 'industry:Manufacturing', label: 'Manufacturing', dimension: 'industry' },
    { id: 'industry:Information', label: 'Information', dimension: 'industry' },
    { id: 'employeeSize:100-249', label: '100-249', dimension: 'employeeSize' },
    { id: 'employeeSize:500+', label: '500+', dimension: 'employeeSize' },
  ],
  links: [
    { source: 'industry:Manufacturing', target: 'employeeSize:100-249', firms: 13573, employees: 943335 },
    { source: 'industry:Manufacturing', target: 'employeeSize:500+', firms: 3200, employees: 2100000 },
    { source: 'industry:Information', target: 'employeeSize:100-249', firms: 8500, employees: 590000 },
  ],
};

const NO_SELECTION = new Set<string>();

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

function makeCallbacks() {
  return { onToggleNode: () => {}, onNodeDblClick: () => {}, onNodeHover: () => {} };
}

describe('renderSankey', () => {
  let svg: SVGSVGElement;

  beforeEach(() => {
    document.body.textContent = '';
    svg = createSvgElement();
  });

  it('renders nodes and links for valid data', () => {
    renderSankey(svg, MOCK_FILTERED, makeCallbacks(), 'firms', NO_SELECTION);

    const nodes = svg.querySelectorAll('.sankey-node');
    expect(nodes.length).toBe(4);

    const links = svg.querySelectorAll('.sankey-link');
    expect(links.length).toBe(3);
  });

  it('shows empty message when no data', () => {
    renderSankey(svg, { nodes: [], links: [] }, makeCallbacks(), 'firms', NO_SELECTION);

    const text = svg.querySelector('text');
    expect(text?.textContent).toBe('No data to display');
  });

  it('shows unavailable pair message when flagged', () => {
    renderSankey(svg, { nodes: [], links: [], unavailablePair: true }, makeCallbacks(), 'firms', NO_SELECTION);

    const text = svg.querySelector('text');
    expect(text?.textContent).toBe('This dimension combination is not available in Census data.');
  });

  it('fires onToggleNode callback on click', () => {
    let toggledId: string | null = null;
    const callbacks = {
      onToggleNode: (id: string) => { toggledId = id; },
      onNodeDblClick: () => {},
      onNodeHover: () => {},
    };
    renderSankey(svg, MOCK_FILTERED, callbacks, 'firms', NO_SELECTION);

    const rect = svg.querySelector('.sankey-node rect') as SVGRectElement;
    rect?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(toggledId).not.toBeNull();
  });

  it('uses employees metric when specified', () => {
    renderSankey(svg, MOCK_FILTERED, makeCallbacks(), 'employees', NO_SELECTION);
    const nodes = svg.querySelectorAll('.sankey-node');
    expect(nodes.length).toBe(4);
  });

  it('returns a handle with updateSelection', () => {
    const handle = renderSankey(svg, MOCK_FILTERED, makeCallbacks(), 'firms', NO_SELECTION);
    expect(handle).not.toBeNull();
    expect(typeof handle!.updateSelection).toBe('function');
  });
});
