import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { MessageCircle, Send, X, Loader2, Lock } from 'lucide-react';
import { Button } from '../../../components/ui/button';
import { aiAPI } from '../../../api';
import { toast } from 'sonner';
import { useAiAccess } from '../../../hooks/useAiAccess';
import { useNavigate } from 'react-router-dom';

export const ChatWidget = ({ context }) => {
  const { t } = useTranslation('ai_analysis');
  const { aiEnabled, canUse, quotaExhausted, usage, limits, refresh } = useAiAccess();
  const navigateTo = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const chatDisabled = !canUse('chat');

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await aiAPI.chat(text, sessionId, context);
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.reply }]);
      refresh(); // update quota counter
    } catch (err) {
      const raw = err?.response?.data?.detail;
      const message = typeof raw === 'object' ? raw?.message : raw;
      toast.error(message || t('chat.error'));
      // Remove the user message on failure
      setMessages(prev => prev.slice(0, -1));
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

  if (!isOpen) {
    return (
      <>
        <button
          onClick={() => !aiEnabled ? navigateTo('/plans') : setIsOpen(true)}
          className={`fixed bottom-6 right-6 z-50 h-14 w-14 rounded-full shadow-lg hover:shadow-xl transition-shadow flex items-center justify-center ${
            !aiEnabled
              ? 'bg-muted text-muted-foreground'
              : 'bg-primary text-primary-foreground'
          }`}
          aria-label={!aiEnabled ? t('chat.widget_aria_locked') : t('chat.widget_aria_open')}
        >
          {!aiEnabled ? <Lock className="h-6 w-6" /> : <MessageCircle className="h-6 w-6" />}
        </button>
      </>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-[360px] h-[480px] flex flex-col bg-card border border-border rounded-2xl shadow-2xl overflow-hidden">
      {/* Header */}
      <div className="border-b bg-muted/50">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <MessageCircle className="h-4 w-4 text-primary" />
            <span className="text-sm font-semibold">{t('chat.widget_title')}</span>
          </div>
          <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => setIsOpen(false)}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        {quotaExhausted('chat') && (
          <div className="px-4 pb-2">
            <p className="text-[11px] text-amber-700 bg-amber-50 rounded px-2 py-1">
              {t('chat.widget_quota_alert', { used: usage.chat, limit: limits.chat })}
            </p>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-xs text-muted-foreground mt-8">
            <p className="font-medium mb-1">{t('chat.widget_empty_title')}</p>
            <p>{t('chat.widget_empty_hint')}</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] rounded-xl px-3 py-2 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-foreground'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-muted rounded-xl px-3 py-2">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-3 py-2 border-t bg-card">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading || chatDisabled}
            placeholder={chatDisabled ? t('chat.widget_placeholder_disabled') : t('chat.widget_placeholder')}
            className="flex-1 h-9 px-3 text-sm rounded-lg border border-input bg-background focus:outline-none focus:ring-1 focus:ring-ring"
          />
          <Button
            size="sm"
            className="h-9 w-9 p-0"
            onClick={handleSend}
            disabled={!input.trim() || loading || chatDisabled}
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ChatWidget;
