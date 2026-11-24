"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { AppShell } from "../../components/layout/AppShell";
import { fetchApi } from "../../lib/api";
import {
  Bot,
  Shield,
  Sparkles,
  Send,
  Loader2,
  FileCheck,
  AlertOctagon,
  Globe,
  Server,
  Info,
} from "lucide-react";

function AiAnalystContent() {
  const searchParams = useSearchParams();
  const [targetType, setTargetType] = useState(searchParams.get("type") || "general");
  const [targetId, setTargetId] = useState(searchParams.get("target") || "");
  const [query, setQuery] = useState(searchParams.get("query") || "");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<any | null>(null);

  const handleInvestigate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setLoading(true);
    try {
      const res = await fetchApi("/ai-analyst/investigate", {
        method: "POST",
        body: JSON.stringify({
          target_type: targetType,
          target_id: targetId || undefined,
          query: query || undefined,
        }),
      });
      setResponse(res);
    } catch (err: any) {
      alert(`AI Analyst error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (searchParams.get("target") || searchParams.get("query")) {
      handleInvestigate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
            <Bot className="w-5 h-5 text-cyan-400" />
            Sentinel AI Security Analyst
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Grounded, advisory AI assistant for threat analysis, alert correlation, and incident investigation
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/40 text-cyan-300 text-xs font-mono">
          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
          <span>Advisory AI &bull; Human-in-the-Loop</span>
        </div>
      </div>

      {/* Investigation Query Form */}
      <div className="p-5 rounded-xl bg-[#0F172A] border border-slate-800 shadow-sm space-y-4">
        <form onSubmit={handleInvestigate} className="space-y-4 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-300 font-semibold mb-1">Investigation Scope / Target</label>
              <select
                value={targetType}
                onChange={(e) => setTargetType(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="general">General SOC Query / Telemetry Guidance</option>
                <option value="ip">Public / Private IP Investigation</option>
                <option value="alert">Specific Alert / Detection Result</option>
                <option value="incident">Active Incident Case</option>
                <option value="asset">Monitored Asset Risk Profile</option>
              </select>
            </div>

            {targetType !== "general" && (
              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Target Identifier (IP, Alert ID, Incident ID, or Hostname)
                </label>
                <input
                  type="text"
                  required
                  value={targetId}
                  onChange={(e) => setTargetId(e.target.value)}
                  placeholder="e.g. 185.220.101.5 or INC-01"
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                />
              </div>
            )}
          </div>

          <div>
            <label className="block text-slate-300 font-semibold mb-1">
              Specific Question or Investigation Focus (Optional)
            </label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. What evidence indicates this is a brute-force attack? What containment steps should I take?"
              className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex justify-between items-center pt-2">
            <span className="text-[11px] text-slate-500">
              AI operates strictly on authorized telemetry inside your active organization tenant.
            </span>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs flex items-center gap-2 transition-colors disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Analyzing Authorized Telemetry...</span>
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>Execute Investigation</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* AI Analysis Report */}
      {response && (
        <div className="p-6 rounded-xl bg-[#0F172A] border border-slate-800 space-y-4 shadow-md">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <FileCheck className="w-5 h-5 text-cyan-400" />
              <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                Advisory Security Investigation Briefing
              </h2>
            </div>
            <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400">
              <span>Model: {response.model}</span>
              <span>&bull;</span>
              <span className="text-cyan-400">{response.provider.toUpperCase()}</span>
            </div>
          </div>

          <div className="text-xs text-slate-200 leading-relaxed font-sans whitespace-pre-wrap bg-slate-950/70 p-5 rounded-lg border border-slate-800">
            {response.analysis}
          </div>

          {response.evidence_sources?.length > 0 && (
            <div className="pt-2 text-xs text-slate-400">
              <span className="font-semibold text-slate-300">Verified Evidence Sources:</span>
              <div className="flex flex-wrap gap-2 mt-1">
                {response.evidence_sources.map((src: string, i: number) => (
                  <span key={i} className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-cyan-300 font-mono text-[11px]">
                    {src}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AiAnalystPage() {
  return (
    <AppShell>
      <Suspense fallback={
        <div className="p-8 flex items-center justify-center text-slate-400 text-xs">
          <Loader2 className="w-5 h-5 animate-spin mr-2 text-cyan-400" />
          Loading AI Security Analyst...
        </div>
      }>
        <AiAnalystContent />
      </Suspense>
    </AppShell>
  );
}
