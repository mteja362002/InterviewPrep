import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import {
  Target, ShieldCheck, RefreshCcw, GraduationCap,
  Sparkles, Check, SkipForward, Loader2,
  CheckCircle2, Circle, Clock, Zap, TrendingUp, ChevronDown, Route, Calendar, ClipboardCheck,
} from 'lucide-react';
import { format, formatDistanceToNow, parseISO } from 'date-fns';
import { GlassCard } from '@/components/common/GlassCard';
import { DASHBOARD } from '@/constants/testIds';
import { useAuth } from '@/contexts/AuthContext';
import { useDashboard, useRoadmapSummary } from '@/queries/hooks';
import { useToggleTask, useCompleteMission, useSkipMission } from '@/queries/mutations';
import { TARGET_COMPANIES } from '@/config/companies';
import { formatApiError } from '@/utils/formatApiError';
import { cn } from '@/lib/utils';
import { useMentorContext } from '@/contexts/MentorContext';
import { useMissionContext } from '@/contexts/MissionContextProvider';
import { useAIPanel } from '@/contexts/AIPanelContext';
import { ProgressBar } from '@/components/progress/ProgressBar';
import { WhyThisMissionDialog } from '@/components/mission/WhyThisMissionDialog';

/**
 * Phase 3D — the primary action button for every task comes ENTIRELY from
 * Mission Context (`taskCtx.cta`). React never infers the activity type or
 * decides which page to open. Exactly ONE primary CTA renders per task
 * (constraint #12: never both Open KB and Open Arena), plus an auxiliary
 * "Ask Mentor" affordance.
 */
function TaskActions({
  task, taskCtx, onOpenKB, onOpenArena, onStartAssessment, onFlashcards,
  onOpenMentor, busyAction,
}) {
  const cta = taskCtx?.cta || null;
  const activity = taskCtx?.activity_type || null;
  const repIds = taskCtx?.mission_context?.representative_problem_ids;
  const arenaEmpty = activity === 'coding' && Array.isArray(repIds) && repIds.length === 0;

  const baseBtn = 'h-10 inline-flex items-center gap-2 px-3 rounded-lg border text-xs font-medium transition-colors';
  const primaryCls = 'border-primary/30 bg-primary/10 hover:bg-primary/15 text-primary';
  const neutralCls = 'border-white/[0.08] bg-white/[0.02] hover:bg-white/[0.05] text-foreground';

  let primary = null;
  if (cta?.action === 'open_knowledge_base') {
    primary = (
      <button type="button" onClick={() => onOpenKB(task.node_id)}
        className={cn(baseBtn, neutralCls)}
        data-testid={`mission-task-cta-${task.id}`} data-cta="open_knowledge_base">
        {cta.label}
      </button>
    );
  } else if (cta?.action === 'open_coding_arena') {
    primary = arenaEmpty ? (
      <button type="button" disabled
        title="No representative problems available for this learning node."
        className={cn(baseBtn, 'border-white/[0.08] bg-white/[0.02] text-muted-foreground cursor-not-allowed opacity-70')}
        data-testid={`mission-task-cta-${task.id}`} data-cta="open_coding_arena">
        No problems available
      </button>
    ) : (
      <button type="button" onClick={() => onOpenArena(task)}
        className={cn(baseBtn, primaryCls)}
        data-testid={`mission-task-cta-${task.id}`} data-cta="open_coding_arena">
        {cta.label}
      </button>
    );
  } else if (cta?.action === 'start_assessment') {
    primary = (
      <button type="button" onClick={() => onStartAssessment(task)}
        className={cn(baseBtn, primaryCls)}
        data-testid={`mission-task-cta-${task.id}`} data-cta="start_assessment">
        {cta.label}
      </button>
    );
  } else if (cta?.action === 'open_flashcards') {
    primary = (
      <button type="button" onClick={() => onFlashcards(task)}
        className={cn(baseBtn, primaryCls)}
        data-testid={`mission-task-cta-${task.id}`} data-cta="open_flashcards">
        {cta.label}
      </button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      {primary}
      {task.node_id && (
        <button
          type="button"
          onClick={() => onOpenMentor(task)}
          disabled={busyAction === `mentor-${task.node_id}`}
          className="h-10 inline-flex items-center justify-center w-10 rounded-lg border border-primary/30 bg-primary/10 hover:bg-primary/15 text-primary transition-colors disabled:opacity-50"
          data-testid={`mission-task-mentor-${task.id}`}
          aria-label="Ask Mentor"
          title="Ask Mentor"
        >
          <Sparkles className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

const ACTIVITY_META = {
  mission_completed:  { dot: 'bg-emerald-400',  label: 'Mission completed' },
  mission_skipped:    { dot: 'bg-amber-400',    label: 'Mission skipped' },
  task_completed:     { dot: 'bg-primary',      label: 'Task completed' },
  task_uncompleted:   { dot: 'bg-white/40',     label: 'Task uncompleted' },
  problem_feedback:   { dot: 'bg-secondary',    label: 'Problem feedback' },
  practice_more:      { dot: 'bg-secondary',    label: 'Practice more' },
  profile_updated:    { dot: 'bg-secondary',    label: 'Profile updated' },
  settings_changed:   { dot: 'bg-secondary',    label: 'Settings changed' },
  daily_login:        { dot: 'bg-white/40',     label: 'Signed in' },
  mission_generated:  { dot: 'bg-primary',      label: 'Mission generated' },
};

function WidgetHeader({ icon: Icon, title, action }) {
  return (
    <div className="flex items-start justify-between mb-4">
      <div className="flex items-center gap-2.5">
        <span className="h-8 w-8 rounded-lg border border-white/10 bg-white/[0.03] flex items-center justify-center">
          <Icon className="h-4 w-4 text-primary" />
        </span>
        <h3 className="font-display text-base font-medium">{title}</h3>
      </div>
      {action}
    </div>
  );
}

function difficultyChipClass(d) {
  if (d === 'easy')   return 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300';
  if (d === 'hard')   return 'border-rose-400/30 bg-rose-400/10 text-rose-300';
  return 'border-amber-400/30 bg-amber-400/10 text-amber-300';
}

function taskKindIcon(kind) {
  if (kind === 'practice') return <Zap className="h-3.5 w-3.5" />;
  if (kind === 'revise')   return <RefreshCcw className="h-3.5 w-3.5" />;
  return <GraduationCap className="h-3.5 w-3.5" />;
}

export default function MissionControl() {
  const { user } = useAuth();
  // RC1.3.2B · dashboard + roadmap-summary are now React Query
  // subscriptions. Every dashboard consumer (Topbar, this page,
  // Analytics in Phase 2) shares the same cache entry, so a mission
  // toggle immediately propagates without a manual reload.
  const { data, isLoading: dashboardLoading } = useDashboard();
  const { data: summary } = useRoadmapSummary();
  const loading = dashboardLoading && !data;

  // Mutation hooks — optimistic, with rollback + invalidation baked in.
  const missionId = data?.mission?.id;
  const toggleTask = useToggleTask(missionId);
  const completeMissionM = useCompleteMission(missionId);
  const skipMissionM = useSkipMission(missionId);

  const [busyAction, setBusyAction] = useState(null);
  const [expandedDomain, setExpandedDomain] = useState(null);
  const navigate = useNavigate();
  const mentor = useMentorContext();
  const aiPanel = useAIPanel();
  // Phase 3D — the shared, fetch-once Mission Context. CTAs derive from here.
  const { getTaskContext, refresh: refreshMission } = useMissionContext();

  // Which task, if any, is currently mid-flight. Derived from the
  // toggle mutation so we don't need to track it in local state.
  const busyTask = toggleTask.isPending ? toggleTask.variables : null;

  // knowledge tree removed from Mission Control (frontend-only redesign)

  const onToggleTask = (taskId) => {
    if (!missionId) return;
    toggleTask.mutate(taskId, { onSettled: () => refreshMission() });
  };

  const onCompleteMission = () => {
    if (!missionId) return;
    setBusyAction('complete');
    completeMissionM.mutate(undefined, {
      onSuccess: () => toast.success('Mission completed. Streak updated.'),
      onSettled: () => { setBusyAction(null); refreshMission(); },
    });
  };

  const onSkipMission = () => {
    if (!missionId) return;
    setBusyAction('skip');
    skipMissionM.mutate(undefined, {
      onSuccess: () => toast('Mission skipped.', { icon: <SkipForward className="h-4 w-4" /> }),
      onSettled: () => setBusyAction(null),
    });
  };

  const onOpenKnowledgeNode = (nodeId) => {
    navigate(`/app/knowledge-base/nodes/${encodeURIComponent(nodeId)}`);
  };

  // Phase 3D — CTA handlers. Each simply routes to the correct page; the
  // decision of WHICH cta to show is made by the backend (Mission Context).
  const onOpenArena = () => navigate('/app/coding-arena');
  const onStartAssessment = () => {
    if (missionId) navigate(`/app/assessment/${missionId}`);
  };
  const onFlashcards = () => toast('Flashcards are coming soon.');

  const onOpenMentorForNode = (task) => {
    aiPanel.openWith(task.title, { topicNodeId: task.node_id });
  };

  if (loading || !data) {
    return (
      <div className="py-24 flex flex-col items-center gap-3 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span className="overline">Loading workspace</span>
      </div>
    );
  }

  const { mission, streak, readiness, knowledge, revisions, activity, onboarding, adjustment, company_readiness, pacing } = data;
  const tasks = mission.tasks || [];
  const doneCount = tasks.filter((t) => t.completed).length;
  const totalCount = tasks.length || 1;
  const progressPct = Math.round((doneCount / totalCount) * 100);
  const missionCompleted = mission.status === 'completed';
  const missionSkipped = mission.status === 'skipped';

  const targetCompanies = (onboarding.target_companies || [])
    .map((id) => TARGET_COMPANIES.find((c) => c.id === id))
    .filter(Boolean);

  return (
    <div className="space-y-6" data-testid={DASHBOARD.root}>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4"
      >
        <div>
          <div className="overline mb-2">Mission Control</div>
          <h1 className="font-display text-3xl sm:text-4xl font-semibold tracking-tight">
            Welcome back, {user?.name?.split(' ')[0]}.
          </h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Calibrated for {targetCompanies.length || '—'} target {targetCompanies.length === 1 ? 'company' : 'companies'}
            {onboarding.days_to_target != null && <> · {onboarding.days_to_target} days to target</>}.
          </p>
        </div>
        <div className="hidden sm:flex items-center gap-3 text-xs font-mono text-muted-foreground">
          {pacing?.has_target_date && (
            <span
              data-testid="dashboard-interview-countdown"
              className="flex items-center gap-2 rounded-full border border-primary/25 bg-primary/[0.06] px-3 py-1.5"
            >
              <Calendar className="h-3.5 w-3.5 text-primary" />
              <span>{pacing.remaining_days} Days Left</span>
              <span className="text-white/20">·</span>
              <span>{pacing.emoji} {pacing.label}</span>
            </span>
          )}
          <span className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            Adaptive Engine · v2
          </span>
        </div>
      </motion.div>

      {/* Adaptive banner */}
      {adjustment && adjustment.reason && (
        <motion.div
          initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}
          data-testid="dashboard-adaptive-banner"
          className={cn(
            'rounded-xl border px-4 py-3 flex items-start gap-3',
            adjustment.mode === 'revise'  && 'border-amber-400/30 bg-amber-400/[0.06]',
            adjustment.mode === 'advance' && 'border-emerald-400/30 bg-emerald-400/[0.06]',
            (!adjustment.mode || adjustment.mode === 'continue') && 'border-primary/25 bg-primary/[0.06]',
          )}
        >
          <TrendingUp className="h-4 w-4 mt-0.5 shrink-0 text-primary" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span className="overline text-primary">Adaptive plan</span>
              {adjustment.mode && (
                <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground border border-white/10 rounded-full px-2 py-0.5">
                  {adjustment.mode}
                </span>
              )}
            </div>
            <p className="text-sm">{adjustment.reason}</p>
            {adjustment.inserted_prerequisites?.length > 0 && (
              <p className="text-xs text-muted-foreground mt-1">
                Prerequisite revisions inserted: {adjustment.inserted_prerequisites.join(', ')}.
              </p>
            )}
          </div>
        </motion.div>
      )}

      {/* Interview Progress strip — powered by /api/roadmap/summary */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3" data-testid="interview-progress-strip">
          <GlassCard className="p-4" data-testid="progress-tile-overall">
            <div className="overline mb-1">Overall</div>
            <div className="flex items-baseline gap-1">
              <span className="font-display text-2xl font-semibold">{Math.round(summary.overall.readiness)}</span>
              <span className="text-xs text-muted-foreground">%</span>
            </div>
            <ProgressBar value={summary.overall.readiness} className="mt-2" size="sm" />
            <div className="mt-2 text-[10px] font-mono text-muted-foreground">
              {summary.overall.completed_topics}/{summary.overall.total_topics} topics
            </div>
          </GlassCard>
          {['dsa', 'lld', 'hld', 'behavioral'].map((tid) => {
            const t = (summary.tracks || []).find((x) => x.id === tid);
            if (!t) return null;
            return (
              <GlassCard key={tid} className="p-4" data-testid={`progress-tile-${tid}`}>
                <div className="overline mb-1 truncate">{t.label}</div>
                <div className="flex items-baseline gap-1">
                  <span className="font-display text-2xl font-semibold">{Math.round(t.completion_pct)}</span>
                  <span className="text-xs text-muted-foreground">%</span>
                </div>
                <ProgressBar value={t.completion_pct} className="mt-2" size="sm" />
                <div className="mt-2 text-[10px] font-mono text-muted-foreground">
                  {t.completed_topics}/{t.total_topics} · {t.estimated_hours_remaining}h left
                </div>
              </GlassCard>
            );
          })}
          <GlassCard className="p-4" data-testid="progress-tile-today">
            <div className="overline mb-1">Today</div>
            <div className="flex items-baseline gap-1">
              <span className="font-display text-2xl font-semibold">{summary.today.completed_count}</span>
              <span className="text-xs text-muted-foreground">done</span>
            </div>
            <div className="mt-2 text-[10px] font-mono text-muted-foreground">
              {summary.counts.revision_due} revision due · {summary.counts.bookmarked} bookmarks
            </div>
          </GlassCard>
        </div>
      )}

      {/* Bento grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-5">
        {/* Today's Mission — hero */}
        <GlassCard
          data-testid={DASHBOARD.widgetTodayMission}
          className="p-6 md:col-span-2 lg:col-span-2 lg:row-span-2 relative overflow-hidden"
        >
          <div className="absolute -top-24 -right-24 h-56 w-56 rounded-full bg-primary/10 blur-3xl" />
          <WidgetHeader
            icon={Target}
            title="Today's Mission"
            action={
              <div className="flex items-center gap-2">
                {mission.recommendation_insight && (
                  <WhyThisMissionDialog
                    insight={mission.recommendation_insight}
                    missionTitle={mission.title}
                    focusArea={mission.focus_area}
                  />
                )}
                <span className={cn('px-2 py-0.5 rounded-full text-[11px] font-mono uppercase tracking-wider border',
                  missionCompleted ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300'
                  : missionSkipped ? 'border-amber-400/30 bg-amber-400/10 text-amber-300'
                  : 'border-primary/30 bg-primary/10 text-primary')}
                >
                  {missionCompleted ? 'Completed' : missionSkipped ? 'Skipped' : 'In progress'}
                </span>
              </div>
            }
          />
          <div className="mt-1">
            <h2 className="font-display text-2xl font-semibold tracking-tight leading-snug max-w-lg">
              {mission.title}
            </h2>
            <p className="mt-2 text-sm text-muted-foreground max-w-md">
              {mission.learning_objective}
            </p>
            {mission.ai_narrative && (
              <div className="mt-3 rounded-lg border border-primary/25 bg-primary/[0.06] px-3.5 py-2.5">
                <div className="text-[10px] font-mono uppercase tracking-wider text-primary/80 mb-0.5">
                  Mentor's take
                </div>
                <div className="text-sm text-foreground/95">{mission.ai_narrative}</div>
              </div>
            )}
            {/* Why this mission moved to the "Why this?" button in the header (RC1.3). */}
            <div className="mt-6 grid grid-cols-3 gap-6">
              <div>
                <div className="overline mb-1">Focus</div>
                <div className="text-sm font-medium">{mission.focus_area}</div>
              </div>
              <div>
                <div className="overline mb-1">Est. time</div>
                <div className="text-sm font-medium flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                  {Math.round(mission.estimated_duration_minutes / 60 * 10) / 10} h
                </div>
              </div>
              <div>
                <div className="overline mb-1">Difficulty</div>
                <span className={cn('inline-block px-2 py-0.5 rounded-md text-xs border capitalize', difficultyChipClass(mission.difficulty))}>
                  {mission.difficulty}
                </span>
              </div>
            </div>

            <div className="mt-6">
              <div className="flex items-center justify-between mb-2">
                <span className="overline">Progress</span>
                <span className="font-mono text-xs text-muted-foreground">{doneCount} / {tasks.length}</span>
              </div>
              <div className="h-1.5 rounded-full bg-white/[0.05] overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-primary to-secondary"
                  animate={{ width: `${progressPct}%` }}
                  transition={{ type: 'spring', stiffness: 200, damping: 30 }}
                />
              </div>
            </div>

            {/* Tasks — once the mission is completed, tasks become read-only
                (RC1.3.1 immutability contract). The backend enforces this
                too (409 on toggle); the disabled state here surfaces the
                lock immediately so the UI doesn't offer an interaction
                that will be rejected. */}
            <div className="mt-5 space-y-2">
              {tasks.map((t) => {
                const isBusy = busyTask === t.id;
                const taskCtx = getTaskContext({ taskId: t.id, nodeId: t.node_id });
                const taskLocked = missionSkipped || missionCompleted;
                return (
                  <div key={t.id} className="flex items-stretch gap-2">
                    <button
                      onClick={() => !taskLocked && onToggleTask(t.id)}
                      disabled={taskLocked || isBusy}
                      data-testid={`mission-task-${t.id}`}
                      title={missionCompleted ? 'Mission completed — tasks are locked.' : undefined}
                      className={cn(
                        'group flex-1 text-left flex items-center gap-3 rounded-lg border px-3 py-2.5 transition-colors',
                        t.completed
                          ? 'border-emerald-400/40 bg-emerald-400/[0.12]'
                          : 'border-white/[0.06] bg-white/[0.02]',
                        !taskLocked && (t.completed ? 'hover:bg-emerald-400/[0.16]' : 'hover:bg-white/[0.05] hover:border-white/[0.12]'),
                        taskLocked && 'cursor-not-allowed opacity-95',
                      )}
                    >
                      <span className={cn('h-5 w-5 rounded-full border flex items-center justify-center shrink-0 transition-colors',
                        t.completed ? 'border-emerald-400 bg-emerald-400 text-emerald-950' : 'border-white/15')}>
                        {isBusy ? <Loader2 className="h-3 w-3 animate-spin" />
                          : t.completed ? <Check className="h-3 w-3" strokeWidth={3} />
                          : <Circle className="h-2 w-2" />}
                      </span>
                      <span className="flex-1 text-sm text-foreground">
                        {t.title}
                      </span>
                      <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-mono text-muted-foreground uppercase tracking-wider">
                        {taskKindIcon(t.kind)}
                        {t.kind}
                      </span>
                    </button>
                    <TaskActions
                      task={t}
                      taskCtx={taskCtx}
                      onOpenKB={onOpenKnowledgeNode}
                      onOpenArena={onOpenArena}
                      onStartAssessment={onStartAssessment}
                      onFlashcards={onFlashcards}
                      onOpenMentor={onOpenMentorForNode}
                      busyAction={busyAction}
                    />
                  </div>
                );
              })}
            </div>

            {/* Phase 3C · Assessment checkpoint — the final step of the daily
                mission. Unlocks once every study & coding task is done. */}
            {!missionSkipped && (
              <div className="mt-4">
                <button
                  onClick={() => navigate(`/app/assessment/${mission.id}`)}
                  disabled={doneCount < tasks.length || missionCompleted || mission.assessment_status === 'completed'}
                  data-testid="mission-take-assessment"
                  className={cn(
                    'w-full text-left flex items-center gap-3 rounded-lg border px-3 py-2.5 transition-colors',
                    mission.assessment_status === 'completed'
                      ? 'border-emerald-400/40 bg-emerald-400/[0.12]'
                      : 'border-primary/30 bg-primary/[0.06]',
                    (doneCount < tasks.length || missionCompleted || mission.assessment_status === 'completed')
                      ? 'cursor-not-allowed opacity-70'
                      : 'hover:bg-primary/[0.12]',
                  )}
                >
                  <span className={cn('h-5 w-5 rounded-full border flex items-center justify-center shrink-0',
                    mission.assessment_status === 'completed' ? 'border-emerald-400 bg-emerald-400 text-emerald-950' : 'border-primary/40 text-primary')}>
                    {mission.assessment_status === 'completed'
                      ? <Check className="h-3 w-3" strokeWidth={3} />
                      : <ClipboardCheck className="h-3 w-3" />}
                  </span>
                  <span className="flex-1 text-sm text-foreground">Take Assessment</span>
                  <span className="text-[11px] font-mono uppercase tracking-wider text-primary">
                    {mission.assessment_status === 'completed'
                      ? 'Done'
                      : doneCount < tasks.length ? 'Locked' : 'Start Assessment'}
                  </span>
                </button>
                {doneCount < tasks.length && !missionCompleted && (
                  <p className="mt-1.5 text-xs text-muted-foreground">
                    Finish your study and coding tasks to unlock the assessment.
                  </p>
                )}
              </div>
            )}

            {!missionCompleted && !missionSkipped && (
              <div className="mt-6 flex flex-wrap gap-2.5">
                <button
                  onClick={onCompleteMission} disabled={busyAction === 'complete'}
                  data-testid="mission-complete-button"
                  className="h-10 px-4 rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-medium btn-primary-glow disabled:opacity-60 transition-colors inline-flex items-center gap-2"
                >
                  {busyAction === 'complete'
                    ? <><Loader2 className="h-3.5 w-3.5 animate-spin" />Completing…</>
                    : <><CheckCircle2 className="h-3.5 w-3.5" />Mark mission complete</>}
                </button>
                <button
                  onClick={onSkipMission} disabled={busyAction === 'skip'}
                  data-testid="mission-skip-button"
                  className="h-10 px-4 rounded-lg border border-white/[0.1] hover:bg-white/[0.04] text-sm text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-2"
                >
                  {busyAction === 'skip'
                    ? <><Loader2 className="h-3.5 w-3.5 animate-spin" />Skipping…</>
                    : <><SkipForward className="h-3.5 w-3.5" />Skip today</>}
                </button>
              </div>
            )}
            {missionCompleted && (
              <div className="mt-6 flex items-center gap-2 text-sm text-emerald-300">
                <CheckCircle2 className="h-4 w-4" />
                Nice work — mission logged. Tomorrow's plan adapts to today's confidence.
              </div>
            )}
            {missionSkipped && (
              <div className="mt-6 flex items-center gap-2 text-sm text-amber-300">
                <SkipForward className="h-4 w-4" />
                Skipped for today. Streak will reset unless you complete tomorrow's mission.
              </div>
            )}
          </div>
        </GlassCard>

        {/* Adaptive Mission Engine — Tomorrow Preview + Week Goal.
            RC1.3.3 · Forecast robustness:
              The card renders whenever ANY forecast source is available:
                a) AI-enriched tomorrow_preview / week_goal, OR
                b) the deterministic `likely_next_topics` computed by
                   services/learning_engine/foresight.py — always
                   produced when planner data is sufficient, so this
                   lane keeps the widget alive even when the AI
                   enrichment layer is silent.
              Text uses `line-clamp-2` + `title` for hover-hint so long
              labels wrap gracefully instead of clipping abruptly. */}
        {(mission.tomorrow_preview
          || mission.week_goal
          || (Array.isArray(mission.recommendation_insight?.likely_next_topics)
              && mission.recommendation_insight.likely_next_topics.length > 0)) && (
          <GlassCard className="p-6 md:col-span-2 lg:col-span-2" data-testid="mission-adaptive-forecast">
            <WidgetHeader icon={Route} title="What's next · adaptive forecast" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
              {mission.tomorrow_preview && (
                <div className="rounded-lg border border-white/[0.08] bg-white/[0.02] p-4 min-w-0">
                  <div className="text-[10px] font-mono uppercase tracking-wider text-primary/80 mb-1">Tomorrow</div>
                  <ul className="text-sm space-y-1 mb-2">
                    <li className="flex items-start gap-2">
                      <span className="text-primary mt-0.5">•</span>
                      <span className="flex-1 min-w-0 line-clamp-2 break-words" title={mission.tomorrow_preview.focus}>
                        {mission.tomorrow_preview.focus}
                      </span>
                    </li>
                    {Array.isArray(mission.tomorrow_preview.topics) && mission.tomorrow_preview.topics.slice(0, 4).map((t, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-primary mt-0.5">•</span>
                        <span className="flex-1 min-w-0 line-clamp-2 break-words" title={t}>{t}</span>
                      </li>
                    ))}
                  </ul>
                  {mission.tomorrow_preview.estimated_duration && (
                    <div className="text-[12px] text-muted-foreground flex items-center gap-2">
                      <span>⏱</span>
                      <span className="font-mono">{mission.tomorrow_preview.estimated_duration} min</span>
                    </div>
                  )}
                </div>
              )}
              {mission.week_goal && (
                <div className="rounded-lg border border-white/[0.08] bg-white/[0.02] p-4 min-w-0">
                  <div className="text-[10px] font-mono uppercase tracking-wider text-primary/80 mb-1">This week</div>
                  <ul className="text-sm space-y-1 mb-2">
                    {Array.isArray(mission.week_goal.milestones) && mission.week_goal.milestones.slice(0, 6).map((m, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-emerald-400 mt-0.5">✓</span>
                        <span className="flex-1 min-w-0 line-clamp-2 break-words" title={m}>{m}</span>
                      </li>
                    ))}
                  </ul>
                  {mission.week_goal.estimated_hours && (
                    <div className="text-[12px] text-muted-foreground flex items-center gap-2">
                      <span>≈</span>
                      <span className="font-mono">{mission.week_goal.estimated_hours}h</span>
                    </div>
                  )}
                </div>
              )}
              {/* Planner-preview fallback: shows deterministically whenever
                  the mission has recommendation_insight.likely_next_topics
                  and no AI enrichment is available for that lane. */}
              {!mission.tomorrow_preview
                && Array.isArray(mission.recommendation_insight?.likely_next_topics)
                && mission.recommendation_insight.likely_next_topics.length > 0 && (
                <div className="rounded-lg border border-white/[0.08] bg-white/[0.02] p-4 min-w-0">
                  <div className="text-[10px] font-mono uppercase tracking-wider text-primary/80 mb-1 flex items-center gap-2">
                    <span>Likely next topics</span>
                    <span className="text-muted-foreground/70 normal-case tracking-normal">· planner preview</span>
                  </div>
                  <ul className="text-sm space-y-1.5 mb-1">
                    {mission.recommendation_insight.likely_next_topics.slice(0, 4).map((t, i) => (
                      <li key={t.node_id || i} className="flex items-start gap-2">
                        <span className="text-[9px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-primary/10 border border-primary/25 text-primary/90 shrink-0 mt-0.5">
                          {t.when || 'next'}
                        </span>
                        <span
                          className="flex-1 min-w-0 line-clamp-2 break-words text-foreground/95"
                          title={t.label + (t.why ? ` — ${t.why}` : '')}
                        >
                          {t.label}
                        </span>
                      </li>
                    ))}
                  </ul>
                  <div className="text-[11px] text-muted-foreground mt-1">
                    Future missions remain adaptive — this is a preview, not a guarantee.
                  </div>
                </div>
              )}
            </div>
          </GlassCard>
        )}

        {/* Interview Readiness */}
        <GlassCard data-testid={DASHBOARD.widgetReadiness} className="p-6">
          <WidgetHeader icon={ShieldCheck} title="Interview Readiness" />
          <div className="flex items-end gap-3">
            <span className="font-display text-4xl font-semibold tracking-tight">
              {Math.round(readiness)}<span className="text-lg text-muted-foreground">%</span>
            </span>
            <span className={cn('text-xs mb-1', readiness >= 70 ? 'text-emerald-400' : readiness >= 40 ? 'text-amber-400' : 'text-muted-foreground')}>
              {readiness >= 70 ? 'On track' : readiness >= 40 ? 'Building' : 'Baseline'}
            </span>
          </div>
          <div className="mt-4 h-1.5 rounded-full bg-white/[0.05] overflow-hidden">
            <motion.div className="h-full bg-gradient-to-r from-primary to-secondary"
              animate={{ width: `${readiness}%` }} transition={{ type: 'spring', stiffness: 200, damping: 30 }} />
          </div>
          <p className="mt-3 text-xs text-muted-foreground">Weighted across DSA · Java · LLD · HLD · Core CS.</p>
        </GlassCard>

        {/* Study Streak and Company Readiness removed for Execution Dashboard */}

        {/* Upcoming Revision */}
        <GlassCard data-testid={DASHBOARD.widgetRevision} className="p-6 md:col-span-1 lg:col-span-2">
          <WidgetHeader icon={RefreshCcw} title="Upcoming Revision" />
          {revisions.length === 0 ? (
            <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-4 text-sm text-muted-foreground">
              No revisions queued yet. They'll appear once you complete tasks.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {revisions.slice(0, 3).map((r) => (
                <div key={r.id} className={cn(
                  'rounded-lg border p-3',
                  r.is_due ? 'border-primary/30 bg-primary/[0.06]' : 'border-white/[0.06] bg-white/[0.02]',
                )}>
                  <div className="overline mb-1">
                    {r.is_due ? 'Due now' : `In ${Math.max(1, Math.ceil((new Date(r.next_review_date) - new Date()) / 86400000))}d`}
                  </div>
                  <p className="text-sm line-clamp-2">{r.task_title}</p>
                </div>
              ))}
            </div>
          )}
          <p className="mt-4 text-xs text-muted-foreground">Spaced repetition · 1d → 3d → 7d → 14d → 30d → 60d (confidence-adjusted).</p>
        </GlassCard>

        {/* Knowledge Progress removed from Mission Control */}

        {/* Recent Activity removed from Mission Control */}

        {/* Notifications removed from Mission Control */}
      </div>
    </div>
  );
}
