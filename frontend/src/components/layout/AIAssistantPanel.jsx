import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Sparkles, X, Send, Wand2, Loader2, AlertTriangle,
  BookOpen, ExternalLink,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAIPanel } from '@/contexts/AIPanelContext';
import { APP_SHELL } from '@/constants/testIds';
import { useMentorContext } from '@/contexts/MentorContext';
import { MentorLessonCards } from '@/components/mentor/MentorLessonCards';
import { stripMathDelimiters } from '@/utils/markdownHelpers';
import { useAuth } from '@/contexts/AuthContext';
import { UserAvatar } from '@/components/common/UserAvatar';

const SUGGESTED = [
  'What should I study next?',
  'Give me a targeted mini-drill on my weakest topic.',
  'Explain HashMap deeply · Act as Google interviewer',
  'Review my last coding solution.',
];

function DrawerMarkdown({ children }) {
  return (
    <div className="mentor-prose prose prose-sm dark:prose-invert max-w-none prose-headings:font-display prose-headings:text-foreground prose-p:text-foreground/90 prose-p:leading-relaxed prose-strong:text-foreground prose-code:text-primary prose-code:bg-primary/10 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-[''] prose-code:after:content-[''] prose-pre:bg-[color:var(--code-bg)] prose-pre:border hairline prose-a:text-primary prose-li:text-foreground/90">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{stripMathDelimiters(children || '')}</ReactMarkdown>
    </div>
  );
}

function DrawerMessage({ message, user }) {
  const isUser = message.role === 'user';
  if (message.style === 'lesson' && message.structured_content) {
    return (
      <div className="py-2">
        <div className="text-[10px] font-mono uppercase tracking-wider text-primary/80 mb-2">Lesson mode</div>
        <MentorLessonCards lesson={message.structured_content} />
      </div>
    );
  }
  return (
    <div className={isUser ? 'flex justify-end gap-2' : 'flex justify-start gap-2'}>
      {!isUser && (
        <span className="h-7 w-7 rounded-md bg-primary/15 border border-primary/30 flex items-center justify-center shrink-0 mt-0.5">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
        </span>
      )}
      <div
        className={
          isUser
            ? 'max-w-[80%] rounded-2xl rounded-tr-md px-4 py-2.5 bg-primary/15 border border-primary/30 text-sm whitespace-pre-wrap break-words'
            : 'max-w-[85%] rounded-2xl rounded-tl-md px-4 py-3 bg-foreground/[0.03] border hairline text-sm min-w-0'
        }
      >
        {isUser ? message.content : <DrawerMarkdown>{message.content}</DrawerMarkdown>}
      </div>
      {isUser && <UserAvatar user={user} size="xs" className="mt-0.5" />}
    </div>
  );
}

export function AIAssistantPanel() {
  const { open, setOpen, consumeSeed } = useAIPanel();
  const { user } = useAuth();
  const [text, setText] = useState('');
  const [lessonMode, setLessonMode] = useState(false);
  const [seedTopicNodeId, setSeedTopicNodeId] = useState(null);
  const scrollRef = useRef(null);
  const panelRef = useRef(null);
  const navigate = useNavigate();
  const m = useMentorContext();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [m.messages, m.sending, open]);

  // Consume any seed prompt pushed via openWith().
  useEffect(() => {
    if (!open) return;
    const seed = consumeSeed?.();
    if (!seed) return;
    if (seed.prompt) setText(seed.prompt);
    if (seed.topicNodeId) setSeedTopicNodeId(seed.topicNodeId);
    if (seed.responseStyle === 'lesson') setLessonMode(true);
  }, [open, consumeSeed]);

  // Legacy seed pathway — kept for any older callers using window events.
  useEffect(() => {
    const handler = () => {
      const p = window.sessionStorage.getItem('mentor:seedPrompt') || '';
      const nid = window.sessionStorage.getItem('mentor:seedTopicNodeId') || null;
      window.sessionStorage.removeItem('mentor:seedPrompt');
      window.sessionStorage.removeItem('mentor:seedTopicNodeId');
      if (!p) return;
      setText(p);
      setSeedTopicNodeId(nid);
      if (/structured lesson|9-card|full lesson|teach me/i.test(p)) setLessonMode(true);
    };
    window.addEventListener('mentor:openWithSeed', handler);
    return () => window.removeEventListener('mentor:openWithSeed', handler);
  }, []);

  const send = () => {
    const val = text.trim();
    if (!val || m.sending) return;
    m.sendMessage(val, {
      responseStyle: lessonMode ? 'lesson' : 'chat',
      topicNodeId: seedTopicNodeId || undefined,
    });
    setText('');
    setSeedTopicNodeId(null);
  };

  const nextStep = m.contextPreview?.recommended_next_step;

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Click-outside overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={() => setOpen(false)}
            data-testid={APP_SHELL.aiPanelOverlay}
            className="fixed inset-0 z-20 bg-background/40 backdrop-blur-[2px]"
            aria-hidden="true"
          />

          <motion.aside
            ref={panelRef}
            initial={{ x: 480, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 480, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 260, damping: 30 }}
            data-testid={APP_SHELL.aiPanel}
            role="dialog"
            aria-label="AI Mentor"
            className="fixed top-16 right-0 bottom-0 z-30 w-full sm:w-[480px] max-w-full border-l bg-[hsl(var(--surface))]/95 backdrop-blur-2xl flex flex-col min-h-0"
            style={{ borderColor: 'var(--hairline)' }}
          >
            <div className="h-14 px-5 flex items-center justify-between border-b shrink-0" style={{ borderColor: 'var(--hairline)' }}>
              <div className="flex items-center gap-2 min-w-0">
                <span className="h-7 w-7 rounded-md bg-primary/15 border border-primary/30 flex items-center justify-center shrink-0">
                  <Sparkles className="h-3.5 w-3.5 text-primary" />
                </span>
                <div className="leading-tight min-w-0">
                  <p className="text-sm font-medium truncate">AI Mentor</p>
                  <p className="text-[11px] text-muted-foreground font-mono uppercase tracking-wider truncate">
                    {m.sending ? 'thinking…' : (m.messages.length ? `${m.messages.length} messages` : 'online')}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button
                  onClick={() => { setOpen(false); navigate('/app/ai-mentor'); }}
                  className="h-8 px-2.5 flex items-center gap-1.5 text-xs rounded-md border hover:bg-foreground/[0.04] transition-colors text-muted-foreground hover:text-foreground"
                  style={{ borderColor: 'var(--hairline)' }}
                  title="Open full page"
                >
                  <ExternalLink className="h-3 w-3" /> Expand
                </button>
                <button
                  onClick={() => setOpen(false)}
                  data-testid={APP_SHELL.aiPanelClose}
                  className="h-8 w-8 flex items-center justify-center rounded-md border hover:bg-foreground/[0.04] transition-colors"
                  style={{ borderColor: 'var(--hairline)' }}
                  aria-label="Close AI panel"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            {m.error && (
              <div className="mx-5 mt-3 px-3 py-2 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-200 text-xs flex items-center gap-2 shrink-0">
                <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />
                <span className="flex-1">{m.error}</span>
                <button onClick={m.dismissError} className="text-[10px] font-mono uppercase tracking-wider text-rose-200/70 hover:text-rose-100">Dismiss</button>
              </div>
            )}

            {nextStep && m.messages.length === 0 && (
              <div className="mx-5 mt-3 px-3 py-2.5 rounded-lg border border-primary/25 bg-primary/[0.06] shrink-0">
                <div className="text-[10px] font-mono uppercase tracking-wider text-primary/80 mb-1">Mentor recommends next</div>
                <div className="text-sm font-medium">{nextStep.label}</div>
                <div className="text-[10px] text-muted-foreground mt-0.5">Based on your prerequisite chain</div>
              </div>
            )}

            <div ref={scrollRef} className="flex-1 overflow-y-auto overflow-x-hidden px-5 py-4 space-y-4 min-h-0">
              {m.messages.length === 0 && !m.sending && (
                <>
                  <div className="rounded-2xl rounded-tl-md px-4 py-3 bg-foreground/[0.03] border hairline text-sm">
                    I'm your PrepOS Mentor. I know your progress, weak topics, target companies and today's mission — ask me anything and I'll reason from your data.
                  </div>
                  <div className="pt-2">
                    <div className="overline mb-2">Suggested prompts</div>
                    <div className="flex flex-col gap-2">
                      {SUGGESTED.map((s) => (
                        <button
                          key={s}
                          onClick={() => setText(s)}
                          className="text-left text-sm rounded-lg border hairline bg-foreground/[0.02] hover:bg-foreground/[0.04] px-3 py-2 flex items-center gap-2 transition-colors"
                        >
                          <Wand2 className="h-3.5 w-3.5 text-primary shrink-0" />
                          <span>{s}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {m.messages.map((msg) => (
                <DrawerMessage key={msg.id} message={msg} user={user} />
              ))}

              {m.sending && (
                <div className="flex gap-3">
                  <div className="h-8 w-8 rounded-lg bg-primary/15 border border-primary/30 flex items-center justify-center">
                    <Loader2 className="h-4 w-4 text-primary animate-spin" />
                  </div>
                  <div className="rounded-2xl px-4 py-3 border hairline bg-foreground/[0.02] text-sm text-muted-foreground">
                    Mentor is thinking…
                  </div>
                </div>
              )}
            </div>

            <div className="p-4 border-t shrink-0" style={{ borderColor: 'var(--hairline)' }}>
              <div className="flex items-center justify-between mb-2">
                <label className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider cursor-pointer text-muted-foreground">
                  <input
                    type="checkbox"
                    checked={lessonMode}
                    onChange={(e) => setLessonMode(e.target.checked)}
                    className="h-3 w-3 rounded accent-primary"
                  />
                  <BookOpen className="h-3 w-3" />
                  Structured lesson (9-card)
                </label>
              </div>
              <div className="flex items-end gap-2 rounded-xl border hairline bg-foreground/[0.02] focus-within:border-primary/50 transition-colors">
                <textarea
                  data-testid={APP_SHELL.aiInput}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  autoFocus
                  placeholder={lessonMode ? 'Ask for a full lesson (e.g., "Teach me HashMap")…' : 'Ask the Mentor…'}
                  rows={2}
                  className="flex-1 resize-none bg-transparent px-3.5 py-2.5 text-sm outline-none placeholder:text-muted-foreground text-foreground"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      send();
                    }
                  }}
                />
                <button
                  onClick={send}
                  disabled={m.sending || !text.trim()}
                  data-testid={APP_SHELL.aiSendButton}
                  className="mb-2 mr-2 h-8 w-8 flex items-center justify-center rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40 transition-colors"
                >
                  {m.sending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                </button>
              </div>
              <p className="mt-2 text-[11px] text-muted-foreground font-mono">
                Grounded in your progress · Enter to send · Shift+Enter for newline
              </p>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
