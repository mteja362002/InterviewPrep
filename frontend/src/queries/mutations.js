import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { missionService, roadmapService } from '@/services/mission.service';
import { qk, nodeAffectedKeys } from '@/queries/keys';
import { formatApiError } from '@/utils/formatApiError';
import { useAuth } from '@/contexts/AuthContext';

/**
 * Write hooks (mutations).
 *
 * Each mutation follows the same three-phase contract:
 *
 *   1. **onMutate** — snapshot the affected caches, then patch them
 *      optimistically. UI updates instantly.
 *   2. **onError**  — restore the snapshot so the UI reverts on failure.
 *      A toast is emitted with the server's error message.
 *   3. **onSettled / onSuccess** — invalidate the affected keys so the
 *      canonical server state overwrites the optimistic patch.
 *
 * The invalidation matrix (see docstrings below) is the ONE place we
 * declare what a mutation affects. Adding a new consumer of dashboard
 * data anywhere in the app requires zero changes here.
 *
 * RC1.3.3 · Every mutation now scopes its cache reads/writes to the
 * authenticated user's id. This is mandatory — otherwise the
 * optimistic patch produced by an in-flight mutation on User A's
 * session could leak into User B's cache if a logout raced with the
 * mutation's onSettled. Cross-user isolation is enforced at the key
 * layer; the mutation body only needs to pass `userId` through.
 */

// -----------------------------------------------------------------------
// Internal helpers
// -----------------------------------------------------------------------

/**
 * Snapshot every key in `keys` and return a rollback function.
 * Used by every optimistic path — one line to snapshot, one line to
 * revert. Keeps the mutation bodies short and consistent.
 */
function snapshotKeys(qc, keys) {
  const snapshots = keys.map((k) => [k, qc.getQueryData(k)]);
  return () => snapshots.forEach(([k, v]) => qc.setQueryData(k, v));
}

// Patch a task inside the nested dashboard.mission.tasks array without
// mutating the original — required by React Query's structural sharing
// so consumers that only care about `dashboard.streak` don't rerender.
function patchDashboardMission(qc, userId, patcher) {
  qc.setQueryData(qk.dashboard(userId), (prev) => {
    if (!prev || !prev.mission) return prev;
    const next = patcher(prev.mission);
    if (!next || next === prev.mission) return prev;
    return { ...prev, mission: next };
  });
}

// -----------------------------------------------------------------------
// Mission mutations
// -----------------------------------------------------------------------

/**
 * Toggle a single task within today's mission.
 *
 * Optimistic:  flip the task's `completed` flag + `completed_at`.
 * Invalidates: dashboard (streak may change if this was the last task),
 *              the affected node's cache entry (task completion writes
 *              through to knowledge_nodes), and the roadmap tree
 *              (progress overlay used by KnowledgeBase).
 */
export function useToggleTask(missionId) {
  const qc = useQueryClient();
  const { user } = useAuth();
  const userId = user?.id;

  return useMutation({
    mutationFn: (taskId) => missionService.toggleTask(missionId, taskId),
    onMutate: async (taskId) => {
      await qc.cancelQueries({ queryKey: qk.dashboard(userId) });
      const rollback = snapshotKeys(qc, [qk.dashboard(userId)]);
      patchDashboardMission(qc, userId, (mission) => {
        if (mission.status === 'completed' || mission.status === 'skipped') {
          return mission; // backend will reject; no optimistic flip
        }
        const nextTasks = mission.tasks.map((t) => {
          if (t.id !== taskId) return t;
          const nextCompleted = !t.completed;
          return {
            ...t,
            completed: nextCompleted,
            completed_at: nextCompleted ? new Date().toISOString() : null,
          };
        });
        return { ...mission, tasks: nextTasks };
      });
      return { rollback };
    },
    onError: (err, _taskId, ctx) => {
      ctx?.rollback?.();
      toast.error(formatApiError(err));
    },
    onSuccess: (serverMission) => {
      // Server is the source of truth for post-toggle state (revision
      // schedule may have moved, etc.). Replace the mission subtree in
      // place — everything else in the dashboard payload stays cached.
      patchDashboardMission(qc, userId, () => serverMission);
    },
    onSettled: (_data, _err, taskId) => {
      qc.invalidateQueries({ queryKey: qk.dashboard(userId) });
      qc.invalidateQueries({ queryKey: qk.roadmapTree(userId) });
      qc.invalidateQueries({ queryKey: qk.revisions(userId) });
      // The task's underlying node may have been updated (mastery,
      // status, next_revision). If a DeepTopicPage is open for it,
      // this will silently refetch and swap in fresh data.
      const dash = qc.getQueryData(qk.dashboard(userId));
      const task = dash?.mission?.tasks?.find((t) => t.id === taskId);
      if (task?.node_id) {
        qc.invalidateQueries({ queryKey: qk.roadmapNode(userId, task.node_id) });
      }
    },
  });
}

/**
 * Mark today's mission complete.
 *
 * Optimistic:  set mission.status='completed'. Streak is NOT bumped
 *              optimistically because the server enforces the "one
 *              bump per day" rule and we don't want to double-count.
 *              We let the onSettled invalidation refresh streak
 *              accurately.
 * Invalidates: dashboard.
 */
export function useCompleteMission(missionId) {
  const qc = useQueryClient();
  const { user } = useAuth();
  const userId = user?.id;

  return useMutation({
    mutationFn: () => missionService.completeMission(missionId),
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: qk.dashboard(userId) });
      const rollback = snapshotKeys(qc, [qk.dashboard(userId)]);
      patchDashboardMission(qc, userId, (mission) => {
        if (mission.status === 'completed') return mission;
        return {
          ...mission,
          status: 'completed',
          completed_at: new Date().toISOString(),
          tasks: mission.tasks.map((t) => ({
            ...t,
            completed: true,
            completed_at: t.completed_at || new Date().toISOString(),
          })),
        };
      });
      return { rollback };
    },
    onError: (err, _v, ctx) => {
      ctx?.rollback?.();
      toast.error(formatApiError(err));
    },
    onSuccess: (serverMission) => {
      patchDashboardMission(qc, userId, () => serverMission);
    },
    onSettled: () => {
      // Streak / activity counters / weekly-activity all move — refresh
      // the whole dashboard payload and the weekly-activity view.
      qc.invalidateQueries({ queryKey: qk.dashboard(userId) });
      qc.invalidateQueries({ queryKey: qk.weeklyActivity(userId) });
    },
  });
}

/**
 * Skip today's mission. Terminal state — the server will reject any
 * subsequent completion attempt.
 *
 * Optimistic:  set mission.status='skipped'.
 * Invalidates: dashboard.
 */
export function useSkipMission(missionId) {
  const qc = useQueryClient();
  const { user } = useAuth();
  const userId = user?.id;

  return useMutation({
    mutationFn: () => missionService.skipMission(missionId),
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: qk.dashboard(userId) });
      const rollback = snapshotKeys(qc, [qk.dashboard(userId)]);
      patchDashboardMission(qc, userId, (mission) => ({
        ...mission,
        status: 'skipped',
      }));
      return { rollback };
    },
    onError: (err, _v, ctx) => {
      ctx?.rollback?.();
      toast.error(formatApiError(err));
    },
    onSuccess: (serverMission) => {
      patchDashboardMission(qc, userId, () => serverMission);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: qk.dashboard(userId) });
    },
  });
}

// -----------------------------------------------------------------------
// Roadmap node mutations
// -----------------------------------------------------------------------

/**
 * Shared patcher for the deep-node view. Merges `patch.progress` into
 * whatever cache already holds `qk.roadmapNode(userId, nodeId)`.
 */
function patchNodeProgress(qc, userId, nodeId, progressPatch) {
  qc.setQueryData(qk.roadmapNode(userId, nodeId), (prev) => {
    if (!prev || !prev.node) return prev;
    return {
      ...prev,
      node: {
        ...prev.node,
        progress: { ...(prev.node.progress || {}), ...progressPatch },
      },
    };
  });
}

/**
 * Mark a knowledge node as {not_started | in_progress | completed | mastered}.
 *
 * Optimistic:  node.progress.status flips instantly.
 * Invalidates: dashboard (readiness, revision counters move) +
 *              roadmap tree (progress overlay).
 */
export function useSetNodeStatus() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const userId = user?.id;

  return useMutation({
    mutationFn: ({ nodeId, status }) => roadmapService.setStatus(nodeId, status),
    onMutate: async ({ nodeId, status }) => {
      await qc.cancelQueries({ queryKey: qk.roadmapNode(userId, nodeId) });
      const rollback = snapshotKeys(qc, [qk.roadmapNode(userId, nodeId)]);
      patchNodeProgress(qc, userId, nodeId, { status });
      return { rollback };
    },
    onError: (err, _v, ctx) => {
      ctx?.rollback?.();
      toast.error(formatApiError(err));
    },
    onSettled: (_data, _err, { nodeId }) => {
      // Server response contains the canonical progress — refresh the
      // deep view + everything that renders progress overlays.
      nodeAffectedKeys(userId, nodeId).forEach((k) => qc.invalidateQueries({ queryKey: k }));
      qc.invalidateQueries({ queryKey: qk.dashboard(userId) });
      qc.invalidateQueries({ queryKey: qk.revisions(userId) });
    },
  });
}

/**
 * Save confidence (0-10) for a knowledge node.
 *
 * Optimistic:  node.progress.confidence updates instantly.
 * Invalidates: actual mastery/completion rollups and readiness consumers.
 */
export function useSetNodeConfidence() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const userId = user?.id;

  return useMutation({
    mutationFn: ({ nodeId, value }) => roadmapService.setConfidence(nodeId, value),
    onMutate: async ({ nodeId, value }) => {
      await qc.cancelQueries({ queryKey: qk.roadmapNode(userId, nodeId) });
      const rollback = snapshotKeys(qc, [qk.roadmapNode(userId, nodeId)]);
      patchNodeProgress(qc, userId, nodeId, { confidence: value });
      return { rollback };
    },
    onError: (err, _v, ctx) => {
      ctx?.rollback?.();
      toast.error(formatApiError(err));
    },
    onSettled: (_data, _err, { nodeId }) => {
      nodeAffectedKeys(userId, nodeId).forEach((k) => qc.invalidateQueries({ queryKey: k }));
      qc.invalidateQueries({ queryKey: qk.dashboard(userId) });
      qc.invalidateQueries({ queryKey: qk.revisions(userId) });
    },
  });
}

/**
 * Record a study/practice attempt for a knowledge node.
 *
 * Optimistic:  bump the node's activity counter.
 * Invalidates: node cache + weekly-activity (the recorded attempt
 *              becomes a `practice_more` activity event).
 */
export function useRecordAttempt() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const userId = user?.id;

  return useMutation({
    mutationFn: ({ nodeId, minutes }) => roadmapService.recordAttempt(nodeId, minutes),
    onMutate: async ({ nodeId, minutes }) => {
      await qc.cancelQueries({ queryKey: qk.roadmapNode(userId, nodeId) });
      const rollback = snapshotKeys(qc, [qk.roadmapNode(userId, nodeId)]);
      qc.setQueryData(qk.roadmapNode(userId, nodeId), (prev) => {
        if (!prev) return prev;
        const activity = Array.isArray(prev.activity) ? prev.activity : [];
        return {
          ...prev,
          activity: [
            {
              id: `optimistic-${Date.now()}`,
              kind: 'practice_more',
              detail: minutes ? `${minutes} min` : 'attempt recorded',
              ts: new Date().toISOString(),
              optimistic: true,
            },
            ...activity,
          ],
        };
      });
      return { rollback };
    },
    onError: (err, _v, ctx) => {
      ctx?.rollback?.();
      toast.error(formatApiError(err));
    },
    onSettled: (_data, _err, { nodeId }) => {
      qc.invalidateQueries({ queryKey: qk.roadmapNode(userId, nodeId) });
      qc.invalidateQueries({ queryKey: qk.weeklyActivity(userId) });
    },
  });
}

/**
 * Save notes for a knowledge node.
 *
 * Optimistic:  node.notes updates instantly (no debounce here — that
 *              still lives in the DeepTopicPage effect).
 * Invalidates: only the deep-node view.
 */
export function useSaveNodeNotes() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const userId = user?.id;

  return useMutation({
    mutationFn: ({ nodeId, notes }) => roadmapService.saveNotes(nodeId, notes),
    onMutate: async ({ nodeId, notes }) => {
      await qc.cancelQueries({ queryKey: qk.roadmapNode(userId, nodeId) });
      const rollback = snapshotKeys(qc, [qk.roadmapNode(userId, nodeId)]);
      qc.setQueryData(qk.roadmapNode(userId, nodeId), (prev) => {
        if (!prev || !prev.node) return prev;
        return {
          ...prev,
          node: { ...prev.node, notes },
        };
      });
      return { rollback };
    },
    onError: (err, _v, ctx) => {
      ctx?.rollback?.();
      toast.error(formatApiError(err));
    },
    onSettled: (_data, _err, { nodeId }) => {
      qc.invalidateQueries({ queryKey: qk.roadmapNode(userId, nodeId) });
    },
  });
}

/**
 * Toggle bookmark for a node (NodeActions).
 *
 * Optimistic:  progress.bookmarked flips instantly on both the deep-
 *              node view AND on the matching leaf in the roadmap tree.
 * Invalidates: none — bookmarks don't affect any other view; the
 *              optimistic patch IS the final state (with a rollback
 *              on server failure).
 */
export function useToggleBookmark() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const userId = user?.id;

  return useMutation({
    mutationFn: (nodeId) => roadmapService.toggleBookmark(nodeId),
    onMutate: async (nodeId) => {
      await qc.cancelQueries({ queryKey: qk.roadmapNode(userId, nodeId) });
      const rollback = snapshotKeys(qc, [qk.roadmapNode(userId, nodeId), qk.roadmapTree(userId)]);
      const current = qc.getQueryData(qk.roadmapNode(userId, nodeId))?.node?.progress?.bookmarked;
      patchNodeProgress(qc, userId, nodeId, { bookmarked: !current });
      patchTreeNode(qc, userId, nodeId, (prog) => ({ ...prog, bookmarked: !prog.bookmarked }));
      return { rollback };
    },
    onError: (err, _v, ctx) => {
      ctx?.rollback?.();
      toast.error(formatApiError(err));
    },
    onSuccess: (res, nodeId) => {
      // Server returns { bookmarked } — snap to the authoritative value.
      patchNodeProgress(qc, userId, nodeId, { bookmarked: !!res?.bookmarked });
      patchTreeNode(qc, userId, nodeId, (prog) => ({ ...prog, bookmarked: !!res?.bookmarked }));
    },
  });
}

export function useToggleFavorite() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const userId = user?.id;

  return useMutation({
    mutationFn: (nodeId) => roadmapService.toggleFavorite(nodeId),
    onMutate: async (nodeId) => {
      await qc.cancelQueries({ queryKey: qk.roadmapNode(userId, nodeId) });
      const rollback = snapshotKeys(qc, [qk.roadmapNode(userId, nodeId), qk.roadmapTree(userId)]);
      const current = qc.getQueryData(qk.roadmapNode(userId, nodeId))?.node?.progress?.favorite;
      patchNodeProgress(qc, userId, nodeId, { favorite: !current });
      patchTreeNode(qc, userId, nodeId, (prog) => ({ ...prog, favorite: !prog.favorite }));
      return { rollback };
    },
    onError: (err, _v, ctx) => {
      ctx?.rollback?.();
      toast.error(formatApiError(err));
    },
    onSuccess: (res, nodeId) => {
      patchNodeProgress(qc, userId, nodeId, { favorite: !!res?.favorite });
      patchTreeNode(qc, userId, nodeId, (prog) => ({ ...prog, favorite: !!res?.favorite }));
    },
  });
}

// -----------------------------------------------------------------------
// Tree traversal helper
// -----------------------------------------------------------------------

/**
 * Walk the cached roadmap tree, find the leaf whose id matches
 * `nodeId`, and merge `updater(progress)` into it. Deep-copies just
 * enough of the tree spine to keep React Query's structural sharing
 * happy — sibling branches remain reference-equal so unrelated
 * subtrees don't re-render.
 */
function patchTreeNode(qc, userId, nodeId, updater) {
  qc.setQueryData(qk.roadmapTree(userId), (prev) => {
    if (!prev || !Array.isArray(prev.tracks)) return prev;
    let changed = false;

    const walk = (list, path) => list.map((n) => {
      if (n.id === nodeId) {
        changed = true;
        const nextProgress = updater(n.progress || {});
        return { ...n, progress: nextProgress };
      }
      let nextChildren = null;
      for (const key of ['modules', 'topics', 'learning_nodes']) {
        if (Array.isArray(n[key])) {
          const w = walk(n[key], [...path, key]);
          if (w !== n[key]) nextChildren = { ...(nextChildren || {}), [key]: w };
        }
      }
      return nextChildren ? { ...n, ...nextChildren } : n;
    });

    const nextTracks = walk(prev.tracks, ['tracks']);
    return changed ? { ...prev, tracks: nextTracks } : prev;
  });
}
