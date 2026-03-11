import type { Dimension, Metric, DrillState } from './types';

const DIMENSION_LABELS: Record<Dimension, string> = {
  industry: 'Industry',
  employeeSize: 'Company Size',
  revenueSize: 'Revenue',
};

interface ControlsCallbacks {
  onDimensionChange: (dimension: Dimension) => void;
  onMetricChange: (metric: Metric) => void;
}

export function initControls(callbacks: ControlsCallbacks): void {
  const tabs = document.querySelectorAll<HTMLButtonElement>('#dimension-tabs .tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const dim = tab.dataset.dimension as Dimension;
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      callbacks.onDimensionChange(dim);
    });
  });

  const metricBtns = document.querySelectorAll<HTMLButtonElement>('#metric-toggle .metric-btn');
  metricBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const metric = btn.dataset.metric as Metric;
      metricBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      callbacks.onMetricChange(metric);
    });
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
