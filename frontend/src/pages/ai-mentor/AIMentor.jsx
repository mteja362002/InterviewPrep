import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { formatDistanceToNow, parseISO } from 'date-fns';
import {
  Sparkles, Send, Plus, Trash2, Loader2, MessageSquare,
  Target, TrendingDown, TrendingUp, BookOpen, AlertTriangle, Route,
  PanelLeftClose, PanelLeft,
} from 'lucide-react';
import { GlassCard } from '@/components/common/GlassCard';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { MENTOR } from '@/constants/testIds';
import { useMentorContext } from '@/contexts/MentorContext';
import { MentorLessonCards } from '@/components/mentor/MentorLessonCards';
import { stripMathDelimiters } from '@/utils/markdownHelpers';
import { useAuth } from '@/contexts/AuthContext';
import { UserAvatar } from '@/components/common/UserAvatar';

// ---------- Sidebar ----------

function ConversationRow({ convo, active, onSelect, onDelete }) {
  return (
    <div
      role="button"
      tabIndex={0}
      data-testid={`${MENTOR.conversationItem}-${convo.id}`}
      onClick={() => onSelect(convo.id)}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelect(convo.id)}
      className={cn(
        'group relative px-3 py-2.5 rounded-xl border cursor-pointer transition-colors',
        active
          ? 'border-primary/40 bg-primary/[0.08]'
          : 'border-transparent hairline bg-foreground/[0.02] hover:bg-foreground/[0.04]',
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium truncate">{convo.title || 'New conversation'}</div>
          {convo.last_message_preview && (
            <div className="text-xs text-muted-foreground truncate mt-0.5">
              {convo.last_message_preview}
            </div>
          )}
        </div>
        <button
          data-testid={`${MENTOR.deleteButton}-${convo.id}`}
          onClick={(e) => {
            e.stopPropagation();
            if (window.confirm('Delete this conversation?')) onDelete(convo.id);
          }}
          className="opacity-0 group-hover:opacity-100 transition-opacity h-6 w-6 rounded-md hover:bg-rose-500/15 text-rose-300 flex items-center justify-center flex-shrink-0"
          aria-label="Delete conversation"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="flex items-center gap-2 mt-1.5">
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground/70">
          {convo.message_count || 0} msgs
        </span>
        <span className="text-[10px] text-muted-foreground/70">·</span>
        <span className="text-[10px] text-muted-foreground/70">
          {(() => {
            try { return formatDistanceToNow(parseISO(convo.updated_at), { addSuffix: true }); }
            catch { return ''; }
          })()}
        </span>
      </div>
    </div>
  );
}

// ---------- Context panel ----------

function ContextPanel({ preview }) {
  if (!preview) return null;
  const { name, target_companies, weak_topics, strong_topics, todays_mission, revision_due_count, current_topic } = preview;
  return (
    <GlassCard className="p-4" data-testid={MENTOR.contextPreview}>
      <div className="flex items-center gap-2 mb-3">
        <span className="h-6 w-6 rounded-md bg-primary/15 border border-primary/30 flex items-center justify-center">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
        </span>
        <div className="text-xs font-mono uppercase tracking-wider text-muted-foreground">Mentor context</div>
      </div>
      <div className="space-y-2.5 text-sm">
        {name && (
          <div>
            <div className="text-xs text-muted-foreground">Learner</div>
            <div className="text-sm">{name}</div>
          </div>
        )}
        {target_companies?.length > 0 && (
          <div>
            <div className="text-xs text-muted-foreground flex items-center gap-1.5"><Target className="h-3 w-3" /> Target companies</div>
            <div className="flex flex-wrap gap-1 mt-1">
              {target_companies.slice(0, 6).map((c) => (
                <Badge key={c} variant="outline" className="text-[10px] font-mono py-0 px-1.5">{c}</Badge>
              ))}
            </div>
          </div>
        )}
        {current_topic && (
          <div>
            <div className="text-xs text-muted-foreground flex items-center gap-1.5"><BookOpen className="h-3 w-3" /> Current topic</div>
            <div className="text-sm mt-0.5">{current_topic.label}</div>
            <div className="text-[10px] text-muted-foreground/80 mt-0.5">
              KB cache: {current_topic.kb_available ? 'available' : 'not generated'}
            </div>
          </div>
        )}
        {weak_topics?.length > 0 && (
          <div>
            <div className="text-xs text-muted-foreground flex items-center gap-1.5"><TrendingDown className="h-3 w-3 text-rose-300" /> Weak areas</div>
            <div className="text-xs text-muted-foreground/90 mt-0.5">{weak_topics.slice(0, 4).join(' · ')}</div>
          </div>
        )}
        {strong_topics?.length > 0 && (
          <div>
            <div className="text-xs text-muted-foreground flex items-center gap-1.5"><TrendingUp className="h-3 w-3 text-emerald-300" /> Strong areas</div>
            <div className="text-xs text-muted-foreground/90 mt-0.5">{strong_topics.slice(0, 4).join(' · ')}</div>
          </div>
        )}
        {todays_mission && (
          <div>
            <div className="text-xs text-muted-foreground">Today's mission</div>
            <div className="text-xs text-muted-foreground/90 mt-0.5">
              {todays_mission.focus_topic || 'general'} · {todays_mission.progress}
            </div>
          </div>
        )}
        {revision_due_count > 0 && (
          <div>
            <div className="text-xs text-muted-foreground">Revision queue</div>
            <div className="text-sm text-amber-300">{revision_due_count} due now</div>
          </div>
        )}
        {preview.recommended_next_step && (
          <div className="mt-2 pt-2.5 border-t hairline">
            <div className="text-xs text-muted-foreground flex items-center gap-1.5"><Route className="h-3 w-3 text-primary" /> Recommended next step</div>
            <div className="text-sm mt-0.5 font-medium text-primary/95">{preview.recommended_next_step.label}</div>
            <div className="text-[10px] text-muted-foreground/80 mt-0.5">
              First incomplete prerequisite on your path
            </div>
          </div>
        )}
      </div>
    </GlassCard>
  );
}

// ---------- Messages ----------

function MentorMarkdown({ children }) {
  return (
    <div className="mentor-prose prose prose-sm dark:prose-invert max-w-none prose-headings:font-display prose-headings:text-foreground prose-h1:text-lg prose-h1:mt-4 prose-h1:mb-2 prose-h2:text-base prose-h2:mt-3 prose-h2:mb-1.5 prose-h3:text-sm prose-h3:mt-2.5 prose-h3:mb-1 prose-p:text-foreground/90 prose-p:leading-relaxed prose-p:my-2 prose-strong:text-foreground prose-code:text-primary prose-code:bg-primary/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-[13px] prose-code:before:content-[''] prose-code:after:content-[''] prose-pre:bg-[color:var(--code-bg)] prose-pre:border hairline prose-pre:rounded-lg prose-pre:my-3 prose-pre:text-[13px] prose-a:text-primary hover:prose-a:text-primary/80 prose-li:text-foreground/90 prose-li:my-0.5 prose-ol:my-2 prose-ul:my-2 prose-hr:border-[color:var(--hairline-strong)] prose-hr:my-4 prose-blockquote:border-l-primary/40 prose-blockquote:bg-primary/[0.04] prose-blockquote:py-0.5 prose-blockquote:px-3 prose-blockquote:not-italic prose-blockquote:text-foreground/85 prose-table:my-3 prose-th:bg-foreground/[0.04] prose-th:px-3 prose-th:py-1.5 prose-th:text-left prose-th:text-xs prose-td:px-3 prose-td:py-1.5 prose-td:border-t prose-td:border-[color:var(--hairline)]">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{stripMathDelimiters(children || '')}</ReactMarkdown>
    </div>
  );
}

function MessageBubble({ message, user }) {
  const isUser = message.role === 'user';
  if (message.style === 'lesson' && message.structured_content) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        data-testid={MENTOR.assistantMessage}
        className="py-4"
      >
        <div className="flex items-center gap-2 mb-3">
          <span className="h-6 w-6 rounded-md bg-primary/15 border border-primary/30 flex items-center justify-center">
            <Sparkles className="h-3 w-3 text-primary" />
          </span>
          <span className="text-[10px] font-mono uppercase tracking-wider text-primary/80">
            Structured lesson · 9 cards
          </span>
        </div>
        <MentorLessonCards lesson={message.structured_content} />
      </motion.div>
    );
  }
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      data-testid={isUser ? MENTOR.userMessage : MENTOR.assistantMessage}
      className={cn('flex gap-3 py-4', isUser ? 'flex-row-reverse' : 'flex-row')}
    >
      <div className="shrink-0 mt-0.5">
        {isUser ? (
          <UserAvatar user={user} size="md" />
        ) : (
          <div className="h-9 w-9 rounded-lg bg-primary/15 border border-primary/30 flex items-center justify-center text-primary">
            <Sparkles className="h-4 w-4" />
          </div>
        )}
      </div>
      <div className={cn('flex-1 min-w-0', isUser && 'flex justify-end')}>
        <div className={cn(
          'rounded-2xl px-4 py-3 border max-w-[85%] min-w-0 break-words',
          isUser
            ? 'bg-primary/[0.08] border-primary/20 text-foreground rounded-tr-md'
            : 'bg-foreground/[0.02] hairline rounded-tl-md',
        )}>
          {isUser ? (
            <div className="text-sm whitespace-pre-wrap break-words">{message.content}</div>
          ) : (
            <MentorMarkdown>{message.content}</MentorMarkdown>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ---------- Composer ----------

function Composer({ onSend, sending, disabled }) {
  const [text, setText] = useState('');
  const [lessonMode, setLessonMode] = useState(false);
  const textareaRef = useRef(null);

  const submit = () => {
    if (sending || !text.trim()) return;
    onSend(text, lessonMode ? 'lesson' : 'chat');
    setText('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div
      className="sticky bottom-0 border-t bg-[hsl(var(--surface))]/95 backdrop-blur-xl px-4 sm:px-6 py-3 sm:py-4 shrink-0"
      style={{ borderColor: 'var(--hairline)' }}
    >
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-2">
          <label className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-muted-foreground cursor-pointer">
            <input
              type="checkbox"
              checked={lessonMode}
              onChange={(e) => setLessonMode(e.target.checked)}
              className="h-3 w-3 rounded accent-primary"
              data-testid="mentor-lesson-mode-toggle"
            />
            <BookOpen className="h-3 w-3" />
            Structured lesson (9-card format)
          </label>
        </div>
        <div className="flex items-end gap-2 sm:gap-3">
          <Textarea
            ref={textareaRef}
            data-testid={MENTOR.input}
            rows={1}
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              const el = e.target;
              el.style.height = 'auto';
              el.style.height = Math.min(el.scrollHeight, 200) + 'px';
            }}
            onKeyDown={onKeyDown}
            disabled={disabled}
            placeholder={lessonMode
              ? 'Ask for a full lesson (e.g. "Teach me HashMap")…'
              : 'Ask about a concept, request a mock question, or paste your solution for review…'}
            className="resize-none bg-foreground/[0.03] focus:border-primary/40 min-h-[48px] max-h-[200px] text-sm"
          />
          <Button
            data-testid={MENTOR.sendButton}
            onClick={submit}
            disabled={sending || !text.trim() || disabled}
            className="h-12 px-4 sm:px-5 bg-primary hover:bg-primary/90 text-primary-foreground gap-2 shrink-0"
          >
            {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            <span className="hidden sm:inline">{sending ? 'Thinking…' : 'Send'}</span>
          </Button>
        </div>
        <div className="mt-1.5 text-[10px] text-muted-foreground/70 font-mono uppercase tracking-wider hidden sm:block">
          Enter to send · Shift+Enter for newline · Lesson mode returns a 9-card structured response
        </div>
      </div>
    </div>
  );
}

// ---------- Empty state ----------

const STARTER_PROMPTS = [
  { title: 'Roadmap next step',   body: 'What should I study next based on my current progress?' },
  { title: 'Weak-area drill',     body: 'Give me a targeted mini-drill on my weakest topic.' },
  { title: 'Mock interview',      body: 'Ask me a system design question at Google L4 bar. Then grade my answer.' },
  { title: 'Structured lesson',   body: 'Teach me HashMap deeply as a structured lesson.' },
];

function EmptyState({ onPick, contextPreview }) {
  return (
    <div className="flex-1 flex items-center justify-center px-4 sm:px-6 py-8 sm:py-12 overflow-y-auto" data-testid={MENTOR.emptyState}>
      <div className="max-w-2xl w-full">
        <div className="text-center mb-6 sm:mb-8">
          <div className="inline-flex h-12 w-12 rounded-2xl bg-primary/15 border border-primary/30 items-center justify-center mb-4">
            <Sparkles className="h-5 w-5 text-primary" />
          </div>
          <h1 className="font-display text-xl sm:text-3xl font-semibold tracking-tight">
            PrepOS Mentor
          </h1>
          <p className="mt-2 text-sm text-muted-foreground max-w-md mx-auto">
            A senior interview mentor grounded in your progress, weak areas, and roadmap.
            Not a chatbot — the intelligence layer of PrepOS.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {STARTER_PROMPTS.map((p) => (
            <button
              key={p.title}
              onClick={() => onPick(p.body)}
              className="text-left p-4 rounded-xl border hairline bg-foreground/[0.02] hover:bg-foreground/[0.04] hover:border-primary/25 transition-colors"
            >
              <div className="text-xs font-mono uppercase tracking-wider text-primary/80 mb-1">
                {p.title}
              </div>
              <div className="text-sm text-foreground/90">{p.body}</div>
            </button>
          ))}
        </div>
        {contextPreview && (contextPreview.weak_topics?.length > 0) && (
          <div className="mt-6 text-center text-[11px] text-muted-foreground/70">
            Mentor knows your weak areas: {contextPreview.weak_topics.slice(0, 3).join(', ')}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------- Main page ----------

export default function AIMentor() {
  const m = useMentorContext();
  const { user } = useAuth();
  const scrollRef = useRef(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [m.messages, m.sending]);

  return (
    <div
      data-testid={MENTOR.root}
      className="-mx-4 sm:-mx-6 lg:-mx-8 -my-6 sm:-my-8 flex overflow-hidden"
      style={{ height: 'calc(100vh - 4rem)' }}
    >
      {/* Sidebar: history + context */}
      <aside
        className={cn(
          'hidden md:flex flex-shrink-0 flex-col border-r bg-[hsl(var(--surface))]/40 backdrop-blur-xl transition-[width] duration-300 min-h-0',
          sidebarOpen ? 'w-[280px]' : 'w-[52px]',
        )}
        style={{ borderColor: 'var(--hairline)' }}
      >
        <div
          className={cn('flex items-center gap-2 border-b shrink-0', sidebarOpen ? 'px-4 pt-5 pb-3' : 'px-2 py-3 justify-center')}
          style={{ borderColor: 'var(--hairline)' }}
        >
          {sidebarOpen && (
            <div className="flex-1">
              <div className="overline mb-2">AI Mentor</div>
              <Button
                data-testid={MENTOR.newChatButton}
                variant="outline"
                className="w-full justify-start gap-2 bg-foreground/[0.03] hover:bg-foreground/[0.06]"
                onClick={() => m.startNewChat()}
              >
                <Plus className="h-4 w-4" />
                New chat
              </Button>
            </div>
          )}
          <button
            onClick={() => setSidebarOpen((v) => !v)}
            className="h-8 w-8 flex items-center justify-center rounded-md border hover:bg-foreground/[0.04] transition-colors shrink-0"
            style={{ borderColor: 'var(--hairline)' }}
            aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            {sidebarOpen ? <PanelLeftClose className="h-3.5 w-3.5" /> : <PanelLeft className="h-3.5 w-3.5" />}
          </button>
        </div>
        {sidebarOpen && (
          <>
            <div className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-3 space-y-1.5 min-h-0" data-testid={MENTOR.historyList}>
              {m.historyLoading && (
                <div className="text-xs text-muted-foreground px-2 py-4 text-center">Loading…</div>
              )}
              {!m.historyLoading && m.history.length === 0 && (
                <div className="text-xs text-muted-foreground px-2 py-4 text-center">
                  No conversations yet. Start one on the right.
                </div>
              )}
              {m.history.map((c) => (
                <ConversationRow
                  key={c.id}
                  convo={c}
                  active={c.id === m.activeId}
                  onSelect={m.loadConversation}
                  onDelete={m.removeConversation}
                />
              ))}
            </div>
            <div className="p-3 border-t shrink-0" style={{ borderColor: 'var(--hairline)' }}>
              <ContextPanel preview={m.contextPreview} />
            </div>
          </>
        )}
        {!sidebarOpen && (
          <button
            onClick={() => m.startNewChat()}
            className="mx-2 mt-3 h-8 w-8 flex items-center justify-center rounded-md border hover:bg-foreground/[0.04] transition-colors"
            style={{ borderColor: 'var(--hairline)' }}
            title="New chat"
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
        )}
      </aside>

      {/* Main chat pane */}
      <main className="flex-1 flex flex-col min-w-0 min-h-0">
        {m.error && (
          <div
            data-testid={MENTOR.errorBanner}
            className="px-4 sm:px-6 py-2.5 flex items-center gap-2 bg-rose-500/10 border-b border-rose-500/30 text-rose-200 text-xs shrink-0"
          >
            <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />
            <span className="flex-1 min-w-0 truncate">{m.error}</span>
            <button
              onClick={m.dismissError}
              className="text-rose-200/70 hover:text-rose-100 uppercase font-mono tracking-wider text-[10px]"
            >
              Dismiss
            </button>
          </div>
        )}

        {m.messages.length === 0 && !m.sending ? (
          <EmptyState
            onPick={(text) => m.sendMessage(text, { responseStyle: /structured|teach me|lesson/i.test(text) ? 'lesson' : 'chat' })}
            contextPreview={m.contextPreview}
          />
        ) : (
          <div
            ref={scrollRef}
            data-testid={MENTOR.messageList}
            className="flex-1 overflow-y-auto overflow-x-hidden min-h-0"
          >
            <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4 sm:py-6 divide-y divide-[color:var(--hairline)]">
              <AnimatePresence initial={false}>
                {m.messages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} user={user} />
                ))}
              </AnimatePresence>
              {m.sending && (
                <motion.div
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-3 py-4"
                  data-testid="mentor-typing-indicator"
                >
                  <div className="h-9 w-9 rounded-lg bg-primary/15 border border-primary/30 flex items-center justify-center shrink-0">
                    <Sparkles className="h-4 w-4 text-primary" />
                  </div>
                  <div className="rounded-2xl px-4 py-3 border hairline bg-foreground/[0.02] flex items-center gap-1.5">
                    <span className="text-xs text-muted-foreground mr-1.5">Thinking</span>
                    {[0, 1, 2].map((i) => (
                      <span
                        key={i}
                        className="inline-block h-1.5 w-1.5 rounded-full bg-primary/70"
                        style={{
                          animation: 'mentorDotBounce 1.4s infinite ease-in-out',
                          animationDelay: `${i * 0.16}s`,
                        }}
                      />
                    ))}
                    <style>{`
                      @keyframes mentorDotBounce {
                        0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
                        40% { transform: scale(1); opacity: 1; }
                      }
                    `}</style>
                  </div>
                </motion.div>
              )}
            </div>
          </div>
        )}

        <Composer onSend={(t, style) => m.sendMessage(t, { responseStyle: style })} sending={m.sending} />
      </main>
    </div>
  );
}
