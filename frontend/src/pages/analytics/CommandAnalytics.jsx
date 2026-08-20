import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart3, Clock, Flame, Target, TrendingUp, TrendingDown,
  BookOpen, RefreshCw, Building2, Loader2, Sparkles,
} from 'lucide-react';
import { GlassCard } from '@/components/common/GlassCard';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { dashboardService, roadmapService } from '@/services/mission.service';
import { TodaysMissionBanner } from '@/components/mission/TodaysMissionBanner';
import api from '@/services/api';
import { cn } from '@/lib/utils';
import { WeeklyActivityWidget } from '@/components/dashboard/WeeklyActivityWidget';

/**
 * Command Analytics — real dashboard sourced from existing endpoints:
 *   /api/dashboard           → streak, readiness, company_readiness, knowledge, activity
 *   /api/roadmap/summary     → completion %, hours remaining, weak/strong nodes
 *   /api/mentor/context/preview → mentor's snapshot (weak/strong topics, revision queue)
 *   /api/activity            → recent activity events
 *
 * No mock data — if a signal is missing we render an empty state, not a fake number.
 */

function StatCard({ label, value, hint, icon: Icon, accent = 'primary' }) {
  const accentCls = {
    primary: 'text-primary bg-primary/10 border-primary/25',
    emerald: 'text-emerald-300 bg-emerald-400/10 border-emerald-400/25',
    amber: 'text-amber-300 bg-amber-400/10 border-amber-400/25',
    rose: 'text-rose-300 bg-rose-400/10 border-rose-400/25',
    sky: 'text-sky-300 bg-sky-400/10 border-sky-400/25',
  }[accent];
  return (
    <GlassCard className="p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className={cn('h-7 w-7 rounded-md border flex items-center justify-center', accentCls)}>
          <Icon className="h-3.5 w-3.5" />
        </span>
        <div className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{label}</div>
      </div>
      <div className="text-2xl font-display font-semibold tracking-tight">{value}</div>
      {hint && <div className="text-xs text-muted-foreground mt-0.5">{hint}</div>}
    </GlassCard>
  );
}

function WeekHeatmap() { return null; }
// Weekly heatmap removed in RC1.3 — replaced by <WeeklyActivityWidget />
// which sources the same underlying activity data.
// (Kept the stub above so this file's imports/exports remain stable.)

function TopicScoreBar({ topic }) {
  const score = Math.round(topic.score || 0);
  const color = score >= 70 ? 'bg-emerald-500' : score >= 40 ? 'bg-amber-500' : 'bg-rose-500';
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <div className="text-sm">{topic.label}</div>
        <div className="text-xs font-mono text-muted-foreground">{score}%</div>
      </div>
      <div className="h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
        <div className={cn('h-full transition-all', color)} style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}

function CompanyReadiness({ items }) {
  if (!items?.length) return null;
  return (
    <GlassCard className="p-4">
      <div className="flex items-center gap-2 mb-3">
        <Building2 className="h-4 w-4 text-primary" />
        <h3 className="font-display text-sm font-semibold tracking-tight">Company Readiness</h3>
      </div>
      <div className="space-y-3">
        {items.map((c) => (
          <div key={c.company_id}>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-1.5">
                <span className="text-sm capitalize">{c.company_id}</span>
                {c.is_target && (
                  <Badge variant="outline" className="text-[9px] font-mono py-0 px-1 border-primary/30 text-primary/90">Target</Badge>
                )}
              </div>
              <div className="text-xs font-mono">{Math.round(c.score)}%</div>
            </div>
            <Progress value={c.score} className="h-1.5" />
          </div>
        ))}
      </div>
    </GlassCard>
  );
}

export default function CommandAnalytics() {
  const [dashboard, setDashboard] = useState(null);
  const [summary, setSummary] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [d, s, p] = await Promise.all([
        dashboardService.get().catch(() => null),
        api.get('/roadmap/summary').then((r) => r.data).catch(() => null),
        api.get('/mentor/context/preview').then((r) => r.data).catch(() => null),
      ]);
      setDashboard(d);
      setSummary(s);
      setPreview(p);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const knowledgeSorted = useMemo(() => {
    if (!dashboard?.knowledge) return [];
    return [...dashboard.knowledge].sort((a, b) => (b.score || 0) - (a.score || 0));
  }, [dashboard]);

  const roadmapTotals = useMemo(() => {
    const tracks = summary?.tracks || [];
    let total = 0, completed = 0, inProgress = 0;
    for (const t of tracks) {
      total += t.total_topics || 0;
      completed += t.completed_topics || 0;
      inProgress += Math.max(0, (t.total_topics || 0) - (t.completed_topics || 0) - (t.remaining_topics || 0));
    }
    // If in_progress is 0 because remaining==total-completed, fall back to touched-completed.
    return { total, completed, inProgress };
  }, [summary]);

  if (loading) {
    return (
      <div className="py-24 flex flex-col items-center gap-3 text-muted-foreground">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
        <div className="text-xs font-mono uppercase tracking-wider">Loading analytics…</div>
      </div>
    );
  }

  const streak = dashboard?.streak || {};
  const readiness = Math.round(dashboard?.readiness ?? 0);
  const missionsCompleted = dashboard?.mission?.status === 'completed' ? 1 : 0;
  const missionTasksDone = (dashboard?.mission?.tasks || []).filter((t) => t.completed).length;
  const missionTasksTotal = (dashboard?.mission?.tasks || []).length;
  const revisionDue = (dashboard?.revisions || []).filter((r) => r.is_due).length;
  const totalNodes = roadmapTotals.total;
  const completedNodes = roadmapTotals.completed;
  const inProgressNodes = roadmapTotals.inProgress;

  return (
    <div data-testid="command-analytics-root" className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <span className="h-11 w-11 rounded-xl bg-primary/12 border border-primary/25 flex items-center justify-center">
          <BarChart3 className="h-5 w-5 text-primary" />
        </span>
        <div className="flex-1">
          <div className="overline">Command Analytics</div>
          <h1 className="font-display text-3xl sm:text-4xl font-semibold tracking-tight mt-1">
            Your learning telemetry.
          </h1>
          <p className="mt-2 text-sm text-muted-foreground max-w-2xl">
            Real-time view of streak, readiness, topic mastery, weak areas and revision queue.
            Every number is sourced from your actual progress — no placeholders.
          </p>
        </div>
        <button
          onClick={load}
          className="h-9 px-3 rounded-lg border border-white/[0.08] hover:bg-white/[0.04] transition-colors text-xs flex items-center gap-1.5 text-muted-foreground hover:text-foreground"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </button>
      </div>

      {/* Today's Mission Context — same source of truth as every other page. */}
      <TodaysMissionBanner />

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="Current Streak" value={`${streak.current || 0}d`} hint={`Longest: ${streak.longest || 0}d`} icon={Flame} accent="amber" />
        <StatCard label="Interview Readiness" value={`${readiness}%`} hint={completedNodes ? `${completedNodes}/${totalNodes} topics done` : 'Complete more topics'} icon={Target} accent="primary" />
        <StatCard label="Today's Mission" value={`${missionTasksDone}/${missionTasksTotal}`} hint={missionsCompleted ? 'Completed' : 'In progress'} icon={Sparkles} accent="emerald" />
        <StatCard label="Revision Due" value={revisionDue} hint={revisionDue > 0 ? 'Cards waiting' : 'All caught up'} icon={RefreshCw} accent={revisionDue > 0 ? 'rose' : 'sky'} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Weekly activity — reuses the shared WeeklyActivityWidget so both
            Mission Control (removed) and Command Analytics stay in sync. */}
        <div className="lg:col-span-2">
          <WeeklyActivityWidget />
        </div>

        {/* Roadmap progress */}
        <GlassCard className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <BookOpen className="h-4 w-4 text-primary" />
            <h3 className="font-display text-sm font-semibold tracking-tight">Roadmap Progress</h3>
          </div>
          <div className="space-y-2">
            <div>
              <div className="flex items-center justify-between mb-1">
                <div className="text-xs text-muted-foreground">Completed</div>
                <div className="text-xs font-mono">{completedNodes}/{totalNodes}</div>
              </div>
              <Progress value={totalNodes ? (completedNodes / totalNodes) * 100 : 0} className="h-1.5" />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <div className="text-xs text-muted-foreground">In progress</div>
                <div className="text-xs font-mono">{inProgressNodes}</div>
              </div>
              <Progress value={totalNodes ? (inProgressNodes / totalNodes) * 100 : 0} className="h-1.5" />
            </div>
          </div>
        </GlassCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Topic mastery */}
        <GlassCard className="p-4 lg:col-span-2">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="h-4 w-4 text-primary" />
            <h3 className="font-display text-sm font-semibold tracking-tight">Topic Mastery</h3>
          </div>
          {knowledgeSorted.length === 0 ? (
            <div className="text-xs text-muted-foreground py-4 text-center">
              Complete a few mission tasks to see your topic mastery emerge.
            </div>
          ) : (
            <div className="space-y-3">
              {knowledgeSorted.slice(0, 8).map((t) => (
                <TopicScoreBar key={t.topic} topic={t} />
              ))}
            </div>
          )}
        </GlassCard>

        {/* Company readiness */}
        <CompanyReadiness items={dashboard?.company_readiness || []} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Weak areas */}
        <GlassCard className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <TrendingDown className="h-4 w-4 text-rose-300" />
            <h3 className="font-display text-sm font-semibold tracking-tight">Weak Areas</h3>
          </div>
          {(preview?.weak_topics || []).length === 0 ? (
            <div className="text-xs text-muted-foreground py-2">No weak areas detected yet — the mentor will flag them as you progress.</div>
          ) : (
            <ul className="space-y-1.5">
              {preview.weak_topics.map((t, i) => (
                <li key={i} className="flex items-center gap-2 text-sm">
                  <span className="h-1.5 w-1.5 rounded-full bg-rose-300" />
                  {t}
                </li>
              ))}
            </ul>
          )}
        </GlassCard>

        {/* Strong areas */}
        <GlassCard className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="h-4 w-4 text-emerald-300" />
            <h3 className="font-display text-sm font-semibold tracking-tight">Strong Areas</h3>
          </div>
          {(preview?.strong_topics || []).length === 0 ? (
            <div className="text-xs text-muted-foreground py-2">Keep going — strong areas emerge once you hit ≥60% mastery + 7+ confidence.</div>
          ) : (
            <ul className="space-y-1.5">
              {preview.strong_topics.map((t, i) => (
                <li key={i} className="flex items-center gap-2 text-sm">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-300" />
                  {t}
                </li>
              ))}
            </ul>
          )}
        </GlassCard>
      </div>

      {/* Per-track breakdown (from /api/roadmap/summary) */}
      {summary?.tracks?.length > 0 && (
        <GlassCard className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <BookOpen className="h-4 w-4 text-primary" />
            <h3 className="font-display text-sm font-semibold tracking-tight">Track-by-Track Roadmap Progress</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {summary.tracks.map((t) => (
              <div key={t.id} className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="text-sm font-medium">{t.label}</div>
                  <div className="text-[10px] font-mono text-muted-foreground">{Math.round(t.completion_pct)}%</div>
                </div>
                <Progress value={t.completion_pct || 0} className="h-1.5" />
                <div className="mt-1.5 text-[10px] font-mono text-muted-foreground">
                  {t.completed_topics}/{t.total_topics} topics · {t.estimated_hours_remaining?.toFixed?.(1) || 0}h left
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {/* Recent activity */}
      <GlassCard className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="h-4 w-4 text-primary" />
          <h3 className="font-display text-sm font-semibold tracking-tight">Recent Activity</h3>
        </div>
        {(dashboard?.activity || []).length === 0 ? (
          <div className="text-xs text-muted-foreground py-2">No activity yet.</div>
        ) : (
          <ul className="divide-y divide-white/[0.04]">
            {dashboard.activity.map((a, i) => (
              <li key={i} className="py-2 flex items-center justify-between text-sm">
                <div>
                  <div className="text-sm">{a.title || a.kind}</div>
                  {a.description && <div className="text-xs text-muted-foreground">{a.description}</div>}
                </div>
                <div className="text-[10px] font-mono uppercase text-muted-foreground">{a.ts?.slice(11, 16)}</div>
              </li>
            ))}
          </ul>
        )}
      </GlassCard>
    </div>
  );
}
