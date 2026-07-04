import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AppLayout, Header } from '../../components/Layout';
import { Button } from '../../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Badge } from '../../components/ui/badge';
import {
  MessageCircle,
  Send,
  Loader2,
  Lock,
  Sparkles,
  FileText,
  Plus,
  PanelLeftClose,
  PanelLeftOpen,
  Trash2,
  Pencil,
  Check,
  X,
} from 'lucide-react';
import { aiAPI } from '../../api';
import { toast } from 'sonner';
import { handleApiError } from '../../utils/handleApiError';
import { useAiAccess } from '../../hooks/useAiAccess';
import { useAuth, useCurrency } from '../../context/AuthContext';
import { DigestTab } from '../cashflow/components/DigestTab';

const VALID_TABS = ['chat', 'digest'];

/* ── Lightweight markdown renderer for AI responses ────────────────────────── */

function FormattedMessage({ content }) {
  if (!content) return null;

  const bold = (text) =>
    text.split(/\*\*(.+?)\*\*/g).map((part, i) =>
      i % 2 === 1 ? <strong key={i}>{part}</strong> : part
    );

  const paragraphs = content.split(/\n\n+/);

  return (
    <div className="space-y-2.5">
      {paragraphs.map((para, pi) => {
        const lines = para.split('\n');

        const isList = lines.every((l) => /^[\-\•]\s/.test(l.trim()) || !l.trim());
        if (isList) {
          const items = lines.filter((l) => /^[\-\•]\s/.test(l.trim()));
          return (
            <ul key={pi} className="list-disc list-outside pl-4 space-y-1">
              {items.map((item, li) => (
                <li key={li}>{bold(item.replace(/^[\-\•]\s*/, ''))}</li>
              ))}
            </ul>
          );
        }

        const isNumbered = lines.every((l) => /^\d+[\.\)]\s/.test(l.trim()) || !l.trim());
        if (isNumbered) {
          const items = lines.filter((l) => /^\d+[\.\)]\s/.test(l.trim()));
          return (
            <ol key={pi} className="list-decimal list-outside pl-4 space-y-1">
              {items.map((item, li) => (
                <li key={li}>{bold(item.replace(/^\d+[\.\)]\s*/, ''))}</li>
              ))}
            </ol>
          );
        }

        return (
          <p key={pi}>
            {lines.map((line, li) => (
              <React.Fragment key={li}>
                {li > 0 && <br />}
                {bold(line)}
              </React.Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
}

/* ── Date grouping helper ──────────────────────────────────────────────────── */

function groupSessionsByDate(sessions, t) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
  const last7 = new Date(today); last7.setDate(today.getDate() - 7);

  const groups = {};
  for (const s of sessions) {
    const d = new Date(s.updated_at || s.created_at);
    let label;
    if (d >= today) label = t('chat.today');
    else if (d >= yesterday) label = t('chat.yesterday');
    else if (d >= last7) label = t('chat.last_7_days');
    else label = t('chat.older');

    if (!groups[label]) groups[label] = [];
    groups[label].push(s);
  }
  return groups;
}

/* ── Session Sidebar ───────────────────────────────────────────────────────── */

const SessionSidebar = ({ sessions, activeSessionId, onSelect, onNew, onDelete, onRename, open, onToggle, t }) => {
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const editRef = useRef(null);

  useEffect(() => {
    if (editingId && editRef.current) editRef.current.focus();
  }, [editingId]);

  const startRename = (s) => {
    setEditingId(s.session_id);
    setEditTitle(s.title || '');
  };

  const confirmRename = () => {
    if (editTitle.trim() && editingId) {
      onRename(editingId, editTitle.trim());
    }
    setEditingId(null);
  };

  const grouped = groupSessionsByDate(sessions, t);

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-black/30 z-30 md:hidden"
          onClick={onToggle}
        />
      )}

      <div
        className={`
          ${open ? 'translate-x-0' : '-translate-x-full md:translate-x-0 md:w-0 md:min-w-0 md:overflow-hidden'}
          fixed md:relative z-40 md:z-auto
          top-0 left-0 h-full md:h-auto
          w-72 md:w-64 min-w-[18rem] md:min-w-0
          bg-card border-r flex flex-col
          transition-all duration-200 ease-in-out
          ${open ? 'md:w-64 md:min-w-[16rem]' : ''}
        `}
      >
        {/* Header */}
        <div className="flex items-center gap-2 p-3 border-b flex-shrink-0">
          <Button
            variant="outline"
            size="sm"
            className="flex-1 gap-2 justify-start"
            onClick={onNew}
          >
            <Plus className="h-4 w-4" />
            {t('chat.new_chat')}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0 hidden md:flex"
            onClick={onToggle}
          >
            <PanelLeftClose className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0 md:hidden"
            onClick={onToggle}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Session list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-3">
          {sessions.length === 0 && (
            <p className="text-xs text-muted-foreground text-center py-4">
              {t('chat.no_sessions')}
            </p>
          )}
          {Object.entries(grouped).map(([label, items]) => (
            <div key={label}>
              <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide px-2 mb-1">
                {label}
              </p>
              {items.map((s) => (
                <div
                  key={s.session_id}
                  className={`
                    group flex items-center gap-1 rounded-lg px-2.5 py-2 cursor-pointer text-sm
                    ${s.session_id === activeSessionId
                      ? 'bg-primary/10 text-primary font-medium'
                      : 'hover:bg-muted text-foreground'}
                  `}
                  onClick={() => {
                    if (editingId !== s.session_id) onSelect(s.session_id);
                  }}
                >
                  {editingId === s.session_id ? (
                    <div className="flex items-center gap-1 flex-1 min-w-0">
                      <input
                        ref={editRef}
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') confirmRename();
                          if (e.key === 'Escape') setEditingId(null);
                        }}
                        className="flex-1 min-w-0 text-sm bg-background border rounded px-1.5 py-0.5"
                        onClick={(e) => e.stopPropagation()}
                      />
                      <button onClick={(e) => { e.stopPropagation(); confirmRename(); }} className="p-0.5 hover:text-primary">
                        <Check className="h-3.5 w-3.5" />
                      </button>
                      <button onClick={(e) => { e.stopPropagation(); setEditingId(null); }} className="p-0.5 hover:text-destructive">
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ) : (
                    <>
                      <MessageCircle className="h-3.5 w-3.5 flex-shrink-0 opacity-50" />
                      <span className="flex-1 truncate">{s.title || 'Chat'}</span>
                      <div className="hidden group-hover:flex items-center gap-0.5 flex-shrink-0">
                        <button
                          onClick={(e) => { e.stopPropagation(); startRename(s); }}
                          className="p-1 rounded hover:bg-background"
                          title={t('chat.rename')}
                        >
                          <Pencil className="h-3 w-3" />
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); onDelete(s.session_id); }}
                          className="p-1 rounded hover:bg-destructive/10 hover:text-destructive"
                          title={t('chat.delete')}
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </>
  );
};

/* ── Chat Tab ──────────────────────────────────────────────────────────────── */

const ChatTab = () => {
  const { t } = useTranslation('ai_analysis');
  const { user } = useAuth();
  const { aiEnabled, canUse, quotaExhausted, usage, limits, refresh } =
    useAiAccess();
  const navigateTo = useNavigate();

  // Session state
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth >= 768);

  // Chat state
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const chatDisabled = !canUse('chat');

  const suggestions = t('chat.suggestions', { returnObjects: true });

  /* ── Load sessions on mount ── */
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await aiAPI.listSessions();
        if (cancelled) return;
        const list = res.data || [];
        setSessions(list);
        if (list.length > 0) {
          setActiveSessionId(list[0].session_id);
        }
      } catch {
        // No sessions yet
      }
    };
    load();
    return () => { cancelled = true; };
  }, []);

  /* ── Load history when session changes ── */
  useEffect(() => {
    if (!activeSessionId) {
      setMessages([]);
      setHistoryLoaded(true);
      return;
    }
    let cancelled = false;
    const loadHistory = async () => {
      setHistoryLoaded(false);
      try {
        const res = await aiAPI.getHistory(activeSessionId);
        if (!cancelled && res.data?.messages?.length > 0) {
          setMessages(res.data.messages);
        } else if (!cancelled) {
          setMessages([]);
        }
      } catch {
        if (!cancelled) setMessages([]);
      } finally {
        if (!cancelled) setHistoryLoaded(true);
      }
    };
    loadHistory();
    return () => { cancelled = true; };
  }, [activeSessionId]);

  /* Auto-scroll to bottom on new messages */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  /* Focus textarea on mount */
  useEffect(() => {
    if (historyLoaded) textareaRef.current?.focus();
  }, [historyLoaded]);

  /* Auto-resize textarea */
  const autoResize = useCallback(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 96) + 'px';
  }, []);

  useEffect(() => {
    autoResize();
  }, [input, autoResize]);

  /* ── Session actions ── */
  const handleNewSession = async () => {
    try {
      const res = await aiAPI.createSession();
      const newId = res.data.session_id;
      setActiveSessionId(newId);
      setMessages([]);
      if (window.innerWidth < 768) setSidebarOpen(false);
    } catch {
      toast.error('Error creating session');
    }
  };

  const handleSelectSession = (sessionId) => {
    if (window.innerWidth < 768) setSidebarOpen(false);
    if (sessionId === activeSessionId) return;
    setActiveSessionId(sessionId);
  };

  const handleDeleteSession = async (sessionId) => {
    if (!window.confirm(t('chat.delete_confirm'))) return;
    try {
      await aiAPI.deleteSession(sessionId);
      setSessions((prev) => {
        const remaining = prev.filter((s) => s.session_id !== sessionId);
        if (sessionId === activeSessionId) {
          if (remaining.length > 0) {
            setActiveSessionId(remaining[0].session_id);
          } else {
            setActiveSessionId(null);
            setMessages([]);
          }
        }
        return remaining;
      });
    } catch {
      toast.error('Error deleting session');
    }
  };

  const handleRenameSession = async (sessionId, title) => {
    try {
      await aiAPI.renameSession(sessionId, title);
      setSessions((prev) =>
        prev.map((s) => (s.session_id === sessionId ? { ...s, title } : s))
      );
    } catch {
      toast.error('Error renaming session');
    }
  };

  /* ── Send message ── */
  const handleSend = async (text) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;

    // If no active session, create one first
    let sessionId = activeSessionId;
    if (!sessionId) {
      try {
        const res = await aiAPI.createSession();
        sessionId = res.data.session_id;
        setActiveSessionId(sessionId);
      } catch {
        toast.error('Error creating session');
        return;
      }
    }

    const userMsg = { role: 'user', content: msg };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    try {
      let periodCtx;
      try { periodCtx = JSON.parse(localStorage.getItem('cashflow_active_period')); } catch {}
      const res = await aiAPI.chat(msg, sessionId, periodCtx || undefined);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.data.reply },
      ]);
      refresh();

      // Update session list
      setSessions((prev) => {
        const exists = prev.find((s) => s.session_id === sessionId);
        if (exists) {
          return [
            { ...exists, updated_at: new Date().toISOString() },
            ...prev.filter((s) => s.session_id !== sessionId),
          ];
        }
        return [
          {
            session_id: sessionId,
            title: msg.slice(0, 60),
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
          ...prev,
        ];
      });
    } catch (err) {
      // v5.8 / Onda 9.O — handleApiError respects __handled_by_paywall flag.
      // For QUOTA_EXCEEDED on ai_assistant.chat (Free user out of 3 messages),
      // QuotaExceededPaywall opens automatically with localized "Limite chat
      // AI raggiunto" + "Aggiorna piano" CTA. We skip the local toast to
      // avoid covering the modal with a generic error.
      handleApiError(err, t('chat.error'));
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  /* ── AI locked state ── */
  if (!aiEnabled) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 text-center px-4">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
          <Lock className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="mt-4 font-heading text-lg font-semibold">
          {t('chat.locked_title')}
        </h3>
        <p className="mt-2 max-w-md text-sm text-muted-foreground">
          {t('chat.locked_desc')}
        </p>
        <Button className="mt-6" onClick={() => navigateTo('/plans')}>
          {t('chat.locked_cta')}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-1 min-h-0">
      {/* Sidebar */}
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={handleSelectSession}
        onNew={handleNewSession}
        onDelete={handleDeleteSession}
        onRename={handleRenameSession}
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((v) => !v)}
        t={t}
      />

      {/* Main chat area */}
      <div className="flex flex-col flex-1 min-h-0 min-w-0">
        {/* Toolbar: sidebar toggle + quota */}
        <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30 flex-shrink-0">
          <div className="flex items-center gap-2">
            {!sidebarOpen && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 hidden md:flex"
                onClick={() => setSidebarOpen(true)}
              >
                <PanelLeftOpen className="h-4 w-4" />
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0 md:hidden"
              onClick={() => setSidebarOpen((v) => !v)}
            >
              {sidebarOpen ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
            </Button>
          </div>
          {limits.chat > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">
                {t('chat.quota_label')}
              </span>
              <Badge
                variant="outline"
                className={`text-xs ${
                  quotaExhausted('chat')
                    ? 'border-amber-300 text-amber-700 bg-amber-50'
                    : ''
                }`}
              >
                {usage.chat ?? 0} / {limits.chat}
              </Badge>
            </div>
          )}
        </div>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 min-h-0">
          {messages.length === 0 && historyLoaded && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 mb-4">
                <Sparkles className="h-6 w-6 text-primary" />
              </div>
              <h3 className="font-heading text-base font-semibold">
                {t('chat.empty_title')}
              </h3>
              <p className="mt-1 text-sm text-muted-foreground max-w-md">
                {t('chat.empty_desc')}
              </p>
              <div className="mt-6 flex flex-col sm:flex-row sm:flex-wrap justify-center gap-2 w-full sm:w-auto px-2 sm:px-0">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => handleSend(s)}
                    disabled={chatDisabled}
                    className="rounded-full border border-border bg-card px-4 py-2.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors disabled:opacity-50 text-left sm:text-center"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] md:max-w-[70%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-primary text-primary-foreground rounded-tr-md whitespace-pre-wrap'
                    : 'bg-muted text-foreground rounded-tl-md'
                }`}
              >
                {msg.role === 'assistant' ? <FormattedMessage content={msg.content} /> : msg.content}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-muted rounded-2xl rounded-tl-md px-4 py-3">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input bar */}
        <div className="border-t bg-card px-4 py-3 flex-shrink-0" style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}>
          <div className="flex items-end gap-3 max-w-3xl mx-auto">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading || chatDisabled}
              placeholder={
                chatDisabled
                  ? t('chat.placeholder_disabled')
                  : t('chat.placeholder')
              }
              rows={1}
              className="flex-1 min-h-[2.5rem] max-h-[6rem] px-4 py-2.5 text-[16px] leading-snug rounded-xl border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring resize-none overflow-y-auto"
            />
            <Button
              size="sm"
              className="h-10 w-10 p-0 rounded-xl flex-shrink-0"
              onClick={() => handleSend()}
              disabled={!input.trim() || loading || chatDisabled}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ── Main Page ─────────────────────────────────────────────────────────────── */

export const AnalisiAIPage = () => {
  const { t } = useTranslation('ai_analysis');
  const { tab } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const currency = useCurrency();
  const isAdmin = user?.role === 'admin' || user?.role === 'system_admin';

  const activeTab = VALID_TABS.includes(tab) ? tab : 'chat';

  const handleTabChange = (newTab) => {
    navigate(`/analisi-ai/${newTab}`, { replace: true });
  };

  return (
    <AppLayout>
      <div className="fixed inset-0 md:left-64 flex flex-col">
        <Header
          title={t('page.title')}
          subtitle={t('page.subtitle')}
        />

        <div className="flex-1 flex flex-col min-h-0 animate-fade-in">
          <Tabs
            value={activeTab}
            onValueChange={handleTabChange}
            className="flex-1 flex flex-col min-h-0"
          >
            <div className="z-20 bg-background border-b px-4 md:px-8 flex-shrink-0">
              <TabsList className="w-full md:w-auto">
                <TabsTrigger
                  value="chat"
                  className="flex-1 md:flex-none gap-2 px-4"
                >
                  <MessageCircle className="h-4 w-4" />
                  {t('tabs.chat')}
                </TabsTrigger>
                <TabsTrigger
                  value="digest"
                  className="flex-1 md:flex-none gap-2 px-4"
                >
                  <FileText className="h-4 w-4" />
                  {t('tabs.digest')}
                </TabsTrigger>
              </TabsList>
            </div>

            <TabsContent
              value="chat"
              className="flex-1 flex flex-col min-h-0 mt-0 data-[state=inactive]:hidden"
            >
              <ChatTab />
            </TabsContent>

            <TabsContent
              value="digest"
              className="flex-1 overflow-y-auto mt-0 data-[state=inactive]:hidden"
            >
              <div className="p-4 md:p-8">
                <DigestTab isAdmin={isAdmin} currency={currency} />
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </AppLayout>
  );
};

export default AnalisiAIPage;
