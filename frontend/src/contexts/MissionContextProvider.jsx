import React, { createContext, useContext, useMemo, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { missionService } from '@/services/mission.service';
import { qk } from '@/queries/keys';
import { useAuth } from '@/contexts/AuthContext';

const ASSESSMENT_ACTIVITIES = ['quiz', 'behavioral', 'design', 'system_design'];

/**
 * MissionContextProvider (Phase 3D · Mission Experience)
 * ------------------------------------------------------
 * The single source of truth for TODAY's learning experience on the
 * frontend. It fetches the canonical Mission Context projection
 * (`GET /api/missions/today/context`) EXACTLY ONCE and shares it across
 * Mission Control, Coding Arena, Assessment, Knowledge Base, AI Mentor and
 * Analytics.
 *
 * React contains NO learning logic here: it does not infer activity types,
 * pick topics, filter problems or generate explanations. Every value —
 * activity_type, the CTA, difficulty, learning stage, estimated time,
 * companies, learning objectives, representative problem ids and the "why
 * this mission" insight — comes verbatim from the backend.
 */

const MissionContextCtx = createContext(null);

export function MissionContextProvider({ children }) {
  const { user } = useAuth();
  const userId = user?.id;
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: qk.missionContext(userId),
    queryFn: () => missionService.getTodayContext(),
    enabled: !!userId,
    // Today's mission does not change within a session unless a mutation
    // invalidates it, so keep it fresh for the whole session and let the
    // mutation layer trigger refetches when progress changes.
    staleTime: 5 * 60 * 1000,
  });

  // Real-time synchronization (Phase 3D Slice B, §10): any page that completes
  // KB / Arena / Assessment work calls refresh() to invalidate BOTH the shared
  // Mission Context and the dashboard, so Mission Control updates with no
  // manual page refresh and no duplicate fetch elsewhere.
  const refresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: qk.missionContext(userId) });
    queryClient.invalidateQueries({ queryKey: qk.missionToday(userId) });
  }, [queryClient, userId]);

  const value = useMemo(() => {
    const data = query.data || null;
    const tasks = data?.tasks || [];

    const byNode = {};
    const byTask = {};
    for (const t of tasks) {
      if (t.node_id) byNode[t.node_id] = t;
      byTask[t.task_id] = t;
    }

    // ---- MissionExecutionState (§9): shared progress across every page ---- //
    const total = tasks.length;
    const completedCount = tasks.filter((t) => t.completed).length;
    const progressPct = total ? Math.round((completedCount / total) * 100) : 0;
    const overallStatus = total === 0
      ? 'not_started'
      : completedCount === total
        ? 'completed'
        : completedCount > 0
          ? 'in_progress'
          : 'not_started';
    const allDone = (list) => list.length > 0 && list.every((t) => t.completed);
    const studyTasks = tasks.filter((t) => t.activity_type === 'study' || t.activity_type === 'flashcards');
    const codingTasks = tasks.filter((t) => t.activity_type === 'coding');
    const assessmentTasks = tasks.filter((t) => ASSESSMENT_ACTIVITIES.includes(t.activity_type));

    const executionState = {
      status: overallStatus,
      progressPct,
      completedCount,
      totalCount: total,
      kbCompleted: allDone(studyTasks),
      arenaCompleted: allDone(codingTasks),
      assessmentCompleted: allDone(assessmentTasks),
      lastUpdated: query.dataUpdatedAt || null,
    };

    return {
      missionId: data?.mission_id || null,
      date: data?.date || null,
      status: data?.status || null,
      title: data?.title || null,
      focusArea: data?.focus_area || null,
      estimatedDurationMinutes: data?.estimated_duration_minutes ?? null,
      // Backend-owned explainability — rendered as-is, never generated here.
      recommendationInsight: data?.recommendation_insight || null,
      aiNarrative: data?.ai_narrative || null,
      tasks,
      executionState,
      isLoading: query.isLoading,
      isFetching: query.isFetching,
      isError: query.isError,
      error: query.error,
      refetch: query.refetch,
      refresh,
      /** Resolve a task's Mission Context by task id (preferred) or node id. */
      getTaskContext: ({ taskId, nodeId } = {}) => {
        if (taskId && byTask[taskId]) return byTask[taskId];
        if (nodeId && byNode[nodeId]) return byNode[nodeId];
        return null;
      },
      getContextByNodeId: (nodeId) => (nodeId ? byNode[nodeId] || null : null),
      /** True when the given node is part of today's mission. */
      isTodaysNode: (nodeId) => !!(nodeId && byNode[nodeId]),
    };
  }, [query.data, query.dataUpdatedAt, query.isLoading, query.isFetching, query.isError, query.error, query.refetch, refresh]);

  return (
    <MissionContextCtx.Provider value={value}>
      {children}
    </MissionContextCtx.Provider>
  );
}

export function useMissionContext() {
  const ctx = useContext(MissionContextCtx);
  if (ctx === null) {
    throw new Error('useMissionContext must be used within a MissionContextProvider');
  }
  return ctx;
}
