import React, { act, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { useAIContent } from './useAIContent';
import { roadmapService } from '@/services/mission.service';

jest.mock('@/services/mission.service', () => ({
  roadmapService: { getContent: jest.fn(), generateContent: jest.fn() },
}), { virtual: true });
jest.mock('@/utils/formatApiError', () => ({ formatApiError: () => 'Request failed' }), { virtual: true });
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

test('pending AI generation allows unrelated interaction in the same mounted UI', async () => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  let finishGeneration;
  roadmapService.getContent.mockResolvedValue({ theory: null });
  roadmapService.generateContent.mockReturnValue(new Promise((resolve) => {
    finishGeneration = resolve;
  }));

  function Harness() {
    const { generating, generate, content } = useAIContent('audit-responsive-topic');
    const [section, setSection] = useState('notes');
    return (
      <div>
        <button data-action="generate" disabled={generating} onClick={() => generate()}>
          {generating ? 'Generating' : 'Generate'}
        </button>
        <button data-action="navigate" onClick={() => setSection('prerequisites')}>Prerequisites</button>
        <span data-value="section">{section}</span>
        <span data-value="content">{content?.theory?.beginner || ''}</span>
      </div>
    );
  }

  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  try {
    await act(async () => { root.render(<Harness />); });
    await act(async () => { container.querySelector('[data-action="generate"]').click(); });
    expect(container.querySelector('[data-action="generate"]').disabled).toBe(true);
    await act(async () => { container.querySelector('[data-action="navigate"]').click(); });
    expect(container.querySelector('[data-value="section"]').textContent).toBe('prerequisites');
    expect(container.querySelector('[data-action="generate"]').textContent).toBe('Generating');
    await act(async () => { finishGeneration({ theory: { beginner: 'Content ready' } }); });
    expect(container.querySelector('[data-value="content"]').textContent).toBe('Content ready');
    expect(roadmapService.generateContent).toHaveBeenCalledTimes(1);
  } finally {
    await act(async () => root.unmount());
    container.remove();
    delete global.IS_REACT_ACT_ENVIRONMENT;
  }
});
