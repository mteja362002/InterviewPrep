import React, { createContext, useContext } from 'react';
import useMentorHook from '@/hooks/useMentor';
import { useAuth } from '@/contexts/AuthContext';

/**
 * MentorProvider (RC1.3)
 *
 * Wraps a single `useMentor()` instance and exposes it through context so the
 * top-level AI Mentor drawer AND the full-page /app/ai-mentor screen share the
 * same conversation state. This ensures:
 *   • Opening the drawer on any page keeps the last conversation intact.
 *   • Navigating between pages doesn't reset the chat.
 *   • Expanding drawer → full page transitions seamlessly.
 *
 * RC1.3.3 · User-scoped reset
 *   `useMentor` holds conversation state in local React state (history,
 *   messages, active id) — not in React Query. To honour the cache
 *   isolation contract of AuthContext, we key the inner provider by
 *   the current user id as well as `authNonce`. The user id is part of
 *   the key because `authNonce` is incremented in an AuthContext effect;
 *   on a logout → login transition there can otherwise be one render in
 *   which the intermediate anonymous hook is reused for the new user.
 *   React remounts the underlying hook immediately, dropping every field
 *   that might have belonged to the previous user. No leaks across sessions.
 */
const MentorContext = createContext(null);

export function MentorProvider({ children }) {
  const { user, authNonce } = useAuth();
  const userId = user && typeof user === 'object' ? user.id : 'anonymous';
  // Remounting the inner tree whenever the authenticated identity changes
  // (with authNonce as a secondary cache-reset signal) forces
  // `useMentor` to reinitialise ALL its useState hooks with their
  // default values (history=[], messages=[], activeId=null, …). No
  // bespoke reset logic needed inside the hook itself.
  return (
    <MentorTreeReset key={`${userId}:${authNonce}`}>{children}</MentorTreeReset>
  );
}

function MentorTreeReset({ children }) {
  const mentor = useMentorHook();
  return (
    <MentorContext.Provider value={mentor}>
      {children}
    </MentorContext.Provider>
  );
}

export function useMentorContext() {
  const ctx = useContext(MentorContext);
  // If a consumer is used outside the provider (e.g. during isolated tests),
  // fall back to a local instance to avoid crashes.
  if (!ctx) {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    return useMentorHook();
  }
  return ctx;
}
