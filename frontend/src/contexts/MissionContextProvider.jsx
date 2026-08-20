import React, { createContext, useContext, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { missionService } from '@/services/mission.service';
import { qk } from '@/queries/keys';
import { useAuth } from '@/contexts/AuthContext';

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

  const query = useQuery({
    queryKey: qk.missionContext(userId),
    queryFn: () => missionService.getTodayContext(),
    enabled: !!userId,
    // Today's mission does not change within a session unless a mutation
    // invalidates it, so keep it fresh for the whole session and let the
    // mutation layer trigger refetches when progress changes.
    staleTime: 5 * 60 * 1000,
  });

  const value = useMemo(() => {
    const data = query.data || null;
    const tasks = data?.tasks || [];

    const byNode = {};
    const byTask = {};
    for (const t of tasks) {
      if (t.node_id) byNode[t.node_id] = t;
      byTask[t.task_id] = t;
    }

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
      isLoading: query.isLoading,
      isFetching: query.isFetching,
      isError: query.isError,
      error: query.error,
      refetch: query.refetch,
      /** Resolve a task's Mission Context by task id (preferred) or node id. */
      getTaskContext: ({ taskId, nodeId } = {}) => {
        if (taskId && byTask[taskId]) return byTask[taskId];
        if (nodeId && byNode[nodeId]) return byNode[nodeId];
        return null;
      },
      getContextByNodeId: (nodeId) => (nodeId ? byNode[nodeId] || null : null),
    };
  }, [query.data, query.isLoading, query.isFetching, query.isError, query.error, query.refetch]);

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
