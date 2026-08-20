/**
 * Central React Query key catalogue.
 *
 * Single source of truth so every hook/component references the same
 * key strings. This is what lets the invalidation matrix work — one
 * page mutates, and every other consumer of the same key
 * automatically refreshes.
 *
 * Convention: use functions (not string constants) so keys can vary by
 * id (e.g. per-node) while still remaining stable references. Never
 * inline a key inline in a component — always call `qk.…()`.
 *
 * RC1.3.3 · User-scoped cache isolation:
 *   Every user-scoped key now carries the authenticated user id as its
 *   FIRST segment. React Query's cache is a Map keyed by the JSON
 *   representation of the key array, so ['user', 'A', 'dashboard'] and
 *   ['user', 'B', 'dashboard'] are two disjoint cache entries. When
 *   User B signs in after User A, they cannot observe User A's stale
 *   payload for even a single render, because they read from a
 *   different key. `AuthContext` additionally calls `queryClient.clear()`
 *   on logout / user-id change as belt-and-braces defense.
 *
 *   `userId` may be `null` — the invariant is that queries only enable
 *   themselves when a user is present, so a null id is effectively a
 *   no-op cache namespace.
 */

const USER = 'user';

export const qk = {
  // Dashboard payload (streak, readiness, mission-of-the-day summary,
  // revision count, knowledge progress, recent activity, week goal).
  // Read by: Topbar, MissionControl, CommandAnalytics.
  dashboard: (userId) => [USER, userId ?? 'anon', 'dashboard'],

  // Today's mission — same underlying network call as `dashboard`
  // (server returns it nested). Kept as a distinct key ONLY when a
  // consumer specifically wants the mission sub-tree; use
  // `useDashboard()` for the general case.
  missionToday: (userId) => [USER, userId ?? 'anon', 'dashboard', 'today'],

  // Phase 3D — canonical Mission Context projection (/missions/today/context).
  // Fetched ONCE and shared by every page through MissionContextProvider.
  missionContext: (userId) => [USER, userId ?? 'anon', 'mission', 'today', 'context'],

  // Weekly-activity roll-up (RC1.3 endpoint).
  weeklyActivity: (userId) => [USER, userId ?? 'anon', 'dashboard', 'weekly-activity'],

  // Full roadmap tree with progress overlay (roadmapService.tree()).
  // Progress overlay is per-user so the key must be user-scoped, even
  // though the roadmap structure itself is global.
  roadmapTree: (userId) => [USER, userId ?? 'anon', 'roadmap', 'tree'],

  // Domain-level summary (roadmapService.summary()) — used by
  // MissionControl right rail.
  roadmapSummary: (userId) => [USER, userId ?? 'anon', 'roadmap', 'summary'],

  // Deep node view (DeepTopicPage). Keyed by node id so multiple
  // nodes can be cached side-by-side (e.g. tab switching).
  roadmapNode: (userId, nodeId) => [USER, userId ?? 'anon', 'roadmap', 'node', nodeId],

  // Revision queue (RC1.3.4) — canonical `/api/revisions/queue?due_only=false`
  // wrapper. Used by Mission Control's revision widget AND by the new
  // Knowledge Base "Revision Due" view. Same server payload, one cache
  // entry, invalidated by every mutation that touches
  // `next_revision` (task toggle, complete_mission, node status change).
  revisions: (userId) => [USER, userId ?? 'anon', 'revisions', 'queue'],
};

/**
 * Helper: given a node id, return every query key that could contain
 * that node's progress. Used by mutations that need to invalidate a
 * node from multiple angles (individual node + the aggregated tree).
 */
export function nodeAffectedKeys(userId, nodeId) {
  return [
    qk.roadmapNode(userId, nodeId),
    qk.roadmapTree(userId),
  ];
}

/**
 * Return the prefix that matches every cache entry for a given user.
 * Used by AuthContext to remove exactly that user's cached data
 * without touching global / anonymous entries.
 */
export function userScopePrefix(userId) {
  return [USER, userId ?? 'anon'];
}
