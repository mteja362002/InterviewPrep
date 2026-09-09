import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import {
  BookOpen, Loader2, ChevronRight, Search, Layers, Cpu,
  Coffee, Network, Database, Wifi, Code2, Hammer, MessageCircle, FileText,
} from 'lucide-react';
import { GlassCard } from '@/components/common/GlassCard';
import { formatApiError } from '@/utils/formatApiError';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { StatusBadge } from '@/components/progress/StatusBadge';
import { FilterChips } from '@/components/progress/FilterChips';
import { matchNode } from '@/hooks/useProgressTree';
import { useRoadmapTree, useRoadmapSummary, useRevisions } from '@/queries/hooks';
import { useRecentlyViewed } from '@/hooks/useRecentlyViewed';
import { KnowledgeViewTabs, KNOWLEDGE_VIEWS } from '@/components/knowledge/KnowledgeViewTabs';
import { ProgressProvenance } from '@/components/knowledge/ProgressProvenance';
import { KnowledgeStats } from '@/components/knowledge/KnowledgeStats';
import { KnowledgeCardList } from '@/components/knowledge/KnowledgeCardList';
import {
  flattenLeaves, bookmarkView, favoriteView, weakView,
  continueLearningView, recentlyViewedView, revisionDueGroups, filterRows,
} from '@/components/knowledge/knowledgeViews';

const TRACK_ICON = {
  dsa: Code2, java: Coffee, lld: Layers, hld: Network,
  operating_systems: Cpu, dbms: Database, computer_networks: Wifi,
  projects: Hammer, behavioral: MessageCircle, resume: FileText,
};

const SUBJECT_ORDER = [
  'programming_fundamentals', 'java', 'dsa', 'dbms', 'operating_systems',
  'computer_networks', 'lld', 'hld', 'projects', 'resume', 'behavioral',
];

const subjectOrderIndex = new Map(SUBJECT_ORDER.map((id, index) => [id, index]));

function orderSubjects(tracks) {
  return [...tracks].sort((left, right) => (
    (subjectOrderIndex.get(left.id) ?? Number.MAX_SAFE_INTEGER)
    - (subjectOrderIndex.get(right.id) ?? Number.MAX_SAFE_INTEGER)
  ));
}

const BUCKET_DOT = {
  green: 'bg-emerald-400',
  yellow: 'bg-amber-400',
  red: 'bg-rose-400',
};

function flattenTopics(rootNodes, expanded) {
  const out = [];
  const stack = [];
  for (let i = rootNodes.length - 1; i >= 0; i--) {
    stack.push({ n: rootNodes[i], depth: 0 });
  }
  while (stack.length) {
    const { n, depth } = stack.pop();
    const hasKids = (n.children || []).length > 0;
    out.push({ node: n, depth, hasKids });
    if (hasKids && expanded.has(n.id)) {
      for (let i = n.children.length - 1; i >= 0; i--) {
        stack.push({ n: n.children[i], depth: depth + 1 });
      }
    }
  }
  return out;
}

function TopicItem({ topic, depth, hasKids, isOpen, onToggle }) {
  const status = topic.progress?.status || 'not_started';
  const bkt = topic.progress?.revision_bucket || 'green';
  const bookmarked = !!topic.progress?.bookmarked;
  const favorite = !!topic.progress?.favorite;
  return (
    <div style={{ paddingLeft: `${depth * 20}px` }}>
      <div className="flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-white/[0.03] transition-colors">
        {hasKids ? (
          <button onClick={onToggle} className="shrink-0 h-5 w-5 flex items-center justify-center rounded hover:bg-white/[0.05]">
            <ChevronRight className={cn('h-3 w-3 text-muted-foreground transition-transform', isOpen && 'rotate-90')} />
          </button>
        ) : (
          <span className="h-5 w-5 shrink-0 flex items-center justify-center">
            <span className={cn('h-1.5 w-1.5 rounded-full', BUCKET_DOT[bkt])} />
          </span>
        )}
        <Link
          to={`/app/knowledge-base/nodes/${topic.id}`}
          data-testid={`roadmap-node-${topic.id}`}
          className="flex-1 text-sm truncate hover:text-primary transition-colors"
        >
          {topic.label}
        </Link>
        {bookmarked && (
          <span title="Bookmarked" className="text-primary text-[10px]" data-testid={`node-bookmark-indicator-${topic.id}`}>■</span>
        )}
        {favorite && (
          <span title="Favorite" className="text-amber-300 text-[10px]" data-testid={`node-favorite-indicator-${topic.id}`}>★</span>
        )}
        <StatusBadge status={status} className="hidden sm:inline-block" />
        <span className="font-mono text-[11px] text-muted-foreground w-10 text-right">
          <span title="Certified actual mastery">{Math.round(topic.progress?.mastery_percentage || 0)}%</span>
        </span>
      </div>
    </div>
  );
}

function ModuleBlock({ module, isOpen, onToggle, expanded, toggleNode }) {
  const modMastery = module.progress?.mastery_percentage || 0;
  const rows = isOpen ? flattenTopics(module.children || [], expanded) : [];
  return (
    <div className="rounded-lg border border-white/[0.06] bg-white/[0.02]" data-testid={`roadmap-module-${module.id}`}>
      <button
        onClick={onToggle}
        className="w-full text-left px-4 py-3 flex items-center gap-3 hover:bg-white/[0.03] transition-colors"
      >
        <ChevronRight className={cn('h-3.5 w-3.5 text-muted-foreground shrink-0 transition-transform', isOpen && 'rotate-90')} />
        <span className="flex-1 text-sm font-medium">{module.label}</span>
        <div className="w-32 h-1 rounded-full bg-white/[0.05] overflow-hidden hidden sm:block">
          <div className="h-full bg-primary/70" style={{ width: `${modMastery}%` }} />
        </div>
        <span className="font-mono text-[11px] text-muted-foreground w-10 text-right">
          {Math.round(modMastery)}%
        </span>
      </button>
      <div className="px-4 pb-2"><ProgressProvenance progress={{ legacy_progress: module.progress?.legacy_progress }} /></div>
      {isOpen && (
        <div className="px-4 pb-3 pt-1 space-y-1">
          {rows.map((r) => (
            <TopicItem
              key={r.node.id} topic={r.node} depth={r.depth} hasKids={r.hasKids}
              isOpen={expanded.has(r.node.id)}
              onToggle={() => toggleNode(r.node.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function TrackBlock({ track, isOpen, onToggle, expanded, toggleNode }) {
  const Icon = TRACK_ICON[track.id] || BookOpen;
  const mastery = track.progress?.mastery_percentage || 0;
  const bucket = track.progress?.revision_bucket || 'green';
  const modules = track.children || [];
  return (
    <GlassCard className="p-0 overflow-hidden" data-testid={`roadmap-track-${track.id}`}>
      <button
        onClick={onToggle}
        className="w-full text-left px-6 py-5 flex items-center gap-4 hover:bg-white/[0.02] transition-colors"
      >
        <span className="h-10 w-10 rounded-xl bg-primary/15 border border-primary/30 flex items-center justify-center shrink-0">
          <Icon className="h-5 w-5 text-primary" />
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="font-display text-lg font-semibold tracking-tight">{track.label}</h2>
            <span className={cn('h-1.5 w-1.5 rounded-full', BUCKET_DOT[bucket])} />
          </div>
          <div className="mt-2 flex items-center gap-3">
            <div className="h-1.5 flex-1 rounded-full bg-white/[0.05] overflow-hidden">
              <div className="h-full bg-gradient-to-r from-primary to-secondary" style={{ width: `${mastery}%` }} />
            </div>
            <span className="font-mono text-xs text-muted-foreground text-right">
              Actual Progress: {Math.round(mastery)}%
            </span>
          </div>
        </div>
        <ChevronRight className={cn('h-4 w-4 text-muted-foreground shrink-0 transition-transform', isOpen && 'rotate-90')} />
      </button>
      <div className="px-6 pb-3"><ProgressProvenance progress={track.progress} /></div>
      {isOpen && (
        <div className="px-6 pb-5 pt-1 space-y-2">
          {modules.map((m) => (
            <ModuleBlock
              key={m.id} module={m}
              isOpen={expanded.has(m.id)}
              onToggle={() => toggleNode(m.id)}
              expanded={expanded}
              toggleNode={toggleNode}
            />
          ))}
        </div>
      )}
    </GlassCard>
  );
}

export default function KnowledgeBase() {
  // RC1.3.4 · One React Query subscription drives every workspace
  // view — no duplicate fetches when switching tabs.
  const { data: tree, isLoading: treeLoading, error: treeError } = useRoadmapTree();
  const { data: summary } = useRoadmapSummary();
  const { data: revisions } = useRevisions();
  const { entries: recentEntries } = useRecentlyViewed();

  const [view, setView] = useState('all');
  const [expanded, setExpanded] = useState(new Set());
  const [q, setQ] = useState('');
  const [filters, setFilters] = useState(new Set());

  useEffect(() => {
    if (treeError) toast.error(formatApiError(treeError));
  }, [treeError]);

  const toggleNode = (id) => {
    setExpanded((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id); else n.add(id);
      return n;
    });
  };

  const toggleFilter = (key) => {
    setFilters((s) => {
      const n = new Set(s);
      if (n.has(key)) n.delete(key); else n.add(key);
      return n;
    });
  };

  const clearFilters = () => setFilters(new Set());

  // ---- Derived views (memoised on the same in-memory tree) --------
  const leaves = useMemo(() => flattenLeaves(tree), [tree]);
  const bookmarks = useMemo(() => bookmarkView(leaves), [leaves]);
  const favorites = useMemo(() => favoriteView(leaves), [leaves]);
  const weak = useMemo(() => weakView(leaves), [leaves]);
  const continueRows = useMemo(
    () => continueLearningView(leaves, recentEntries),
    [leaves, recentEntries],
  );
  const recentRows = useMemo(
    () => recentlyViewedView(leaves, recentEntries),
    [leaves, recentEntries],
  );
  const revisionGroups = useMemo(
    () => revisionDueGroups(revisions, leaves),
    [revisions, leaves],
  );

  // Counts feed both the view-tab badges AND the stats strip.
  const viewCounts = useMemo(() => ({
    all: leaves.length,
    continue: continueRows.length,
    bookmarks: bookmarks.length,
    favorites: favorites.length,
    weak: weak.length,
    revision: (revisions || []).length,
    recent: recentRows.length,
  }), [leaves, continueRows, bookmarks, favorites, weak, revisions, recentRows]);

  // ---- All-Topics filtered tree — kept identical to the old view --
  const filteredTracks = useMemo(() => {
    if (!tree) return [];
    const needle = q.trim().toLowerCase();
    const hasFilters = filters.size > 0;
    if (!needle && !hasFilters) return orderSubjects(tree.tracks || []);
    const autoExpand = new Set();
    const cloneMatches = (root) => {
      const stack = [{ node: root, phase: 'enter', parent: null }];
      const rootBox = { copy: null };
      const kidsCollected = new Map();
      while (stack.length) {
        const it = stack[stack.length - 1];
        if (it.phase === 'enter') {
          it.phase = 'exit';
          kidsCollected.set(it.node, []);
          const children = it.node.children || [];
          for (let i = children.length - 1; i >= 0; i--) {
            stack.push({ node: children[i], phase: 'enter', parent: it.node });
          }
        } else {
          stack.pop();
          const kids = kidsCollected.get(it.node) || [];
          const textMatch = !needle
            || it.node.label.toLowerCase().includes(needle)
            || (it.node.id || '').includes(needle);
          const filterMatch = !hasFilters || matchNode(it.node, filters);
          const selfMatch = textMatch && filterMatch;
          if (selfMatch || kids.length) {
            const copy = { ...it.node, children: kids };
            if (kids.length) autoExpand.add(it.node.id);
            if (it.parent) {
              (kidsCollected.get(it.parent) || []).push(copy);
            } else {
              rootBox.copy = copy;
            }
          }
        }
      }
      return rootBox.copy;
    };
    return orderSubjects((tree.tracks || []).map(cloneMatches).filter(Boolean)).map((t, _idx, all) => {
      autoExpand.forEach((_id) => { /* no-op — kept for future auto-expand hooks */ });
      return t;
    });
  }, [tree, q, filters]);

  // Auto-expand tracks whose descendants matched the current filter,
  // moved out of `useMemo` so we no longer trigger the render-time
  // setState warning that used to require the `setTimeout(…, 0)` hack.
  useEffect(() => {
    if (!tree) return;
    const needle = q.trim().toLowerCase();
    const hasFilters = filters.size > 0;
    if (!needle && !hasFilters) return;
    const nextExpanded = new Set(expanded);
    let changed = false;
    (filteredTracks || []).forEach((t) => {
      if ((t.children || []).length > 0 && !nextExpanded.has(t.id)) {
        nextExpanded.add(t.id);
        changed = true;
      }
    });
    if (changed) setExpanded(nextExpanded);
  }, [q, filters, tree, filteredTracks, expanded]);

  const loading = treeLoading && !tree;
  if (loading || !tree) {
    return (
      <div className="py-24 flex flex-col items-center gap-3 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span className="overline">Loading workspace</span>
      </div>
    );
  }

  const filteredRows = (rows) => filterRows(rows, q, filters, matchNode);
  const searchPlaceholder = view === 'all'
    ? 'Find a topic, pattern or learning node…'
    : `Search inside ${KNOWLEDGE_VIEWS.find((v) => v.id === view)?.label || 'this view'}…`;

  return (
    <div className="space-y-6" data-testid="knowledge-base-root">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <div className="overline mb-2">Knowledge Workspace</div>
          <h1 className="font-display text-3xl sm:text-4xl font-semibold tracking-tight">
            Your Learning Library
          </h1>
          <p className="mt-2 text-sm text-muted-foreground max-w-2xl">
            One place to explore the master roadmap, jump back into what you were learning,
            and revisit bookmarks, favourites, weak spots and revision-due topics.
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs font-mono text-muted-foreground">
          <span>Version <span className="text-primary">{tree.version}</span></span>
          <span>·</span>
          <span>{viewCounts.all} topics</span>
        </div>
      </div>

      {/* Stat strip — reuses /api/roadmap/summary; no extra call */}
      <KnowledgeStats summary={summary} counts={{ weak: weak.length }} />

      {/* View tabs */}
      <KnowledgeViewTabs active={view} onChange={setView} counts={viewCounts} />

      {/* Search + filters — apply on top of whichever view is active */}
      <div className="flex flex-col gap-3">
        <div className="relative max-w-lg">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={searchPlaceholder}
            data-testid="knowledge-search-input"
            className="pl-10 bg-white/[0.03] border-white/10 h-11"
          />
        </div>
        <FilterChips
          active={filters}
          companies={tree.companies || []}
          onToggle={toggleFilter}
          onClear={clearFilters}
        />
      </div>

      {/* Content */}
      {view === 'all' && (
        <div className="grid grid-cols-1 gap-4" data-testid="kb-view-all-body">
          {filteredTracks.map((track) => (
            <TrackBlock
              key={track.id} track={track}
              isOpen={expanded.has(track.id)}
              onToggle={() => toggleNode(track.id)}
              expanded={expanded}
              toggleNode={toggleNode}
            />
          ))}
        </div>
      )}
      {view === 'continue' && (
        <KnowledgeCardList
          rows={filteredRows(continueRows)}
          emptyTitle="Nothing to continue yet"
          emptyBody="Open a topic from the roadmap and it will appear here so you can resume anytime."
        />
      )}
      {view === 'bookmarks' && (
        <KnowledgeCardList
          rows={filteredRows(bookmarks)}
          emptyTitle="No bookmarks yet"
          emptyBody="Tap the bookmark icon on any topic to save it here as a reading list."
        />
      )}
      {view === 'favorites' && (
        <KnowledgeCardList
          rows={filteredRows(favorites)}
          emptyTitle="No favorites yet"
          emptyBody="Star the topics you consider interview-critical to see them here at a glance."
        />
      )}
      {view === 'weak' && (
        <KnowledgeCardList
          rows={filteredRows(weak)}
          emptyTitle="No weak spots — yet"
          emptyBody="Topics with low confidence or high weakness will surface here so you can prioritise them."
        />
      )}
      {view === 'revision' && (
        <KnowledgeCardList
          groups={revisionGroups.map((g) => ({ ...g, rows: filteredRows(g.rows) }))}
          emptyTitle="No revisions scheduled"
          emptyBody="Complete a topic and PrepOS will schedule spaced-repetition reviews here."
        />
      )}
      {view === 'recent' && (
        <KnowledgeCardList
          rows={filteredRows(recentRows)}
          emptyTitle="No recently viewed topics"
          emptyBody="Open a topic and it will appear here — even after you leave and come back."
        />
      )}
    </div>
  );
}
