import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import {
  ClipboardCheck, Loader2, ArrowLeft, CheckCircle2, ExternalLink,
  TrendingUp, TrendingDown, Minus, RefreshCcw,
} from 'lucide-react';
import { GlassCard } from '@/components/common/GlassCard';
import { cn } from '@/lib/utils';
import {
  assessmentService, missionService, learnerIntelligenceService,
} from '@/services/mission.service';
import { formatApiError } from '@/utils/formatApiError';
import { useMissionContext } from '@/contexts/MissionContextProvider';
import { TodaysMissionBanner } from '@/components/mission/TodaysMissionBanner';

function difficultyChipClass(d) {
  if (d === 'easy') return 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300';
  if (d === 'hard') return 'border-rose-400/30 bg-rose-400/10 text-rose-300';
  return 'border-amber-400/30 bg-amber-400/10 text-amber-300';
}

const COMPLEXITY_OPTIONS = ['O(1)', 'O(log n)', 'O(n)', 'O(n log n)', 'O(n^2)'];

export default function Assessment() {
  const { missionId } = useParams();
  const navigate = useNavigate();

  const [phase, setPhase] = useState('loading'); // loading | attempt | submitting | result
  const [assessment, setAssessment] = useState(null);
  const [mission, setMission] = useState(null);
  const [result, setResult] = useState(null);
  const [liUpdate, setLiUpdate] = useState(null);

  // Shared Mission Context — pre-start info (objectives) + progress sync.
  const { refresh: refreshMission, tasks: mcTasks } = useMissionContext();
  const missionCtx = (mcTasks || []).find((t) => t.mission_context)?.mission_context || null;
  const missionObjectives = missionCtx?.learning_objectives || [];

  // Structured coding-attempt form (matches backend SubmitAssessmentRequest).
  const [form, setForm] = useState({
    solved: true,
    passed_tests: 10,
    total_tests: 10,
    edge_cases_passed: 3,
    edge_cases_total: 3,
    claimed_time_complexity: 'O(n)',
    explanation: '',
    code: '',
  });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [m, gen] = await Promise.all([
          missionService.getToday().catch(() => null),
          assessmentService.generateForMission(missionId),
        ]);
        if (cancelled) return;
        setMission(m);
        setAssessment(gen.assessment);
        setPhase('attempt');
      } catch (err) {
        if (cancelled) return;
        toast.error(formatApiError(err));
        // §11 — explicit empty state; never silently bounce or substitute.
        setPhase('unavailable');
      }
    })();
    return () => { cancelled = true; };
  }, [missionId, navigate]);

  const update = (patch) => setForm((f) => ({ ...f, ...patch }));

  const onSubmit = async () => {
    if (!assessment) return;
    setPhase('submitting');
    try {
      // Deterministic lifecycle: start → submit → evaluate (reuses the engine).
      if (assessment.status === 'pending') {
        await assessmentService.start(assessment.id);
      }
      await assessmentService.submit(assessment.id, {
        solved: form.solved,
        passed_tests: Number(form.passed_tests) || 0,
        total_tests: Number(form.total_tests) || 0,
        edge_cases_passed: Number(form.edge_cases_passed) || 0,
        edge_cases_total: Number(form.edge_cases_total) || 0,
        claimed_time_complexity: form.claimed_time_complexity,
        explanation: form.explanation,
        code: form.code,
      });
      const evaluated = await assessmentService.evaluate(assessment.id);
      // Assessment → Learner Intelligence already ran on evaluate (Phase 3B);
      // fetch the newest update to surface confidence / mastery change.
      const updates = await learnerIntelligenceService.updates(1).catch(() => []);
      // Finalize the mission (mission only orchestrates; it never evaluates).
      await missionService.completeMission(missionId).catch((err) => {
        // Non-fatal: assessment is recorded even if completion races.
        toast.error(formatApiError(err));
      });
      setResult(evaluated);
      setLiUpdate(Array.isArray(updates) && updates.length ? updates[0] : null);
      setPhase('result');
      refreshMission();
    } catch (err) {
      toast.error(formatApiError(err));
      setPhase('attempt');
    }
  };

  if (phase === 'loading') {
    return (
      <div className="py-24 flex flex-col items-center gap-3 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span className="overline">Preparing assessment</span>
      </div>
    );
  }

  if (phase === 'unavailable') {
    return (
      <div className="max-w-2xl mx-auto py-16">
        <button
          onClick={() => navigate('/app/mission-control')}
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Mission Control
        </button>
        <GlassCard className="p-8 text-center mt-4" data-testid="assessment-unavailable">
          <p className="text-sm text-muted-foreground">
            Assessment is currently unavailable for this topic.
          </p>
        </GlassCard>
      </div>
    );
  }

  const q = assessment?.question || {};

  // ---- Result view ------------------------------------------------------- //
  if (phase === 'result' && result) {
    const r = result.result || {};
    const fb = result.feedback || {};
    const rec = result.recommendation || {};
    const confDelta = liUpdate?.confidence_delta ?? 0;
    const masteryDelta = liUpdate?.mastery_delta ?? 0;
    const DeltaIcon = (v) => (v > 0 ? TrendingUp : v < 0 ? TrendingDown : Minus);
    const deltaClass = (v) => (v > 0 ? 'text-emerald-300' : v < 0 ? 'text-rose-300' : 'text-muted-foreground');

    return (
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center gap-2 text-emerald-300">
          <CheckCircle2 className="h-5 w-5" />
          <span className="font-display text-2xl font-semibold">Assessment Complete</span>
        </div>

        <GlassCard className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="overline mb-1">Score</div>
              <div className="font-display text-4xl font-semibold">
                {Math.round(r.overall_score ?? 0)}<span className="text-lg text-muted-foreground">/100</span>
              </div>
            </div>
            <span className={cn('px-2.5 py-1 rounded-md text-sm border capitalize',
              r.verdict === 'correct' ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300'
                : r.verdict === 'incorrect' ? 'border-rose-400/30 bg-rose-400/10 text-rose-300'
                  : 'border-amber-400/30 bg-amber-400/10 text-amber-300')}>
              {(r.verdict || '').replace('_', ' ') || '—'}
            </span>
          </div>

          <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="rounded-lg border border-white/[0.08] bg-white/[0.02] p-4">
              <div className="overline mb-2">Strengths</div>
              {fb.strengths?.length ? (
                <ul className="text-sm space-y-1">
                  {fb.strengths.map((s, i) => <li key={i} className="text-emerald-300">✓ {s}</li>)}
                </ul>
              ) : <p className="text-sm text-muted-foreground">—</p>}
            </div>
            <div className="rounded-lg border border-white/[0.08] bg-white/[0.02] p-4">
              <div className="overline mb-2">Weaknesses</div>
              {fb.weaknesses?.length ? (
                <ul className="text-sm space-y-1">
                  {fb.weaknesses.map((s, i) => <li key={i} className="text-rose-300">• {s}</li>)}
                </ul>
              ) : <p className="text-sm text-muted-foreground">—</p>}
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="rounded-lg border border-white/[0.08] bg-white/[0.02] p-4">
              <div className="overline mb-1">Confidence change</div>
              <div className={cn('flex items-center gap-2 text-lg font-medium', deltaClass(confDelta))}>
                {(() => { const I = DeltaIcon(confDelta); return <I className="h-4 w-4" />; })()}
                {confDelta > 0 ? '+' : ''}{confDelta.toFixed(2)}
              </div>
            </div>
            <div className="rounded-lg border border-white/[0.08] bg-white/[0.02] p-4">
              <div className="overline mb-1">Mastery change</div>
              <div className={cn('flex items-center gap-2 text-lg font-medium', deltaClass(masteryDelta))}>
                {(() => { const I = DeltaIcon(masteryDelta); return <I className="h-4 w-4" />; })()}
                {masteryDelta > 0 ? '+' : ''}{masteryDelta.toFixed(1)}%
              </div>
            </div>
          </div>

          {(fb.revision_recommendation || rec.reason) && (
            <div className="mt-4 rounded-lg border border-amber-400/25 bg-amber-400/[0.06] px-4 py-3 flex items-start gap-2.5">
              <RefreshCcw className="h-4 w-4 mt-0.5 text-amber-300 shrink-0" />
              <div>
                <div className="overline text-amber-300 mb-0.5">Recommended revision</div>
                <p className="text-sm">{fb.revision_recommendation || rec.reason}</p>
              </div>
            </div>
          )}

          <div className="mt-6 flex items-center gap-2 text-sm text-emerald-300">
            <CheckCircle2 className="h-4 w-4" />
            Mission Completed — tomorrow's plan adapts to this evidence.
          </div>
        </GlassCard>

        <button
          onClick={() => navigate('/app/mission-control')}
          data-testid="assessment-return-button"
          className="h-10 px-4 rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-medium inline-flex items-center gap-2 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" /> Return to Mission Control
        </button>
      </div>
    );
  }

  // ---- Attempt view ------------------------------------------------------ //
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <button
        onClick={() => navigate('/app/mission-control')}
        className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" /> Back to Mission Control
      </button>

      {/* Pre-start Mission Context (§4): topic, type, difficulty, time, companies. */}
      <TodaysMissionBanner className="mb-4" />
      {missionObjectives.length > 0 && (
        <GlassCard className="p-4 mb-4" data-testid="assessment-objectives">
          <div className="overline mb-2">Learning Objectives</div>
          <ul className="text-sm space-y-1 text-muted-foreground">
            {missionObjectives.map((o, i) => <li key={i}>• {o}</li>)}
          </ul>
        </GlassCard>
      )}

      <GlassCard className="p-6">
        <div className="flex items-center gap-2.5 mb-4">
          <span className="h-8 w-8 rounded-lg border border-white/10 bg-white/[0.03] flex items-center justify-center">
            <ClipboardCheck className="h-4 w-4 text-primary" />
          </span>
          <div>
            <div className="overline">Assessment · {mission?.title || 'Today\u2019s Mission'}</div>
            <h1 className="font-display text-xl font-semibold">{q.title || 'Coding Assessment'}</h1>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs">
          {q.pattern && <span className="px-2 py-0.5 rounded-md border border-white/10 bg-white/[0.03] capitalize">{String(q.pattern).replace(/_/g, ' ')}</span>}
          {q.difficulty && <span className={cn('px-2 py-0.5 rounded-md border capitalize', difficultyChipClass(q.difficulty))}>{q.difficulty}</span>}
          {q.expected_time_complexity && <span className="px-2 py-0.5 rounded-md border border-white/10 bg-white/[0.03] font-mono">target {q.expected_time_complexity}</span>}
        </div>

        <div className="mt-4 rounded-lg border border-white/[0.08] bg-white/[0.02] p-4">
          <div className="overline mb-1">Question 1 of 1</div>
          <p className="text-sm">{q.prompt || 'Solve the linked problem, then report your result below.'}</p>
          {q.external_url && (
            <a href={q.external_url} target="_blank" rel="noreferrer"
              className="mt-3 inline-flex items-center gap-1.5 text-sm text-primary hover:underline">
              Open problem <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
        </div>

        {/* Structured self-report (deterministic evaluation input) */}
        <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.solved}
              onChange={(e) => update({ solved: e.target.checked })}
              className="h-4 w-4 accent-[hsl(var(--primary))]" data-testid="assessment-solved" />
            I solved this problem
          </label>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground w-32">Tests passed</span>
            <input type="number" min="0" value={form.passed_tests}
              onChange={(e) => update({ passed_tests: e.target.value })}
              className="w-16 rounded-md border border-white/10 bg-white/[0.03] px-2 py-1 text-sm" />
            <span className="text-muted-foreground">/</span>
            <input type="number" min="1" value={form.total_tests}
              onChange={(e) => update({ total_tests: e.target.value })}
              className="w-16 rounded-md border border-white/10 bg-white/[0.03] px-2 py-1 text-sm" />
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground w-32">Edge cases</span>
            <input type="number" min="0" value={form.edge_cases_passed}
              onChange={(e) => update({ edge_cases_passed: e.target.value })}
              className="w-16 rounded-md border border-white/10 bg-white/[0.03] px-2 py-1 text-sm" />
            <span className="text-muted-foreground">/</span>
            <input type="number" min="0" value={form.edge_cases_total}
              onChange={(e) => update({ edge_cases_total: e.target.value })}
              className="w-16 rounded-md border border-white/10 bg-white/[0.03] px-2 py-1 text-sm" />
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground w-32">Time complexity</span>
            <select value={form.claimed_time_complexity}
              onChange={(e) => update({ claimed_time_complexity: e.target.value })}
              className="rounded-md border border-white/10 bg-white/[0.03] px-2 py-1 text-sm">
              {COMPLEXITY_OPTIONS.map((c) => <option key={c} value={c} className="bg-background">{c}</option>)}
            </select>
          </div>
        </div>

        <div className="mt-4">
          <div className="overline mb-1">Explain your approach</div>
          <textarea rows={4} value={form.explanation}
            onChange={(e) => update({ explanation: e.target.value })}
            placeholder="Describe your approach and reasoning…"
            data-testid="assessment-explanation"
            className="w-full rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary/40" />
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={onSubmit}
            disabled={phase === 'submitting'}
            data-testid="assessment-submit-button"
            className="h-10 px-5 rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-medium inline-flex items-center gap-2 disabled:opacity-60 transition-colors"
          >
            {phase === 'submitting'
              ? <><Loader2 className="h-4 w-4 animate-spin" /> Submitting…</>
              : <>Submit Assessment</>}
          </button>
        </div>
      </GlassCard>
    </div>
  );
}
