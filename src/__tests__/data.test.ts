import { describe, it, expect } from 'vitest';
import { filterSankeyForDrill, getAvailableDimensions, getMetricValue } from '../data';
import type { SankeyData, SankeyLink, DrillState, Dimension } from '../types';

const MOCK_DATA: SankeyData = {
  dimensions: ['industry', 'employeeSize', 'revenueSize'],
  nodes: [
    { id: 'industry:Manufacturing', label: 'Manufacturing', dimension: 'industry' },
    { id: 'industry:Information', label: 'Information', dimension: 'industry' },
    { id: 'employeeSize:100-249', label: '100-249', dimension: 'employeeSize' },
    { id: 'employeeSize:500+', label: '500+', dimension: 'employeeSize' },
    { id: 'revenueSize:$1-2.5M', label: '$1-2.5M', dimension: 'revenueSize' },
    { id: 'revenueSize:$100M+', label: '$100M+', dimension: 'revenueSize' },
  ],
  links: [
    { source: 'industry:Manufacturing', target: 'employeeSize:100-249', firms: 13573, employees: 943335 },
    { source: 'industry:Manufacturing', target: 'employeeSize:500+', firms: 3200, employees: 2100000 },
    { source: 'industry:Information', target: 'employeeSize:100-249', firms: 8500, employees: 590000 },
    { source: 'industry:Manufacturing', target: 'revenueSize:$1-2.5M', firms: 18000, employees: 250000 },
    { source: 'industry:Information', target: 'revenueSize:$100M+', firms: 500, employees: 800000 },
  ],
  availablePairs: [['industry', 'employeeSize'], ['industry', 'revenueSize']],
};

describe('filterSankeyForDrill', () => {
  it('returns links between industry and employeeSize', () => {
    const state: DrillState = { path: ['industry', 'employeeSize'], selections: [] };
    const result = filterSankeyForDrill(MOCK_DATA, state);
    expect(result.links.length).toBe(3);
    expect(result.links.every(l => l.source.startsWith('industry:'))).toBe(true);
    expect(result.links.every(l => l.target.startsWith('employeeSize:'))).toBe(true);
  });

  it('returns links between industry and revenueSize', () => {
    const state: DrillState = { path: ['industry', 'revenueSize'], selections: [] };
    const result = filterSankeyForDrill(MOCK_DATA, state);
    expect(result.links.length).toBe(2);
  });

  it('reverses links for employeeSize -> industry', () => {
    const state: DrillState = { path: ['employeeSize', 'industry'], selections: [] };
    const result = filterSankeyForDrill(MOCK_DATA, state);
    expect(result.links.length).toBe(3);
    expect(result.links.every(l => l.source.startsWith('employeeSize:'))).toBe(true);
    expect(result.links.every(l => l.target.startsWith('industry:'))).toBe(true);
  });

  it('returns empty with unavailablePair flag for unavailable pair', () => {
    const state: DrillState = { path: ['employeeSize', 'revenueSize'], selections: [] };
    const result = filterSankeyForDrill(MOCK_DATA, state);
    expect(result.nodes.length).toBe(0);
    expect(result.links.length).toBe(0);
    expect(result.unavailablePair).toBe(true);
  });

  it('filters by selection when drilling down', () => {
    const state: DrillState = {
      path: ['industry', 'employeeSize'],
      selections: ['Manufacturing'],
    };
    const result = filterSankeyForDrill(MOCK_DATA, state);
    expect(result.links.every(l => l.source === 'industry:Manufacturing')).toBe(true);
    expect(result.links.length).toBe(2);
  });

  it('filters by selection on reverse pair', () => {
    const state: DrillState = {
      path: ['employeeSize', 'industry'],
      selections: ['100-249'],
    };
    const result = filterSankeyForDrill(MOCK_DATA, state);
    expect(result.links.every(l => l.source === 'employeeSize:100-249')).toBe(true);
    expect(result.links.length).toBe(2);
  });
});

describe('getAvailableDimensions', () => {
  it('returns dimensions that form valid pairs with current path', () => {
    const result = getAvailableDimensions(['industry'], MOCK_DATA.availablePairs);
    expect(result).toContain('employeeSize');
    expect(result).toContain('revenueSize');
  });

  it('returns industry for employeeSize starting dimension', () => {
    const result = getAvailableDimensions(['employeeSize'], MOCK_DATA.availablePairs);
    expect(result).toEqual(['industry']);
  });

  it('does not return revenueSize for employeeSize', () => {
    const result = getAvailableDimensions(['employeeSize'], MOCK_DATA.availablePairs);
    expect(result).not.toContain('revenueSize');
  });

  it('returns empty when all pair-valid dimensions used', () => {
    const result = getAvailableDimensions(['industry', 'employeeSize'], MOCK_DATA.availablePairs);
    expect(result).toEqual([]);
  });
});

describe('getMetricValue', () => {
  it('returns firms for firms metric', () => {
    const link: SankeyLink = { source: 'a', target: 'b', firms: 100, employees: 5000 };
    expect(getMetricValue(link, 'firms')).toBe(100);
  });

  it('returns employees for employees metric', () => {
    const link: SankeyLink = { source: 'a', target: 'b', firms: 100, employees: 5000 };
    expect(getMetricValue(link, 'employees')).toBe(5000);
  });
});
