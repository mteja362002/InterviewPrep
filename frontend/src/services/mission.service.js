import api from './api';

export const missionService = {
  getToday: () => api.get('/missions/today').then((r) => r.data),
  toggleTask: (missionId, taskId) =>
    api.post(`/missions/${missionId}/tasks/${taskId}/toggle`).then((r) => r.data),
  completeMission: (missionId) =>
    api.post(`/missions/${missionId}/complete`).then((r) => r.data),
  skipMission: (missionId) =>
    api.post(`/missions/${missionId}/skip`).then((r) => r.data),
  getHistory: (limit = 20) =>
    api.get('/missions/history', { params: { limit } }).then((r) => r.data),
};

export const dashboardService = {
  get: () => api.get('/dashboard').then((r) => r.data),
  weeklyActivity: () => api.get('/dashboard/weekly-activity').then((r) => r.data),
};

export const revisionService = {
  getQueue: () => api.get('/revisions/queue').then((r) => r.data),
};

export const activityService = {
  list: (limit = 20) => api.get('/activity', { params: { limit } }).then((r) => r.data),
};

export const onboardingService = {
  patch: (payload) => api.patch('/onboarding', payload).then((r) => r.data),
};

export const codingArenaService = {
  get: () => api.get('/coding-arena').then((r) => r.data),
  practiceMore: (pattern) =>
    api.post('/coding-arena/practice-more', { pattern }).then((r) => r.data),
  submitFeedback: (assignmentId, payload) =>
    api.post(`/coding-arena/assignments/${assignmentId}/feedback`, payload).then((r) => r.data),
  getPatterns: () => api.get('/problems/patterns').then((r) => r.data),
  // Bridges a manually-searched LeetCode Catalog problem into the existing
  // ProblemAssignment/feedback/Learning-Engine pipeline (unified learning flow).
  startManualPractice: (leetcodeId) =>
    api.post('/coding-arena/manual-assignment', { leetcode_id: leetcodeId }).then((r) => r.data),
};

// Manual search/discovery only — backed by the standalone LeetCode Catalog,
// never the Mission Engine's problem_bank.
export const leetcodeCatalogService = {
  getById: (leetcodeId) => api.get(`/leetcode/problems/${leetcodeId}`).then((r) => r.data),
  getByTitle: (title) => api.get(`/leetcode/problems/title/${encodeURIComponent(title)}`).then((r) => r.data),
  search: (query, limit = 20) =>
    api.get('/leetcode/problems/search', { params: { q: query, limit } }).then((r) => r.data),
};

export const knowledgeService = {
  tree: () => api.get('/knowledge/tree').then((r) => r.data),
};

// Phase 3C — Mission → Assessment workflow. Reuses the Assessment Engine
// (Phase 3A) and the Assessment → Learner Intelligence flow (Phase 3B).
export const assessmentService = {
  generateForMission: (missionId) =>
    api.post(`/missions/${missionId}/assessment/generate`).then((r) => r.data),
  getForMission: (missionId) =>
    api.get(`/missions/${missionId}/assessment`).then((r) => r.data),
  start: (id) => api.post(`/assessments/${id}/start`).then((r) => r.data),
  submit: (id, payload) => api.post(`/assessments/${id}/submit`, payload).then((r) => r.data),
  evaluate: (id) => api.post(`/assessments/${id}/evaluate`).then((r) => r.data),
  get: (id) => api.get(`/assessments/${id}`).then((r) => r.data),
};

export const learnerIntelligenceService = {
  updates: (limit = 5) =>
    api.get('/learner-intelligence/updates', { params: { limit } }).then((r) => r.data),
};

export const readinessService = {
  companies: () => api.get('/readiness/companies').then((r) => r.data),
};

export const roadmapService = {
  tree: () => api.get('/roadmap').then((r) => r.data),
  node: (nodeId) => api.get(`/roadmap/nodes/${nodeId}`).then((r) => r.data),
  progress: () => api.get('/roadmap/progress').then((r) => r.data),
  summary: () => api.get('/roadmap/summary').then((r) => r.data),
  saveNotes: (nodeId, notes) => api.patch(`/roadmap/nodes/${nodeId}/notes`, { notes }).then((r) => r.data),
  setConfidence: (nodeId, confidence) =>
    api.post(`/roadmap/nodes/${nodeId}/confidence`, { confidence }).then((r) => r.data),
  setStatus: (nodeId, status) =>
    api.post(`/roadmap/nodes/${nodeId}/status`, { status }).then((r) => r.data),
  toggleBookmark: (nodeId) => api.post(`/roadmap/nodes/${nodeId}/bookmark`).then((r) => r.data),
  toggleFavorite: (nodeId) => api.post(`/roadmap/nodes/${nodeId}/favorite`).then((r) => r.data),
  recordAttempt: (nodeId, actualMinutes) =>
    api.post(`/roadmap/nodes/${nodeId}/attempt`, actualMinutes ? { actual_minutes: actualMinutes } : {}).then((r) => r.data),
  version: () => api.get('/roadmap/version').then((r) => r.data),
  // AI-generated knowledge content.
  getContent: (nodeId) => api.get(`/roadmap/nodes/${nodeId}/content`).then((r) => r.data),
  generateContent: (nodeId) => api.post(`/roadmap/nodes/${nodeId}/content/generate`).then((r) => r.data),
  regenerateContent: (nodeId) => api.post(`/roadmap/nodes/${nodeId}/content/regenerate`).then((r) => r.data),
};
