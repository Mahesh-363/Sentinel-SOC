"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "../../components/layout/AppShell";
import { fetchApi } from "../../lib/api";
import {
  HelpCircle,
  Send,
  Plus,
  ThumbsUp,
  ThumbsDown,
  Sparkles,
  BookOpen,
  MessageSquare,
  Loader2,
  Terminal,
} from "lucide-react";

export default function AiHelpdeskPage() {
  const [conversations, setConversations] = useState<any[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const loadConversations = async () => {
    try {
      const data = await fetchApi("/ai-helpdesk/conversations");
      setConversations(data || []);
      if (data && data.length > 0 && !activeConvId) {
        setActiveConvId(data[0].id);
        setMessages(data[0].messages || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadConversations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSelectConv = (conv: any) => {
    setActiveConvId(conv.id);
    setMessages(conv.messages || []);
  };

  const handleSendMessage = async (customText?: string) => {
    const text = customText || inputMessage;
    if (!text.trim()) return;

    const userMsg = {
      id: `temp-${Date.now()}`,
      sender_role: "user",
      message: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputMessage("");
    setLoading(true);

    try {
      const res = await fetchApi("/ai-helpdesk/chat", {
        method: "POST",
        body: JSON.stringify({
          conversation_id: activeConvId || undefined,
          message: text,
          context_page: window.location.pathname,
        }),
      });

      setMessages((prev) => [...prev, res]);
      loadConversations();
    } catch (err: any) {
      alert(`Helpdesk error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (msgId: string, helpful: boolean) => {
    try {
      await fetchApi("/ai-helpdesk/feedback", {
        method: "POST",
        body: JSON.stringify({ message_id: msgId, is_helpful: helpful }),
      });
      alert(helpful ? "Thank you for the positive feedback!" : "Feedback recorded.");
    } catch (e) {}
  };

  const SUGGESTIONS = [
    "Why is my sensor offline?",
    "How do I install a Linux sensor with systemd?",
    "How do I enroll a Windows sensor?",
    "What does the detection rule AUTH_FAILED_BURST mean?",
    "How does Sentinel SOC classify IP addresses?",
    "How do I simulate an attack in the lab?",
  ];

  return (
    <AppShell>
      <div className="space-y-6 max-w-6xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
              <HelpCircle className="w-5 h-5 text-cyan-400" />
              Sentinel AI Helpdesk &amp; Troubleshooting Assistant
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Operational guide, error troubleshooting, and technical documentation RAG assistant
            </p>
          </div>
          <button
            onClick={() => {
              setActiveConvId(null);
              setMessages([]);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs"
          >
            <Plus className="w-4 h-4" />
            <span>New Conversation</span>
          </button>
        </div>

        {/* Chat Interface Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {/* History Column */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Previous Conversations
            </span>
            <div className="space-y-1.5 max-h-[600px] overflow-y-auto pr-1">
              {conversations.length > 0 ? (
                conversations.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => handleSelectConv(c)}
                    className={`w-full text-left p-2.5 rounded-lg text-xs transition-colors flex items-center gap-2 truncate ${
                      activeConvId === c.id
                        ? "bg-slate-900 border border-cyan-800/60 text-cyan-300 font-medium"
                        : "bg-[#0F172A] border border-slate-800 text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" />
                    <span className="truncate">{c.title}</span>
                  </button>
                ))
              ) : (
                <div className="text-xs text-slate-500 italic py-4">No previous conversations.</div>
              )}
            </div>
          </div>

          {/* Active Conversation Main Chat */}
          <div className="md:col-span-3 flex flex-col h-[650px] rounded-xl bg-[#0F172A] border border-slate-800 overflow-hidden shadow-sm">
            {/* Messages Feed */}
            <div className="flex-1 p-5 overflow-y-auto space-y-4">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4">
                  <div className="w-12 h-12 rounded-xl bg-cyan-950/80 border border-cyan-500/50 flex items-center justify-center text-cyan-400">
                    <Sparkles className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-slate-200">How can I assist you with Sentinel SOC today?</h3>
                    <p className="text-xs text-slate-400 mt-1 max-w-md">
                      Ask me how to configure sensors, troubleshoot application errors, understand SOC metrics, or deploy containers.
                    </p>
                  </div>

                  {/* Suggested Prompts */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-xl text-left pt-2">
                    {SUGGESTIONS.map((sug, i) => (
                      <button
                        key={i}
                        onClick={() => handleSendMessage(sug)}
                        className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-cyan-800/60 text-slate-300 hover:text-cyan-300 text-xs text-left transition-colors"
                      >
                        {sug}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((m, idx) => (
                  <div
                    key={m.id || idx}
                    className={`flex flex-col ${m.sender_role === "user" ? "items-end" : "items-start"}`}
                  >
                    <div
                      className={`max-w-2xl p-4 rounded-xl text-xs leading-relaxed ${
                        m.sender_role === "user"
                          ? "bg-cyan-950 border border-cyan-800/60 text-cyan-100 rounded-br-sm"
                          : "bg-slate-950 border border-slate-800 text-slate-200 rounded-bl-sm"
                      }`}
                    >
                      <div className="font-sans whitespace-pre-wrap">{m.message}</div>

                      {/* RAG Citations */}
                      {m.citations && m.citations.length > 0 && (
                        <div className="mt-3 pt-2.5 border-t border-slate-800/80 text-[11px] text-slate-400">
                          <div className="flex items-center gap-1 text-cyan-400 font-semibold mb-1">
                            <BookOpen className="w-3.5 h-3.5" />
                            <span>Referenced Sentinel Documentation:</span>
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            {m.citations.map((c: any, i: number) => (
                              <span
                                key={i}
                                className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-cyan-300 font-mono text-[10px]"
                              >
                                {c.document} &bull; {c.section}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Feedback Buttons for Assistant */}
                    {m.sender_role === "assistant" && (
                      <div className="flex items-center gap-2 mt-1 px-1 text-[11px] text-slate-500">
                        <span>Was this helpful?</span>
                        <button
                          onClick={() => handleFeedback(m.id, true)}
                          className="hover:text-cyan-400 transition-colors"
                        >
                          <ThumbsUp className="w-3 h-3" />
                        </button>
                        <button
                          onClick={() => handleFeedback(m.id, false)}
                          className="hover:text-red-400 transition-colors"
                        >
                          <ThumbsDown className="w-3 h-3" />
                        </button>
                      </div>
                    )}
                  </div>
                ))
              )}

              {loading && (
                <div className="flex items-center gap-2 text-xs text-cyan-400 italic p-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Sentinel AI Helpdesk searching documentation and formulating solution...</span>
                </div>
              )}
            </div>

            {/* Input Bar */}
            <form onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }} className="p-3 bg-slate-900/60 border-t border-slate-800 flex gap-2">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Ask how to configure Sentinel SOC, resolve an error, or install a sensor..."
                className="flex-1 px-4 py-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />
              <button
                type="submit"
                disabled={loading || !inputMessage.trim()}
                className="px-4 py-2.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs flex items-center gap-1.5 disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Send</span>
              </button>
            </form>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
