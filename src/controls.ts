import type { Dimension, Metric, DrillState, RegionsData } from './types';

const DIMENSION_LABELS: Record<Dimension, string> = {
  industry: 'Industry',
  employeeSize: 'Company Size',
  revenueSize: 'Revenue',
};

interface ControlsCallbacks {
  onDimensionChange: (dimension: Dimension) => void;
  onMetricChange: (metric: Metric) => void;
  onRegionChange: (regionId: string) => void;
}

export function initControls(regionsData: RegionsData, callbacks: ControlsCallbacks): void {
  // Dimension tabs
  const tabs = document.querySelectorAll<HTMLButtonElement>('#dimension-tabs .tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      if (tab.classList.contains('disabled')) return;
      const dim = tab.dataset.dimension as Dimension;
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      callbacks.onDimensionChange(dim);
    });
  });

  // Metric toggle
  const metricBtns = document.querySelectorAll<HTMLButtonElement>('#metric-toggle .metric-btn');
  metricBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const metric = btn.dataset.metric as Metric;
      metricBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      callbacks.onMetricChange(metric);
    });
  });

  // Region selector
  const regionSelect = document.getElementById('region-select') as HTMLSelectElement | null;
  if (regionSelect) {
    populateRegionSelect(regionSelect, regionsData);
    regionSelect.addEventListener('change', () => {
      callbacks.onRegionChange(regionSelect.value);
    });
  }
}

function populateRegionSelect(select: HTMLSelectElement, data: RegionsData): void {
  const topLevel = data.regions.filter(r => r.group === null);
  for (const region of topLevel) {
    const groupId = region.id;
    const children = data.regions.filter(r => r.group === groupId);

    if (children.length > 0) {
      // Optgroup with the aggregate as its first selectable entry
      const group = document.createElement('optgroup');
      group.label = data.groups[groupId] || region.label;

      const aggregateOpt = document.createElement('option');
      aggregateOpt.value = region.id;
      aggregateOpt.textContent = `${region.label} (all)`;
      group.appendChild(aggregateOpt);

      for (const child of children) {
        const childOpt = document.createElement('option');
        childOpt.value = child.id;
        childOpt.textContent = child.label;
        group.appendChild(childOpt);
      }
      select.appendChild(group);
    } else {
      const opt = document.createElement('option');
      opt.value = region.id;
      opt.textContent = region.label;
      select.appendChild(opt);
    }
  }
}

export function setRevenueTabEnabled(enabled: boolean): void {
  const revenueTab = document.querySelector<HTMLButtonElement>('#dimension-tabs .tab[data-dimension="revenueSize"]');
  if (!revenueTab) return;

  if (enabled) {
    revenueTab.classList.remove('disabled');
    revenueTab.removeAttribute('title');
  } else {
    revenueTab.classList.add('disabled');
    revenueTab.title = 'Revenue breakdown only available for United States';
  }
}

export function setActiveTab(dimension: Dimension): void {
  const tabs = document.querySelectorAll<HTMLButtonElement>('#dimension-tabs .tab');
  tabs.forEach(t => {
    if (t.dataset.dimension === dimension) {
      t.classList.add('active');
    } else {
      t.classList.remove('active');
    }
  });
}

export function updateBreadcrumb(state: DrillState, onClick: (level: number) => void): void {
  const container = document.getElementById('breadcrumb');
  if (!container) return;

  while (container.firstChild) {
    container.removeChild(container.firstChild);
  }

  if (state.selections.length === 0) return;

  for (let i = 0; i < state.path.length; i++) {
    if (i > 0) {
      const sep = document.createElement('span');
      sep.className = 'separator';
      sep.textContent = '>';
      container.appendChild(sep);
    }

    const dimLabel = DIMENSION_LABELS[state.path[i]];

    if (i < state.selections.length) {
      const crumb = document.createElement('span');
      crumb.className = 'crumb';
      crumb.textContent = `${dimLabel}: ${state.selections[i]}`;
      const level = i;
      crumb.addEventListener('click', () => onClick(level));
      container.appendChild(crumb);
    } else {
      const current = document.createElement('span');
      current.textContent = dimLabel;
      container.appendChild(current);
    }
  }
}
