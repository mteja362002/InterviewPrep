import React from 'react';
import { Target, GraduationCap, Gauge, Clock, Building2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useMissionContext } from '@/contexts/MissionContextProvider';

/**
 * TodaysMissionBanner (Phase 3D Slice B · §12 UI consistency)
 * -----------------------------------------------------------
 * A SINGLE shared presentation of today's Mission Context, reused by
 * Knowledge Base, Coding Arena, Assessment and Analytics so that Topic,
 * Learning Stage, Difficulty, Estimated Time, Target Companies and Assessment
 * Type are formatted identically everywhere (no duplicated formatting logic).
 *
 * It reads ONLY from the shared MissionContextProvider — it never fetches,
 * infers or computes anything on its own.
 *
 * Props:
 *  - nodeId?: string  → show the mission context for a specific roadmap node.
 *                       If omitted (or not part of today's mission) the banner
 *                       falls back to the first task that carries context.
 *  - variant?: 'full' | 'compact'
 *  - className?: string
 */
function Chip({ icon: Icon, label, value }) {
  if (value === null || value === undefined || value === '') return null;
  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-white/[0.08] bg-white/[0.03] text-xs">
      <Icon className="h-3.5 w-3.5 text-primary/80" />
      <span className="text-muted-foreground">{label}:</span>
      <span className="font-medium text-foreground capitalize">{value}</span>
    </div>
  );
}

export function TodaysMissionBanner({ nodeId, variant = 'full', className }) {
  const { getTaskContext, tasks, isLoading } = useMissionContext();

  if (isLoading) {
    return (
      <div className={cn('h-16 rounded-xl border border-white/[0.06] bg-white/[0.02] animate-pulse', className)} />
    );
  }

  // Resolve the task context: explicit node → any task with context.
  const task = getTaskContext({ nodeId }) || tasks.find((t) => t.mission_context) || null;
  const mc = task?.mission_context || null;
  if (!mc) return null;

  const companies = (mc.target_companies || []).slice(0, 4);
  const stageLabel = mc.learning_stage ? String(mc.learning_stage).replace(/_/g, ' ') : null;
  const assessmentLabel = mc.assessment_type && mc.assessment_type !== 'none'
    ? String(mc.assessment_type).replace(/_/g, ' ')
    : null;

  return (
    <div
      data-testid="todays-mission-banner"
      className={cn(
        'rounded-xl border border-primary/20 bg-gradient-to-br from-primary/[0.06] to-transparent p-4',
        className,
      )}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-primary/80">
          Today&apos;s Mission
        </span>
      </div>
      <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
        <Target className="h-4 w-4 text-primary" />
        <span data-testid="mission-banner-topic">{mc.topic || task.title}</span>
      </h3>
      {variant === 'full' && (
        <div className="mt-3 flex flex-wrap gap-2">
          <Chip icon={GraduationCap} label="Stage" value={stageLabel} />
          <Chip icon={Gauge} label="Difficulty" value={mc.difficulty} />
          <Chip icon={Clock} label="Time" value={mc.estimated_time ? `${mc.estimated_time}m` : null} />
          {assessmentLabel && <Chip icon={Target} label="Assessment" value={assessmentLabel} />}
          {companies.length > 0 && (
            <Chip icon={Building2} label="Companies" value={companies.join(', ')} />
          )}
        </div>
      )}
    </div>
  );
}

export default TodaysMissionBanner;
