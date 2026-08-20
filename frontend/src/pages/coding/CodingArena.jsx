import { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import { formatDistanceToNow, parseISO } from 'date-fns';
import {
  Code2, ExternalLink, Plus, Loader2, CheckCircle2, Clock,
  Sparkles, Zap, MessageSquare, X, Star, Search,
} from 'lucide-react';
import { GlassCard } from '@/components/common/GlassCard';
import { EmptyState } from '@/components/common/EmptyState';
import { codingArenaService, leetcodeCatalogService } from '@/services/mission.service';
import { formatApiError } from '@/utils/formatApiError';
import { Button } from '@/components/ui/button';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { cn } from '@/lib/utils';
import { useMissionContext } from '@/contexts/MissionContextProvider';
import { TodaysMissionBanner } from '@/components/mission/TodaysMissionBanner';

function difficultyChip(d) {
  const cls = d === 'easy'   ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300'
    : d === 'hard'   ? 'border-rose-400/30 bg-rose-400/10 text-rose-300'
    :                  'border-amber-400/30 bg-amber-400/10 text-amber-300';
  return <span className={cn('capitalize text-[11px] font-mono uppercase tracking-wider border rounded-md px-1.5 py-0.5', cls)}>{d}</span>;
}

function statusChip(s) {
  const cls = s === 'solved'    ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300'
    : s === 'attempted' ? 'border-amber-400/30 bg-amber-400/10 text-amber-300'
    :                     'border-white/10 bg-white/[0.03] text-muted-foreground';
  return <span className={cn('capitalize text-[10px] font-mono uppercase tracking-wider border rounded-full px-2 py-0.5', cls)}>{s}</span>;
}

export default function CodingArena() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [feedbackFor, setFeedbackFor] = useState(null);

  // LeetCode Catalog manual search (by number, exact title, or fuzzy title)
  const [searchInput, setSearchInput] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchResult, setSearchResult] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [searchError, setSearchError] = useState('');

  // Shared Mission Context — used to sync progress back to Mission Control.
  const { refresh: refreshMission } = useMissionContext();

  const load = useCallback(async () => {
    try {
      const d = await codingArenaService.get();
      setData(d);
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const onPracticeMore = async () => {
    if (!data?.primary_pattern) {
      toast.error("Today's mission doesn't include a DSA pattern to extend.");
      return;
    }
    setBusy(true);
    try {
      const r = await codingArenaService.practiceMore(data.primary_pattern);
      toast.success(`Added: ${r.problem.title}`);
      await load();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  const onSearchProblem = async (e) => {
    e?.preventDefault();
    const raw = searchInput.trim();
    const digits = raw.replace(/^#/, '').replace(/^lc-/i, '');
    if (!raw) {
      setSearchError('Enter a LeetCode problem number or title.');
      return;
    }
    setSearching(true);
    setSearchError('');
    setSearchResult(null);
    setSearchResults([]);
    try {
      if (/^\d+$/.test(digits)) {
        // Numeric search — unchanged exact-id lookup.
        const problem = await leetcodeCatalogService.getById(digits);
        setSearchResult(problem);
      } else {
        // Title search — exact / partial / fuzzy, ranked results.
        const results = await leetcodeCatalogService.search(raw);
        if (!results || results.length === 0) {
          setSearchError(`No problems found matching "${raw}".`);
        } else if (results.length === 1) {
          setSearchResult(results[0]);
        } else {
          setSearchResults(results);
        }
      }
    } catch (err) {
      if (err?.response?.status === 404) {
        setSearchError(`No problem found with ID #${digits}.`);
      } else {
        setSearchError(formatApiError(err));
        toast.error(formatApiError(err));
      }
    } finally {
      setSearching(false);
    }
  };

  const onStartManualPractice = async (problem) => {
    try {
      const assignment = await codingArenaService.startManualPractice(problem.leetcode_id);
      setFeedbackFor(assignment);
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  if (loading || !data) {
    return (
      <div className="py-24 flex flex-col items-center gap-3 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span className="overline">Loading arena</span>
      </div>
    );
  }

  const { mission, primary_pattern, primary_pattern_label, assignments, history } = data;
  const solvedCount = assignments.filter((a) => a.status === 'solved').length;

  return (
    <div className="space-y-6" data-testid="coding-arena-root">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <div className="overline mb-2">Coding Arena</div>
          <h1 className="font-display text-3xl sm:text-4xl font-semibold tracking-tight">
            Today's pattern · <span className="text-primary">{primary_pattern_label || '—'}</span>
          </h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            {primary_pattern
              ? "Solve, log confidence, and let the engine adapt tomorrow's plan."
              : "Today's mission focuses on a non-coding topic. Come back tomorrow — or use Practice More on any past pattern."}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="text-xs font-mono text-muted-foreground">
            {solvedCount} / {assignments.length} solved today
          </div>
          <Button
            onClick={onPracticeMore}
            disabled={busy || !primary_pattern}
            data-testid="arena-practice-more-button"
            className="bg-primary hover:bg-primary/90 btn-primary-glow"
          >
            {busy ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Adding…</>
              : <><Plus className="h-4 w-4 mr-2" />Practice More</>}
          </Button>
        </div>
      </div>

      {/* Today's Mission Context — shared single source of truth (§12). */}
      <TodaysMissionBanner />

      {/* Explicit empty state (§11): never substitute another topic. */}
      {primary_pattern && assignments.length === 0 && (
        <GlassCard className="p-6 text-center" data-testid="arena-empty-state">
          <p className="text-sm text-muted-foreground">
            No representative problems available for this learning node.
          </p>
        </GlassCard>
      )}

      {/* LeetCode search by problem ID */}
      <GlassCard className="p-5">
        <form onSubmit={onSearchProblem} className="flex flex-col sm:flex-row gap-2.5">
          <div className="flex-1 flex items-center gap-2 h-10 px-3 rounded-lg border border-white/10 bg-white/[0.03]">
            <Search className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
            <Input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search by LeetCode number or title, e.g. 53 or Maximum Subarray"
              data-testid="arena-search-input"
              className="border-0 bg-transparent p-0 h-auto focus-visible:ring-0 focus-visible:ring-offset-0"
            />
          </div>
          <Button
            type="submit"
            disabled={searching}
            data-testid="arena-search-button"
            className="bg-primary hover:bg-primary/90 btn-primary-glow"
          >
            {searching ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Searching…</> : <><Search className="h-4 w-4 mr-2" />Search</>}
          </Button>
        </form>

        {searchError && (
          <p data-testid="arena-search-error" className="mt-3 text-sm text-rose-300">
            {searchError}
          </p>
        )}

        {searchResult && (
          <div data-testid="arena-search-result" className="mt-4 rounded-xl border border-white/[0.08] bg-white/[0.02] p-4">
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className="text-[11px] font-mono text-muted-foreground">#{searchResult.leetcode_id}</span>
              {difficultyChip(searchResult.difficulty)}
              {(searchResult.topic_tags || []).map((t) => (
                <span key={t} className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground border border-white/10 rounded-full px-2 py-0.5">
                  {t.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
            <h3 className="font-display text-lg font-medium">{searchResult.title}</h3>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <a
                href={searchResult.url} target="_blank" rel="noreferrer"
                data-testid="arena-search-result-open"
                className="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg border border-white/10 bg-white/[0.03] hover:bg-white/[0.06] text-xs font-medium transition-colors"
              >
                <ExternalLink className="h-3.5 w-3.5" /> Open on LeetCode
              </a>
              <button
                onClick={() => onStartManualPractice(searchResult)}
                data-testid="arena-search-complete-practice"
                className="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg border border-primary/40 bg-primary/10 hover:bg-primary/15 text-primary text-xs font-medium transition-colors"
              >
                <MessageSquare className="h-3.5 w-3.5" /> Complete Practice
              </button>
            </div>
          </div>
        )}

        {searchResults.length > 0 && (
          <div data-testid="arena-search-results-list" className="mt-4 space-y-2">
            {searchResults.map((p) => (
              <div
                key={p.leetcode_id}
                data-testid={`arena-search-result-${p.leetcode_id}`}
                className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 flex flex-col sm:flex-row sm:items-center gap-3"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-[11px] font-mono text-muted-foreground">#{p.leetcode_id}</span>
                    {difficultyChip(p.difficulty)}
                    {(p.topic_tags || []).slice(0, 3).map((t) => (
                      <span key={t} className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground border border-white/10 rounded-full px-2 py-0.5">
                        {t.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                  <h4 className="font-display text-base font-medium truncate">{p.title}</h4>
                </div>
                <div className="flex flex-wrap gap-2">
                  <a
                    href={p.url} target="_blank" rel="noreferrer"
                    data-testid={`arena-search-result-open-${p.leetcode_id}`}
                    className="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg border border-white/10 bg-white/[0.03] hover:bg-white/[0.06] text-xs font-medium transition-colors"
                  >
                    <ExternalLink className="h-3.5 w-3.5" /> Open
                  </a>
                  <button
                    onClick={() => onStartManualPractice(p)}
                    data-testid={`arena-search-complete-practice-${p.leetcode_id}`}
                    className="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg border border-primary/40 bg-primary/10 hover:bg-primary/15 text-primary text-xs font-medium transition-colors"
                  >
                    <MessageSquare className="h-3.5 w-3.5" /> Complete Practice
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </GlassCard>

      {/* Mission recap */}
      <GlassCard className="p-5 relative overflow-hidden">
        <div className="absolute -top-16 -right-16 h-40 w-40 rounded-full bg-primary/10 blur-3xl" />
        <div className="flex items-center gap-4">
          <span className="h-10 w-10 rounded-lg bg-primary/15 border border-primary/30 flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-primary" />
          </span>
          <div className="flex-1 min-w-0">
            <div className="overline mb-0.5">Mission</div>
            <p className="text-sm font-medium truncate">{mission.title} · <span className="text-muted-foreground">{mission.focus_area}</span></p>
          </div>
          <div className="hidden sm:flex items-center gap-3 text-xs font-mono text-muted-foreground">
            <span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" /> {Math.round(mission.estimated_duration_minutes / 60 * 10) / 10}h</span>
            {difficultyChip(mission.difficulty)}
          </div>
        </div>
      </GlassCard>

      {/* Assignments */}
      {assignments.length === 0 ? (
        <GlassCard className="p-8">
          <EmptyState
            icon={Code2}
            title="No coding problems assigned today"
            description="Today's mission focuses on non-DSA topics. Use Practice More to pull problems from a past pattern."
          />
        </GlassCard>
      ) : (
        <div className="space-y-3">
          {assignments.map((a) => (
            <GlassCard
              key={a.id}
              data-testid={`arena-problem-${a.id}`}
              className={cn(
                'p-5 flex flex-col sm:flex-row sm:items-center gap-4 transition-colors',
                a.status === 'solved' && 'border-emerald-400/25 bg-emerald-400/[0.04]',
              )}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                  {statusChip(a.status)}
                  {difficultyChip(a.problem.difficulty)}
                  <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground border border-white/10 rounded-full px-2 py-0.5">
                    {a.pattern.replace('_', ' ')}
                  </span>
                  <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                    <Clock className="h-3 w-3" /> {a.problem.estimated_minutes}m
                  </span>
                  {a.source === 'practice_more' && (
                    <span className="text-[10px] font-mono uppercase tracking-wider text-secondary border border-secondary/30 rounded-full px-2 py-0.5">
                      + Practice
                    </span>
                  )}
                </div>
                <h3 className="font-display text-lg font-medium">{a.problem.title}</h3>
                {a.notes && (
                  <p className="mt-1 text-xs text-muted-foreground italic line-clamp-2">"{a.notes}"</p>
                )}
                {a.feedback && (
                  <div className="mt-2 flex items-center gap-3 text-[11px] font-mono text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Star className="h-3 w-3 text-amber-400" /> Confidence {a.feedback.confidence}/10
                    </span>
                    <span>· {a.feedback.time_taken_minutes}m taken</span>
                    <span>· {a.feedback.solved_status.replace(/_/g, ' ')}</span>
                  </div>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <a
                  href={a.problem.leetcode_url} target="_blank" rel="noreferrer"
                  data-testid={`arena-open-${a.id}`}
                  className="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg border border-white/10 bg-white/[0.03] hover:bg-white/[0.06] text-xs font-medium transition-colors"
                >
                  <ExternalLink className="h-3.5 w-3.5" /> Open on LeetCode
                </a>
                <button
                  onClick={() => setFeedbackFor(a)}
                  data-testid={`arena-feedback-${a.id}`}
                  className={cn(
                    'inline-flex items-center gap-1.5 h-9 px-3 rounded-lg border text-xs font-medium transition-colors',
                    a.feedback
                      ? 'border-white/10 bg-white/[0.03] hover:bg-white/[0.06]'
                      : 'border-primary/40 bg-primary/10 hover:bg-primary/15 text-primary',
                  )}
                >
                  {a.feedback ? <><CheckCircle2 className="h-3.5 w-3.5" />Update feedback</> : <><MessageSquare className="h-3.5 w-3.5" />Log feedback</>}
                </button>
              </div>
            </GlassCard>
          ))}
        </div>
      )}

      {/* History */}
      {history.length > 0 && (
        <GlassCard className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="h-4 w-4 text-muted-foreground" />
            <div className="overline">Recent problems</div>
          </div>
          <div className="divide-y divide-white/[0.05]">
            {history.map((h) => (
              <div key={h.id} className="py-3 flex items-center gap-3 text-sm">
                {statusChip(h.status)}
                <span className="flex-1 truncate">{h.problem.title}</span>
                <span className="text-[11px] font-mono text-muted-foreground">
                  {h.pattern.replace('_', ' ')}
                </span>
                <span className="text-[11px] font-mono text-muted-foreground whitespace-nowrap">
                  {h.completed_at ? formatDistanceToNow(parseISO(h.completed_at), { addSuffix: true }) : '—'}
                </span>
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {/* Feedback modal */}
      <FeedbackDialog
        assignment={feedbackFor}
        open={!!feedbackFor}
        onClose={() => setFeedbackFor(null)}
        onSubmitted={async () => { setFeedbackFor(null); await load(); refreshMission(); }}
      />
    </div>
  );
}

function FeedbackDialog({ assignment, open, onClose, onSubmitted }) {
  const [difficulty, setDifficulty] = useState('medium');
  const [solved, setSolved] = useState('without_hints');
  const [confidence, setConfidence] = useState([7]);
  const [time, setTime] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (assignment) {
      const f = assignment.feedback;
      setDifficulty(f?.difficulty_rating || assignment.problem?.difficulty || 'medium');
      setSolved(f?.solved_status || 'without_hints');
      setConfidence([f?.confidence ?? 7]);
      setTime(f?.time_taken_minutes ? String(f.time_taken_minutes) : String(assignment.problem?.estimated_minutes ?? 20));
      setNotes(f?.notes || assignment.notes || '');
    }
  }, [assignment]);

  const submit = async () => {
    if (!assignment) return;
    const mins = parseInt(time, 10);
    if (Number.isNaN(mins) || mins < 0) {
      toast.error('Enter a valid time in minutes.');
      return;
    }
    setSubmitting(true);
    try {
      await codingArenaService.submitFeedback(assignment.id, {
        difficulty_rating: difficulty,
        solved_status: solved,
        confidence: confidence[0],
        time_taken_minutes: mins,
        notes: notes.trim() || null,
      });
      toast.success('Feedback logged. The engine will adapt.');
      onSubmitted();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        data-testid="arena-feedback-dialog"
        className="bg-[hsl(var(--surface))]/95 border-white/10 backdrop-blur-xl max-w-lg"
      >
        <DialogHeader>
          <DialogTitle className="font-display">
            Log feedback · <span className="text-primary">{assignment?.problem?.title}</span>
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-5 py-2">
          {/* Difficulty */}
          <div>
            <Label className="mb-2 block text-xs font-mono uppercase tracking-wider text-muted-foreground">
              How hard was it?
            </Label>
            <RadioGroup value={difficulty} onValueChange={setDifficulty} className="grid grid-cols-3 gap-2">
              {['easy', 'medium', 'hard'].map((d) => (
                <label key={d} className={cn(
                  'flex items-center gap-2 rounded-lg border px-3 py-2 cursor-pointer capitalize text-sm',
                  difficulty === d ? 'border-primary/50 bg-primary/10' : 'border-white/[0.08] bg-white/[0.02]',
                )}>
                  <RadioGroupItem value={d} data-testid={`feedback-difficulty-${d}`} />
                  {d}
                </label>
              ))}
            </RadioGroup>
          </div>

          {/* Solved status */}
          <div>
            <Label className="mb-2 block text-xs font-mono uppercase tracking-wider text-muted-foreground">Solved?</Label>
            <RadioGroup value={solved} onValueChange={setSolved} className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {[
                { id: 'without_hints',  label: 'Without hints' },
                { id: 'one_hint',       label: 'One hint' },
                { id: 'multi_hints',    label: 'Multiple hints' },
                { id: 'could_not_solve',label: 'Could not solve' },
              ].map((opt) => (
                <label key={opt.id} className={cn(
                  'flex items-center gap-2 rounded-lg border px-3 py-2 cursor-pointer text-sm',
                  solved === opt.id ? 'border-primary/50 bg-primary/10' : 'border-white/[0.08] bg-white/[0.02]',
                )}>
                  <RadioGroupItem value={opt.id} data-testid={`feedback-solved-${opt.id}`} />
                  {opt.label}
                </label>
              ))}
            </RadioGroup>
          </div>

          {/* Confidence */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <Label className="text-xs font-mono uppercase tracking-wider text-muted-foreground">Confidence</Label>
              <span className="font-mono text-sm text-primary">{confidence[0]}/10</span>
            </div>
            <Slider
              value={confidence} onValueChange={setConfidence}
              min={1} max={10} step={1}
              data-testid="feedback-confidence-slider"
            />
          </div>

          {/* Time */}
          <div>
            <Label className="mb-1.5 block text-xs font-mono uppercase tracking-wider text-muted-foreground">
              Time taken (minutes)
            </Label>
            <Input
              type="number" min={0} max={600}
              value={time} onChange={(e) => setTime(e.target.value)}
              data-testid="feedback-time-input"
              className="bg-white/[0.03] border-white/10"
            />
          </div>

          {/* Notes */}
          <div>
            <Label className="mb-1.5 block text-xs font-mono uppercase tracking-wider text-muted-foreground">
              Notes (optional)
            </Label>
            <Textarea
              value={notes} onChange={(e) => setNotes(e.target.value)} rows={3}
              placeholder="What tripped you up? What did you learn?"
              data-testid="feedback-notes-input"
              className="bg-white/[0.03] border-white/10"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose} className="text-muted-foreground">
            <X className="h-4 w-4 mr-1.5" />Cancel
          </Button>
          <Button
            onClick={submit} disabled={submitting}
            data-testid="feedback-submit-button"
            className="bg-primary hover:bg-primary/90 btn-primary-glow"
          >
            {submitting ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Saving…</> : 'Save feedback'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
