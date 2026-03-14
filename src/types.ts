export type Dimension = 'industry' | 'employeeSize' | 'revenueSize';

export type Metric = 'firms' | 'employees';

export interface SankeyNode {
  id: string;
  label: string;
  dimension: Dimension;
}

export interface SankeyLink {
  source: string;
  target: string;
  firms: number;
  employees: number;
}

export interface SankeyData {
  dimensions: Dimension[];
  nodes: SankeyNode[];
  links: SankeyLink[];
  availablePairs: [Dimension, Dimension][];
}

export interface FilteredSankey {
  nodes: SankeyNode[];
  links: SankeyLink[];
  unavailablePair?: boolean;
}

export interface DrillState {
  path: Dimension[];
  selections: string[];
}

export interface RegionInfo {
  id: string;
  label: string;
  group: string | null;
  hasRevenue: boolean;
}

export interface RegionsData {
  regions: RegionInfo[];
  groups: Record<string, string>;
}
