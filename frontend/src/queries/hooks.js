import { useQuery } from '@tanstack/react-query';
import { dashboardService, missionService, roadmapService, revisionService } from '@/services/mission.service';
import { qk } from '@/queries/keys';
import { useAuth } from '@/contexts/AuthContext';

/**
 * Read-only query hooks.
 *
 * Every hook is a thin wrapper over the existing service — the goal
 * is deduplication + shared invalidation, not a new API surface.
 * Callers keep passing the same data around and rendering the same
 * JSX; only the loading mechanism changes.
 *
 * RC1.3.3 · Every user-scoped hook reads `user.id` from `AuthContext`
 * and folds it into the query key. The query is only enabled when a
 * user is present, so we never fire a network request pre-auth and
 * we never mix caches across users. Anonymous (unauthenticated)
 * consumers get an inert query — the same shape they had before.
 */

// ---------- Dashboard --------------------------------------------------

/**
 * The canonical dashboard read. Topbar, MissionControl and (Phase 2)
 * CommandAnalytics all subscribe to this same cache entry, so a
 * single mutation propagates everywhere without any extra network
 * round-trip. Duplicate requests within one staleTime window are
 * naturally deduped by React Query.
 */
export function useDashboard(options = {}) {
  const { user } = useAuth();
  const userId = user?.id;
  return useQuery({
    queryKey: qk.dashboard(userId),
    queryFn: () => dashboardService.get(),
    enabled: !!userId,
    staleTime: 2 * 60 * 1000,
    ...options,
  });
}

// ---------- Roadmap ----------------------------------------------------

export function useRoadmapTree(options = {}) {
  const { user } = useAuth();
  const userId = user?.id;
  return useQuery({
    queryKey: qk.roadmapTree(userId),
    queryFn: () => roadmapService.tree(),
    enabled: !!userId,
    ...options,
  });
}

export function useRoadmapSummary(options = {}) {
  const { user } = useAuth();
  const userId = user?.id;
  return useQuery({
    queryKey: qk.roadmapSummary(userId),
    queryFn: () => roadmapService.summary(),
    enabled: !!userId,
    staleTime: 2 * 60 * 1000,
    ...options,
  });
}

/**
 * Deep node view — the payload behind DeepTopicPage. `enabled: !!nodeId`
 * so the hook can be called unconditionally in a component that
 * receives a nullable route param.
 */
export function useRoadmapNode(nodeId, options = {}) {
  const { user } = useAuth();
  const userId = user?.id;
  return useQuery({
    queryKey: qk.roadmapNode(userId, nodeId),
    queryFn: () => roadmapService.node(nodeId),
    enabled: !!userId && !!nodeId,
    ...options,
  });
}

// ---------- Revisions --------------------------------------------------

/**
 * Canonical revision queue read (RC1.3.4).
 *
 * Backed by `GET /api/revisions/queue?due_only=false` — the same
 * endpoint the Mission Control widget already consumes. Adding a hook
 * gives the new Knowledge Base "Revision Due" view a shared cache
 * entry: opening that view after Mission Control does NOT trigger a
 * second network round-trip, and any mutation that already
 * invalidates `qk.dashboard(userId)` also updates the revision list
 * as of the same tick.
 */
export function useRevisions(options = {}) {
  const { user } = useAuth();
  const userId = user?.id;
  return useQuery({
    queryKey: qk.revisions(userId),
    queryFn: () => revisionService.getQueue(),
    enabled: !!userId,
    ...options,
  });
}
