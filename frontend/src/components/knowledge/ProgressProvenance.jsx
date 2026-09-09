/** The API owns all percentages. Never infer a baseline from topic mastery. */
export function ProgressProvenance({ progress = {}, details = false }) {
  const legacy = progress.legacy_progress;
  return (
    <div className="text-xs text-muted-foreground space-y-1" data-testid="progress-provenance">
      {progress.onboarding_baseline != null && (
        <p>Onboarding Baseline: {progress.onboarding_baseline}% · declared subject knowledge</p>
      )}
      {legacy && (
        <p>Unverified Legacy Progress: {legacy.mastery_percentage}% · excluded from actual progress</p>
      )}
      {details && legacy && (
        <details className="pt-2">
          <summary className="cursor-pointer">Inspect preserved historical values</summary>
          <pre className="mt-2 whitespace-pre-wrap break-words text-[11px]">
            {JSON.stringify(legacy.stored_fields || legacy, null, 2)}
          </pre>
          <p>Recorded dates and attempts do not establish the source of historical mastery.</p>
        </details>
      )}
    </div>
  );
}
