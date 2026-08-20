import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import {
  ChevronRight, Loader2, Home, ExternalLink, Clock, Save, Star,
  MessageSquare, Zap, ArrowLeft, Building2,
} from 'lucide-react';
import { GlassCard } from '@/components/common/GlassCard';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { useRoadmapNode } from '@/queries/hooks';
import {
  useSetNodeStatus, useSetNodeConfidence,
  useRecordAttempt, useSaveNodeNotes,
} from '@/queries/mutations';
import { userService } from '@/services/auth.service';
import { formatApiError } from '@/utils/formatApiError';
import { TARGET_COMPANIES } from '@/config/companies';
import { cn } from '@/lib/utils';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { StatusBadge } from '@/components/progress/StatusBadge';
import { NodeActions } from '@/components/progress/NodeActions';
import { AIContentTabs } from '@/components/knowledge/AIContentTabs';
import { AIInterviewCards } from '@/components/knowledge/AIInterviewCards';
import { useRecentlyViewed } from '@/hooks/useRecentlyViewed';
import { useMissionContext } from '@/contexts/MissionContextProvider';
import { TodaysMissionBanner } from '@/components/mission/TodaysMissionBanner';

const BUCKET_LABEL = {
  green:  { label: 'Fresh',   cls: 'text-emerald-300 border-emerald-400/30 bg-emerald-400/10' },
  yellow: { label: 'Review',  cls: 'text-amber-300 border-amber-400/30 bg-amber-400/10' },
  red:    { label: 'Weak',    cls: 'text-rose-300 border-rose-400/30 bg-rose-400/10' },
};

function starLine(count) {
  const filled = Math.max(0, Math.min(5, count | 0));
  const empty = 5 - filled;
  return '★'.repeat(filled) + '☆'.repeat(empty);
}

export default function DeepTopicPage() {
  const { nodeId } = useParams();
  const navigate = useNavigate();

  // RC1.3.2B · The heavy `load()` + `setLoading(true)` cycle is gone.
  // React Query owns the cache; optimistic mutations patch it
  // instantly so this page no longer flickers back through the
  // Loading skeleton on save.
  const { data, isLoading } = useRoadmapNode(nodeId);
  const [notes, setNotes] = useState('');
  const [confidence, setConfidence] = useState([0]);
  const [targetCompanies, setTargetCompanies] = useState([]);

  // Sync local edit-buffers with server data whenever the node changes.
  // Notes + confidence are edit-in-place fields, so we mirror them into
  // local state; mutations still write through the shared cache.
  useEffect(() => {
    if (!data) return;
    setNotes(data.notes || '');
    setConfidence([data.node?.progress?.confidence || 0]);
  }, [data, nodeId]);

  useEffect(() => {
    // Load target companies so we can put them first in the Interview
    // Importance card. Fails silently — if we can't reach onboarding we just
    // fall back to unsorted scores.
    userService.getOnboarding()
      .then((o) => setTargetCompanies(o?.target_companies || []))
      .catch(() => {});
  }, []);

  // RC1.3.4 · Track "recently viewed" for the Knowledge Workspace.
  // Persisted to a user-scoped localStorage key by `useRecentlyViewed`,
  // so this is a purely local UX signal — no backend write, no new
  // endpoint. We record after the node payload has actually loaded so
  // we don't accidentally track a broken/404 topic.
  const { record: recordRecentlyViewed } = useRecentlyViewed();
  useEffect(() => {
    if (nodeId && data?.node) {
      recordRecentlyViewed(nodeId);
    }
  }, [nodeId, data?.node, recordRecentlyViewed]);

  const setStatusM = useSetNodeStatus();
  const setConfidenceM = useSetNodeConfidence();
  const recordAttemptM = useRecordAttempt();
  const saveNotesM = useSaveNodeNotes();
  // Shared Mission Context: know if this is today's node + sync progress back.
  const { isTodaysNode, refresh: refreshMission } = useMissionContext();
  const savingConf = setConfidenceM.isPending;
  const savingNotes = saveNotesM.isPending;

  const saveNotes = () => {
    saveNotesM.mutate({ nodeId, notes }, {
      onSuccess: () => toast.success('Notes saved.'),
    });
  };

  const saveConfidence = () => {
    setConfidenceM.mutate({ nodeId, value: confidence[0] }, {
      onSuccess: () => toast.success('Confidence updated.'),
    });
  };

  if (isLoading || !data) {
    return (
      <div className="py-24 flex flex-col items-center gap-3 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span className="overline">Loading topic</span>
      </div>
    );
  }

  const { node, breadcrumb, prerequisites, related, problems, company_importance, activity } = data;
  const progress = node.progress || {};

  // RC1.3 — dynamic Interview Importance:
  //   1. User's target companies first (in the order they appear on Profile).
  //   2. Then any other companies with a non-zero importance for this topic,
  //      sorted by score desc.
  const importanceMap = company_importance || {};
  const targetSet = new Set(targetCompanies);
  const targetOrdered = targetCompanies
    .filter((cid) => cid in importanceMap)
    .map((cid) => [cid, importanceMap[cid] || 0]);
  const nonTargetOrdered = Object.entries(importanceMap)
    .filter(([cid, v]) => !targetSet.has(cid) && v > 0)
    .sort((a, b) => b[1] - a[1]);
  const importanceSorted = [...targetOrdered, ...nonTargetOrdered];

  return (
    <div className="space-y-6" data-testid="deep-topic-root">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-xs font-mono text-muted-foreground flex-wrap">
        <button onClick={() => navigate('/app/knowledge-base')}
          className="inline-flex items-center gap-1 hover:text-foreground transition-colors">
          <Home className="h-3 w-3" />
          Roadmap
        </button>
        {breadcrumb.map((b) => (
          <span key={b.id} className="inline-flex items-center gap-1.5">
            <ChevronRight className="h-3 w-3" />
            <Link
              to={`/app/knowledge-base/nodes/${b.id}`}
              data-testid={`breadcrumb-${b.id}`}
              className="hover:text-foreground transition-colors"
            >
              {b.label}
            </Link>
          </span>
        ))}
        <span className="inline-flex items-center gap-1.5">
          <ChevronRight className="h-3 w-3" />
          <span className="text-foreground">{node.label}</span>
        </span>
        <button
          onClick={() => navigate('/app/mission-control')}
          data-testid="deep-topic-back-to-mission"
          className="ml-auto inline-flex items-center gap-1.5 hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-3 w-3" />
          Back to Mission
        </button>
      </div>

      {/* Today's Mission Context — shown when this is today's mission node. */}
      {isTodaysNode(nodeId) && <TodaysMissionBanner nodeId={nodeId} className="mb-2" />}

      {/* Hero */}
      <GlassCard className="p-6 sm:p-8 relative overflow-hidden" data-testid="topic-hero">
        <div className="absolute -top-20 -right-20 h-56 w-56 rounded-full bg-primary/10 blur-3xl" />
        <div className="flex flex-col md:flex-row items-start gap-6">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <span className="overline">{node.type || 'topic'}</span>
              <StatusBadge status={progress.status || 'not_started'} />
              {progress.revision_bucket && (
                <span className={cn('text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-full border', BUCKET_LABEL[progress.revision_bucket].cls)}>
                  {BUCKET_LABEL[progress.revision_bucket].label}
                </span>
              )}
              <div className="ml-auto flex items-center gap-2">
                <NodeActions
                  nodeId={node.id}
                  bookmarked={progress.bookmarked}
                  favorite={progress.favorite}
                />
              </div>
            </div>
            <h1 className="font-display text-3xl sm:text-4xl font-semibold tracking-tight">{node.label}</h1>
            <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
              {node.pattern && (
                <span className="font-mono uppercase tracking-wider">Pattern · {node.pattern.replace('_', ' ')}</span>
              )}
              {node.difficulty && <span className="capitalize">Difficulty · {node.difficulty}</span>}
              {node.estimated_minutes ? (
                <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {node.estimated_minutes}m</span>
              ) : null}
            </div>
            <div className="mt-5 grid grid-cols-3 gap-4 max-w-md">
              <Stat label="Mastery" value={`${Math.round(progress.mastery_percentage || 0)}%`} />
              <Stat label="Confidence" value={`${(progress.confidence || 0).toFixed(1)}/10`} />
              <Stat label="Attempts" value={`${progress.attempts || 0}`} />
            </div>

            {/* Quick actions — attempt + status transitions */}
            <div className="mt-5 flex flex-wrap items-center gap-2" data-testid="topic-quick-actions">
              <Button
                onClick={() => {
                  const raw = window.prompt('Time spent on this attempt in minutes (leave blank to skip):', '');
                  const mins = raw ? Math.max(0, parseInt(raw, 10) || 0) : null;
                  recordAttemptM.mutate(
                    { nodeId: node.id, minutes: mins || null },
                    { onSuccess: () => toast.success(mins ? `Logged attempt (${mins}m).` : 'Attempt logged.') },
                  );
                }}
                data-testid="topic-record-attempt"
                variant="secondary"
                className="h-8 text-xs"
                disabled={recordAttemptM.isPending}
              >
                <Clock className="h-3.5 w-3.5 mr-1.5" />
                Record Attempt
              </Button>
              {['in_progress', 'completed', 'mastered'].map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => {
                    setStatusM.mutate(
                      { nodeId: node.id, status: s },
                      { onSuccess: () => { toast.success(`Marked as ${s.replace('_', ' ')}.`); refreshMission(); } },
                    );
                  }}
                  data-testid={`topic-mark-${s}`}
                  disabled={setStatusM.isPending}
                  className="text-[11px] font-mono uppercase tracking-wider px-2.5 py-1 rounded-full border bg-white/[0.03] border-white/[0.08] text-muted-foreground hover:text-primary hover:border-primary/30 transition-colors disabled:opacity-60"
                >
                  Mark {s.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>

          {/* Confidence editor */}
          <GlassCard className="p-4 w-full md:w-72 shrink-0 bg-white/[0.02]">
            <div className="overline mb-2">Set confidence</div>
            <div className="flex items-baseline gap-2 mb-3">
              <span className="font-display text-3xl font-semibold">{confidence[0].toFixed(1)}</span>
              <span className="text-xs text-muted-foreground">/ 10</span>
            </div>
            <Slider
              value={confidence} onValueChange={setConfidence}
              min={0} max={10} step={0.5}
              data-testid="topic-confidence-slider"
            />
            <Button
              onClick={saveConfidence} disabled={savingConf}
              data-testid="topic-confidence-save"
              className="mt-4 w-full bg-primary hover:bg-primary/90 btn-primary-glow"
            >
              {savingConf ? <><Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />Saving…</> : 'Save'}
            </Button>
          </GlassCard>
        </div>
      </GlassCard>

      {/* Prerequisites + Related + Company importance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <GlassCard className="p-6" data-testid="topic-prerequisites">
          <div className="overline mb-3">Prerequisites</div>
          {prerequisites.length === 0 ? (
            <p className="text-sm text-muted-foreground">No prerequisites — you can start here.</p>
          ) : (
            <div className="space-y-2">
              {prerequisites.map((p) => (
                <Link
                  key={p.id}
                  to={`/app/knowledge-base/nodes/${p.id}`}
                  data-testid={`prereq-${p.id}`}
                  className="block rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2.5 hover:bg-white/[0.05] transition-colors"
                >
                  <div className="text-sm">{p.label}</div>
                  <div className="mt-1 flex items-center gap-2">
                    <div className="flex-1 h-1 rounded-full bg-white/[0.05] overflow-hidden">
                      <div className="h-full bg-primary/70" style={{ width: `${p.progress?.mastery_percentage || 0}%` }} />
                    </div>
                    <span className="font-mono text-[10px] text-muted-foreground">
                      {Math.round(p.progress?.mastery_percentage || 0)}%
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </GlassCard>

        <GlassCard className="p-6" data-testid="topic-related">
          <div className="overline mb-3">Related</div>
          {related.length === 0 ? (
            <p className="text-sm text-muted-foreground">No related nodes wired yet.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {related.map((r) => (
                <Link
                  key={r.id}
                  to={`/app/knowledge-base/nodes/${r.id}`}
                  className="rounded-full border border-white/[0.1] bg-white/[0.03] px-3 py-1.5 text-xs hover:bg-white/[0.06] transition-colors"
                >
                  {r.label}
                </Link>
              ))}
            </div>
          )}
        </GlassCard>

        <GlassCard className="p-6" data-testid="topic-company-importance">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Building2 className="h-3.5 w-3.5 text-primary" />
              <div className="overline">Interview importance</div>
            </div>
            {targetCompanies.length > 0 && (
              <span className="text-[10px] font-mono uppercase tracking-wider text-primary/80">
                Targets first
              </span>
            )}
          </div>
          {importanceSorted.length === 0 ? (
            <p className="text-sm text-muted-foreground">Not yet mapped for this topic.</p>
          ) : (
            <div className="space-y-1.5">
              {importanceSorted.slice(0, 8).map(([cid, val]) => {
                const meta = TARGET_COMPANIES.find((c) => c.id === cid);
                const isTarget = targetSet.has(cid);
                const stars = Math.max(0, Math.min(5, Math.round(val || 0)));
                return (
                  <div key={cid} className={cn(
                    'flex items-center gap-2 text-sm rounded-md px-2 py-1 -mx-2',
                    isTarget && 'bg-primary/[0.06] border border-primary/20',
                  )}>
                    <span className="flex-1 truncate flex items-center gap-1.5">
                      {meta?.name || cid.replace('_', ' ')}
                      {isTarget && (
                        <span className="text-[9px] font-mono uppercase tracking-wider px-1 py-0.5 rounded bg-primary/20 text-primary/90 border border-primary/30">
                          Target
                        </span>
                      )}
                    </span>
                    <span className="text-amber-400 font-mono tracking-wider">
                      {starLine(stars)}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </GlassCard>
      </div>

      {/* Resources tabs */}
      <AIInterviewCards nodeId={node.id} />

      <AIContentTabs nodeId={node.id} />

      {/* Linked problems */}
      {problems && problems.length > 0 && (
        <GlassCard className="p-6" data-testid="topic-problems">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="h-4 w-4 text-primary" />
            <div className="overline">Linked coding problems</div>
            <span className="ml-auto text-[11px] font-mono text-muted-foreground">
              {problems.length} problem{problems.length === 1 ? '' : 's'}
            </span>
          </div>
          <div className="divide-y divide-white/[0.05]">
            {problems.map((p) => (
              <div key={p.id} className="py-3 flex items-center gap-3 text-sm">
                <span className={cn(
                  'text-[10px] font-mono uppercase tracking-wider border rounded-md px-1.5 py-0.5 capitalize',
                  p.difficulty === 'easy' ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300'
                  : p.difficulty === 'hard' ? 'border-rose-400/30 bg-rose-400/10 text-rose-300'
                  : 'border-amber-400/30 bg-amber-400/10 text-amber-300',
                )}>
                  {p.difficulty}
                </span>
                <span className="flex-1 truncate">{p.title}</span>
                {p.feedback && (
                  <span className="text-[11px] font-mono text-muted-foreground hidden sm:inline">
                    <Star className="inline h-3 w-3 text-amber-400 mr-0.5" />
                    {p.feedback.confidence}/10
                  </span>
                )}
                <a
                  href={p.leetcode_url} target="_blank" rel="noreferrer"
                  data-testid={`topic-problem-open-${p.id}`}
                  className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                >
                  <ExternalLink className="h-3 w-3" /> LeetCode
                </a>
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {/* Personal notes */}
      <GlassCard className="p-6" data-testid="topic-notes">
        <div className="flex items-center gap-2 mb-3">
          <MessageSquare className="h-4 w-4 text-primary" />
          <div className="overline">Personal notes</div>
        </div>
        <Textarea
          value={notes} onChange={(e) => setNotes(e.target.value)} rows={6}
          data-testid="topic-notes-input"
          className="bg-white/[0.03] border-white/10"
          placeholder="Write your own insights, mnemonics, edge cases…"
        />
        <div className="mt-3 flex justify-end">
          <Button
            onClick={saveNotes} disabled={savingNotes}
            data-testid="topic-notes-save"
            className="bg-primary hover:bg-primary/90 btn-primary-glow"
          >
            {savingNotes ? <><Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />Saving…</> : <><Save className="h-3.5 w-3.5 mr-2" />Save notes</>}
          </Button>
        </div>
      </GlassCard>

      {/* Activity */}
      {activity && activity.length > 0 && (
        <GlassCard className="p-6" data-testid="topic-activity">
          <div className="overline mb-4">Activity timeline</div>
          <div className="relative pl-6">
            <span className="absolute left-2 top-1 bottom-1 w-px bg-white/10" />
            {activity.map((e) => (
              <div key={e.id} className="relative py-2.5">
                <span className="absolute -left-[22px] top-3.5 h-2.5 w-2.5 rounded-full bg-primary/70 ring-4 ring-background" />
                <p className="text-sm">{e.title}</p>
                {e.description && <p className="text-xs text-muted-foreground">{e.description}</p>}
                <p className="mt-0.5 text-[10px] font-mono text-muted-foreground">
                  {formatDistanceToNow(parseISO(e.ts), { addSuffix: true })}
                </p>
              </div>
            ))}
          </div>
        </GlassCard>
      )}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <div className="overline mb-1">{label}</div>
      <div className="font-display text-xl font-semibold tracking-tight">{value}</div>
    </div>
  );
}
