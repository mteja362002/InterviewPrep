import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ProgressProvenance } from './ProgressProvenance';

test('baseline and preserved legacy values are explicitly labelled and inspectable', async () => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  const host = document.createElement('div');
  const root = createRoot(host);
  try {
    await act(async () => root.render(<ProgressProvenance details progress={{
      mastery_percentage: 18,
      onboarding_baseline: 70,
      legacy_progress: { mastery_percentage: 52, stored_fields: {
        mastery_percentage: 52, completion_date: '2026-01-01', attempts: 3,
      } },
    }} />));
    expect(host.textContent).toContain('Onboarding Baseline: 70%');
    expect(host.textContent).toContain('Unverified Legacy Progress: 52%');
    expect(host.textContent).toContain('excluded from actual progress');
    expect(host.querySelector('details').textContent).toContain('2026-01-01');
    expect(host.querySelector('pre').textContent).toContain('"attempts": 3');
  } finally {
    await act(async () => root.unmount());
    delete global.IS_REACT_ACT_ENVIRONMENT;
  }
});

test('zero declaration remains visible and independent tracks receive no invented baseline', async () => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  const host = document.createElement('div');
  const root = createRoot(host);
  try {
    await act(async () => root.render(<ProgressProvenance progress={{ onboarding_baseline: 0 }} />));
    expect(host.textContent).toContain('Onboarding Baseline: 0%');
    await act(async () => root.render(<ProgressProvenance progress={{}} />));
    expect(host.textContent).toBe('');
  } finally {
    await act(async () => root.unmount());
    delete global.IS_REACT_ACT_ENVIRONMENT;
  }
});
