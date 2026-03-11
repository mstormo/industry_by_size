import { describe, it, expect } from 'vitest';
import { filterSankeyForDrill, getAvailableDimensions } from '../data';
import type { SankeyData, DrillState } from '../types';

const MOCK_DATA: SankeyData = {
  dimensions: ['industry', 'employeeBucket', 'revenueBucket'],
  nodes: [
    { id: 'industry:Technology', label: 'Technology', dimension: 'industry' },
    { id: 'industry:Healthcare', label: 'Healthcare', dimension: 'industry' },
    { id: 'employeeBucket:100-249', label: '100-249', dimension: 'employeeBucket' },
    { id: 'employeeBucket:5-9', label: '5-9', dimension: 'employeeBucket' },
    { id: 'revenueBucket:$10-50M', label: '$10-50M', dimension: 'revenueBucket' },
    { id: 'revenueBucket:$1-5M', label: '$1-5M', dimension: 'revenueBucket' },
  ],
  links: [
    { source: 'industry:Technology', target: 'employeeBucket:100-249', value: 10 },
    { source: 'industry:Technology', target: 'employeeBucket:5-9', value: 5 },
    { source: 'industry:Healthcare', target: 'employeeBucket:100-249', value: 8 },
    { source: 'employeeBucket:100-249', target: 'revenueBucket:$10-50M', value: 12 },
    { source: 'employeeBucket:5-9', target: 'revenueBucket:$1-5M', value: 3 },
    { source: 'industry:Technology', target: 'revenueBucket:$10-50M', value: 7 },
    { source: 'industry:Technology', target: 'revenueBucket:$1-5M', value: 3 },
  ],
};

describe('filterSankeyForDrill', () => {
  it('returns top-level links between two dimensions', () => {
    const state: DrillState = { path: ['industry', 'employeeBucket'], selections: [] };
    const result = filterSankeyForDrill(MOCK_DATA, state);
    expect(result.links.length).toBe(3);
    expect(result.links.every(l => l.source.startsWith('industry:'))).toBe(true);
    expect(result.links.every(l => l.target.startsWith('employeeBucket:'))).toBe(true);
  });

  it('filters to selected node when drilling down', () => {
    const state: DrillState = {
      path: ['industry', 'revenueBucket'],
      selections: ['Technology'],
    };
    const result = filterSankeyForDrill(MOCK_DATA, state);
    expect(result.links.every(l => l.source === 'industry:Technology')).toBe(true);
    expect(result.links.every(l => l.target.startsWith('revenueBucket:'))).toBe(true);
  });
});

describe('getAvailableDimensions', () => {
  it('returns dimensions not yet in the path', () => {
    const result = getAvailableDimensions(['industry']);
    expect(result).toEqual(['employeeBucket', 'revenueBucket']);
  });

  it('returns one dimension when two are used', () => {
    const result = getAvailableDimensions(['industry', 'employeeBucket']);
    expect(result).toEqual(['revenueBucket']);
  });
});
