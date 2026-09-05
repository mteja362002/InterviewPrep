import { useState } from 'react';
import {
  BookOpen, Sparkles, Bookmark,
  Layers, Users, AlertTriangle, RefreshCw, Loader2, Wand2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { GlassCard } from '@/components/common/GlassCard';
import { cn } from '@/lib/utils';
import { useAIContent } from '@/hooks/useAIContent';

/**
 * AI-generated knowledge content viewer.
 *
 * Renders 7 populated tabs (theory, examples, tips, mistakes, flashcards,
 * related, prerequisites) and 2 stub tabs (articles, videos) that stay as
 * placeholders per product spec.
 *
 * Behavior:
 *   - On mount: GET /roadmap/nodes/{id}/content — never triggers generation.
 *   - If not available: render an empty-state with a "Generate with AI"
 *     button that POSTs /content/generate.
 *   - After generation, MongoDB caches the response; every subsequent visit
 *     is a cache read.
 */

const TABS = [
  { key: 'theory',        label: 'Theory',           icon: BookOpen,    ai: true },
  { key: 'examples',      label: 'Examples',         icon: Sparkles,    ai: true },
  { key: 'flashcards',    label: 'Flashcards',       icon: Bookmark,    ai: true },
  { key: 'related',       label: 'Related Topics',   icon: Layers,      ai: true },
  { key: 'prerequisites', label: 'Prerequisites',    icon: Users,       ai: true },
  { key: 'articles',      label: 'Articles',         icon: BookOpen,    ai: false },
  { key: 'videos',        label: 'Videos',           icon: Sparkles,    ai: false },
];


export function AIContentTabs({ nodeId }) {
  const { content, loading, generating, genError, generate } = useAIContent(nodeId);
  const [tab, setTab] = useState('theory');

  const handleGenerate = ({ regenerate = false } = {}) => generate({ regenerate });

  if (loading) {
    return (
      <GlassCard className="p-6" data-testid="ai-content-loading">
        <div className="flex items-center gap-2 text-muted-foreground text-sm">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="overline">Loading AI content</span>
        </div>
      </GlassCard>
    );
  }

  const available = !!content?.available;
  const activeTab = TABS.find((t) => t.key === tab) || TABS[0];
  const isPlaceholderTab = !activeTab.ai;

  return (
    <GlassCard className="p-6" data-testid="ai-content">
      {/* Tab strip — same visual language as the existing RESOURCE_TABS */}
      <div className="flex items-center gap-2 flex-wrap mb-4">
        <div className="flex flex-wrap gap-2 flex-1">
          {TABS.map((t) => {
            const Icon = t.icon;
            const active = tab === t.key;
            return (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                data-testid={`ai-tab-${t.key}`}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs transition-colors',
                  active
                    ? 'border-primary/40 bg-primary/10 text-primary'
                    : 'border-white/[0.06] bg-white/[0.02] text-muted-foreground hover:text-foreground',
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                {t.label}
                {!t.ai && (
                  <span className="text-[9px] font-mono uppercase tracking-wider ml-1 opacity-60">
                    stub
                  </span>
                )}
              </button>
            );
          })}
        </div>
        {available && (
          <button
            onClick={() => handleGenerate({ regenerate: true })}
            disabled={generating}
            data-testid="ai-content-regenerate"
            className="inline-flex items-center gap-1 text-[11px] font-mono uppercase tracking-wider text-muted-foreground hover:text-primary transition-colors disabled:opacity-50"
            title="Regenerate content"
          >
            {generating ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
            Regenerate
          </button>
        )}
      </div>

      {/* Content body */}
      {isPlaceholderTab ? (
        <PlaceholderBlock label={activeTab.label} />
      ) : !available ? (
        <EmptyState onGenerate={() => handleGenerate({})} generating={generating} error={genError} />
      ) : (
        <TabBody kind={tab} content={content} />
      )}

      {available && (
        <div className="mt-4 pt-3 border-t border-white/[0.05] flex items-center justify-end text-[10px] font-mono text-muted-foreground/70">
          {content.generated_at && (
            <span>Generated {new Date(content.generated_at).toLocaleDateString()}</span>
          )}
        </div>
      )}
    </GlassCard>
  );
}


function PlaceholderBlock({ label }) {
  return (
    <div className="rounded-xl border border-dashed border-white/[0.08] bg-white/[0.015] p-8 text-center"
         data-testid="ai-content-placeholder">
      <Sparkles className="h-5 w-5 text-muted-foreground mx-auto mb-2" />
      <p className="text-sm text-muted-foreground">
        {label} content is intentionally not AI-generated yet.
      </p>
      <p className="mt-1 text-xs text-muted-foreground/70 font-mono">
        Placeholder · reserved for curated resources.
      </p>
    </div>
  );
}


function EmptyState({ onGenerate, generating, error }) {
  return (
    <div className="rounded-xl border border-dashed border-white/[0.08] bg-white/[0.015] p-8 text-center"
         data-testid="ai-content-empty">
      <Wand2 className="h-6 w-6 text-primary mx-auto mb-3" />
      <p className="text-sm">
        No AI content generated yet for this topic.
      </p>
      <p className="mt-1 text-xs text-muted-foreground/70">
        Content is generated once, cached in the database, and shared with the whole community.
      </p>
      {error && (
        <div className="mt-4 mx-auto max-w-md rounded-lg border border-rose-400/30 bg-rose-400/10 px-3 py-2 text-xs text-left text-rose-200"
             data-testid="ai-content-error">
          <div className="flex items-start gap-2">
            <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
            <div className="flex-1">
              <div>AI is temporarily unavailable. Please try again in a few moments.</div>
            </div>
          </div>
        </div>
      )}
      <div className="mt-5 flex items-center justify-center gap-2">
        <Button
          onClick={onGenerate}
          disabled={generating}
          data-testid="ai-content-generate"
          className="h-9 text-xs"
        >
          {generating ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <Wand2 className="h-3.5 w-3.5 mr-1.5" />}
          {generating ? 'Generating…' : 'Generate with AI'}
        </Button>
      </div>
    </div>
  );
}


// -- Section renderers ------------------------------------------------------

function TabBody({ kind, content }) {
  if (kind === 'theory')        return <TheorySection theory={content.theory} />;
  if (kind === 'examples')      return <ExamplesSection items={content.examples} />;
  if (kind === 'flashcards')    return <FlashcardsSection items={content.flashcards} />;
  if (kind === 'related')       return <NodeLinkSection kind="related" items={content.related_topics} emptyLabel="No related topics returned." />;
  if (kind === 'prerequisites') return <NodeLinkSection kind="prereq"  items={content.prerequisites} emptyLabel="No prerequisites returned." />;
  return null;
}

function TheorySection({ theory }) {
  if (!theory) return <EmptyLine>No theory generated yet.</EmptyLine>;
  return (
    <div className="space-y-4 text-sm leading-relaxed" data-testid="ai-section-theory">
      <SubHead>Beginner Explanation</SubHead>
      <p>{theory.beginner}</p>
      <SubHead>Deep Dive</SubHead>
      <p className="whitespace-pre-line">{theory.deep}</p>
      {theory.real_world && (<><SubHead>Real-world Intuition</SubHead><p>{theory.real_world}</p></>)}
      {theory.architecture && (<><SubHead>Architecture Perspective</SubHead><p>{theory.architecture}</p></>)}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
        <BulletBlock title="Advantages" items={theory.advantages} tone="good" />
        <BulletBlock title="Disadvantages" items={theory.disadvantages} tone="bad" />
        <BulletBlock title="When to use" items={theory.when_to_use} tone="good" />
        <BulletBlock title="When NOT to use" items={theory.when_not_to_use} tone="bad" />
      </div>
      {theory.interview_summary && (
        <div className="mt-2 rounded-lg border border-primary/25 bg-primary/[0.05] p-3">
          <div className="overline text-primary mb-1">30-second interview answer</div>
          <p className="text-sm">{theory.interview_summary}</p>
        </div>
      )}
    </div>
  );
}

function ExamplesSection({ items }) {
  if (!items?.length) return <EmptyLine>No examples generated yet.</EmptyLine>;
  return (
    <div className="space-y-3" data-testid="ai-section-examples">
      {items.map((ex, i) => (
        <div key={i} className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-4">
          <div className="text-sm font-medium mb-1.5">{ex.title || `Example ${i + 1}`}</div>
          {ex.scenario && <p className="text-sm text-muted-foreground">{ex.scenario}</p>}
          {ex.walkthrough && <p className="mt-2 text-sm">{ex.walkthrough}</p>}
        </div>
      ))}
    </div>
  );
}


function FlashcardsSection({ items }) {
  if (!items?.length) return <EmptyLine>No flashcards generated yet.</EmptyLine>;
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="ai-section-flashcards">
      {items.map((c, i) => (
        <Flashcard key={i} question={c.q} answer={c.a} index={i} />
      ))}
    </div>
  );
}

function Flashcard({ question, answer, index }) {
  const [open, setOpen] = useState(false);
  return (
    <button
      type="button"
      onClick={() => setOpen((v) => !v)}
      data-testid={`ai-flashcard-${index}`}
      className="text-left rounded-lg border border-white/[0.06] bg-white/[0.02] p-4 hover:border-primary/30 transition-colors"
    >
      <div className="text-[10px] font-mono uppercase tracking-wider text-primary mb-1">
        Card {index + 1}
      </div>
      <div className="text-sm">{question}</div>
      {open ? (
        <div className="mt-3 pt-3 border-t border-white/[0.05] text-sm text-muted-foreground">
          {answer}
        </div>
      ) : (
        <div className="mt-3 text-[11px] font-mono uppercase tracking-wider text-muted-foreground/60">
          Tap to reveal answer
        </div>
      )}
    </button>
  );
}

function NodeLinkSection({ kind, items, emptyLabel }) {
  if (!items?.length) return <EmptyLine>{emptyLabel}</EmptyLine>;
  return (
    <div className="space-y-2" data-testid={`ai-section-${kind === 'prereq' ? 'prerequisites' : 'related'}`}>
      {items.map((r, i) => (
        <NodeLinkRow key={i} entry={r} kind={kind} />
      ))}
    </div>
  );
}

function NodeLinkRow({ entry, kind }) {
  const linkable = !!entry.id;
  const inner = (
    <>
      <div className="flex items-center gap-2">
        {kind === 'prereq' ? <Users className="h-3.5 w-3.5 text-primary" /> : <Layers className="h-3.5 w-3.5 text-primary" />}
        <span className="text-sm">{entry.label || entry.id || 'Untitled'}</span>
        {linkable && <ChevronRight className="ml-auto h-4 w-4 text-muted-foreground" />}
      </div>
      {entry.why && <div className="mt-1 text-xs text-muted-foreground pl-5">{entry.why}</div>}
    </>
  );
  const clsBase = 'block rounded-lg border border-white/[0.06] bg-white/[0.02] p-3';
  if (linkable) {
    return (
      <Link
        to={`/app/knowledge-base/nodes/${entry.id}`}
        className={cn(clsBase, 'hover:border-primary/30 transition-colors')}
        data-testid={`ai-link-${kind}-${entry.id}`}
      >
        {inner}
      </Link>
    );
  }
  return <div className={clsBase} data-testid={`ai-link-${kind}-orphan`}>{inner}</div>;
}


// -- Small primitives -------------------------------------------------------

function SubHead({ children }) {
  return <div className="overline text-primary mt-1">{children}</div>;
}

function BulletBlock({ title, items, tone = 'good' }) {
  if (!items?.length) return null;
  const dotCls = tone === 'good' ? 'bg-emerald-400' : 'bg-rose-400';
  return (
    <div>
      <SubHead>{title}</SubHead>
      <ul className="mt-1 space-y-1">
        {items.map((it, i) => (
          <li key={i} className="flex items-start gap-2 text-sm">
            <span className={cn('mt-1.5 h-1.5 w-1.5 rounded-full shrink-0', dotCls)} />
            <span>{it}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function EmptyLine({ children }) {
  return <div className="text-sm text-muted-foreground italic">{children}</div>;
}
