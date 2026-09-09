import { Link } from 'react-router-dom';
import { Clock, ChevronRight, Bookmark, Star } from 'lucide-react';
import { cn } from '@/lib/utils';
import { StatusBadge } from '@/components/progress/StatusBadge';
import { NodeActions } from '@/components/progress/NodeActions';
import { EmptyState } from '@/components/common/EmptyState';
import { formatDistanceToNow, parseISO } from 'date-fns';

/**
 * KnowledgeCardList (RC1.3.4)
 *
 * Flat card renderer used by every non-tree view of the Knowledge
 * Base workspace (Bookmarks / Favorites / Weak / Revision Due /
 * Recently Viewed / Continue Learning).
 *
 * A "row" is a plain object with — at minimum — { id, label, track,
 * progress, meta? }. `meta` is a short freeform string a caller can
 * pass to show view-specific context (e.g. "Due 3 days ago" for the
 * Revision Due view; "Last opened 2h ago" for Recently Viewed).
 *
 * Optimistic-updates guarantee: rows read `progress.bookmarked` and
 * `progress.favorite` from the same tree cache the mutations write
 * to, so a bookmark toggle updates every visible list, the deep
 * page, and Mission Control together — no local shadow state, no
 * refetch flicker.
 */
function safeFormatRelative(iso) {
  if (!iso) return null;
  try {
    return formatDistanceToNow(parseISO(iso), { addSuffix: true });
  } catch {
    return null;
  }
}

function KnowledgeCard({ row }) {
  const { id, label, track, progress = {}, meta, metaAccent } = row;
  const status = progress.status || 'not_started';
  const mastery = Math.round(progress.mastery_percentage || 0);
  const confidence = progress.confidence;
  const bucket = progress.revision_bucket || 'green';

  const bucketDot = {
    green: 'bg-emerald-400',
    yellow: 'bg-amber-400',
    red: 'bg-rose-400',
  }[bucket] || 'bg-white/20';

  return (
    <div
      className="group flex items-stretch gap-2"
      data-testid={`kb-card-${id}`}
    >
      <Link
        to={`/app/knowledge-base/nodes/${id}`}
        className="flex-1 min-w-0 rounded-xl border border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.05] hover:border-white/[0.12] px-4 py-3.5 transition-colors flex items-center gap-3"
      >
        <span className={cn('h-2 w-2 rounded-full shrink-0', bucketDot)} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className="text-sm font-medium text-foreground truncate max-w-full"
              title={label}
            >
              {label}
            </span>
            <StatusBadge status={status} />
          </div>
          <div className="mt-1 flex items-center gap-3 text-[11px] text-muted-foreground font-mono">
            {track && (
              <span className="uppercase tracking-wider truncate" title={track.label || track.id}>
                {track.label || track.id}
              </span>
            )}
            {progress.bookmarked && (
              <span className="inline-flex items-center gap-1 text-primary" title="Bookmarked">
                <Bookmark className="h-2.5 w-2.5 fill-current" /> saved
              </span>
            )}
            {progress.favorite && (
              <span className="inline-flex items-center gap-1 text-amber-300" title="Favorite">
                <Star className="h-2.5 w-2.5 fill-current" /> starred
              </span>
            )}
            {typeof confidence === 'number' && confidence > 0 && (
              <span>conf {confidence.toFixed(1)}/10</span>
            )}
            <span>{mastery}% actual mastery</span>
            {progress.legacy_progress && <span>Unverified legacy: {progress.legacy_progress.mastery_percentage}%</span>}
            {meta && (
              <span
                className={cn(
                  'inline-flex items-center gap-1 truncate max-w-[220px]',
                  metaAccent === 'rose' && 'text-rose-300',
                  metaAccent === 'amber' && 'text-amber-300',
                  metaAccent === 'emerald' && 'text-emerald-300',
                )}
                title={meta}
              >
                <Clock className="h-2.5 w-2.5" />
                {meta}
              </span>
            )}
          </div>
        </div>
        <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground shrink-0 transition-colors" />
      </Link>
      <NodeActions
        nodeId={id}
        bookmarked={progress.bookmarked}
        favorite={progress.favorite}
      />
    </div>
  );
}

/**
 * @param {object} props
 * @param {Array} props.rows      — {id,label,track,progress,meta?,metaAccent?}
 * @param {string} props.emptyTitle
 * @param {string} props.emptyBody
 * @param {Array}  [props.groups] — optional grouping. Each group is
 *   { id, label, rows: [...] }. When provided, `rows` is ignored and
 *   sections render one after another. Used by Revision Due to
 *   segment Overdue / Today / Tomorrow / Upcoming.
 */
export function KnowledgeCardList({ rows = [], groups = null, emptyTitle, emptyBody }) {
  if (groups) {
    const allEmpty = groups.every((g) => (g.rows || []).length === 0);
    if (allEmpty) {
      return <EmptyState title={emptyTitle} description={emptyBody} />;
    }
    return (
      <div className="space-y-6" data-testid="kb-card-groups">
        {groups.map((g) => (
          (g.rows || []).length > 0 && (
            <section key={g.id} data-testid={`kb-card-group-${g.id}`} className="space-y-2">
              <div className="flex items-baseline justify-between">
                <div className="overline">{g.label}</div>
                <div className="text-[11px] font-mono text-muted-foreground">{g.rows.length}</div>
              </div>
              <div className="space-y-2">
                {g.rows.map((r) => <KnowledgeCard key={r.id} row={r} />)}
              </div>
            </section>
          )
        ))}
      </div>
    );
  }

  if (!rows.length) {
    return <EmptyState title={emptyTitle} description={emptyBody} />;
  }

  return (
    <div className="space-y-2" data-testid="kb-card-list">
      {rows.map((r) => <KnowledgeCard key={r.id} row={r} />)}
    </div>
  );
}

export { safeFormatRelative };
