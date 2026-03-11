export interface Company {
  id: string;
  name: string;
  industry: string;
  employeeCount: number | null;
  employeeBucket: string | null;
  revenue: number | null;
  revenueBucket: string | null;
  country: string;
  source: string;
}

export interface SankeyNode {
  id: string;
  label: string;
  dimension: Dimension;
}

export interface SankeyLink {
  source: string;
  target: string;
  value: number;
}

export interface SankeyData {
  dimensions: string[];
  nodes: SankeyNode[];
  links: SankeyLink[];
}

export type Dimension = 'industry' | 'employeeBucket' | 'revenueBucket';

export interface FilteredSankey {
  nodes: SankeyNode[];
  links: SankeyLink[];
}

export interface DrillState {
  /** The ordered sequence of dimensions as the user drills down */
  path: Dimension[];
  /** The selected values at each level (e.g., ["Technology", "100-249"]) */
  selections: string[];
}
