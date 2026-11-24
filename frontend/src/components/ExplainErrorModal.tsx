"use client";

import React, { useState } from "react";
import { AlertCircle, HelpCircle, Shield, Check, Loader2, ArrowRight } from "lucide-react";
import { fetchApi } from "../lib/api";

interface ExplainErrorModalProps {
  isOpen: boolean;
  onClose: () => void;
  errorMessage: string;
  moduleName: string;
  errorCode?: string;
  contextData?: Record<string, any>;
}

export function ExplainErrorModal({
  isOpen,
  onClose,
  errorMessage,
  moduleName,
  errorCode = "ERR_APP_GENERAL",
  contextData = {},
}: ExplainErrorModalProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [shareConsent, setShareConsent] = useState(true);

  if (!isOpen) return null;

  const handleExplain = async () => {
    setLoading(true);
    try {
      const sanitizedPayload = shareConsent ? contextData : {};
      const res = await fetchApi("/ai-helpdesk/explain-error", {
        method: "POST",
        body: JSON.stringify({
          error_message: errorMessage,
          module_name: moduleName,
          error_code: errorCode,
          context_data: sanitizedPayload,
        }),
      });
      setResult(res);
    } catch (e: any) {
      setResult({
        explanation: `Unable to query Helpdesk: ${e.message}. Sentinel SOC core operations remain fully active.`,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-2xl rounded-xl border border-slate-800 bg-[#0B1120] p-6 shadow-2xl text-slate-200">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-950/60 border border-cyan-800/40 text-cyan-400">
              <HelpCircle className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-100">Explain This Error</h2>
              <p className="text-xs text-slate-400">Sentinel AI Helpdesk Technical Diagnostic Workflow</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 text-sm px-2 py-1 rounded bg-slate-900 border border-slate-800"
          >
            ✕
          </button>
        </div>

        <div className="mt-4 space-y-4">
          <div className="p-3 rounded-lg bg-red-950/30 border border-red-900/40 text-red-300 text-sm flex gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-400" />
            <div>
              <div className="font-semibold text-xs text-red-400 uppercase tracking-wider">
                {moduleName} &bull; {errorCode}
              </div>
              <p className="mt-0.5 font-mono text-xs">{errorMessage}</p>
            </div>
          </div>

          {!result ? (
            <div>
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-300 space-y-2">
                <div className="flex items-center gap-2 text-cyan-400 font-medium">
                  <Shield className="w-4 h-4" />
                  Diagnostic Privacy &amp; Sanitization Guarantee
                </div>
                <p>
                  Before requesting technical guidance from the AI Helpdesk, all passwords, API keys, JWT tokens, and credentials are automatically stripped and redacted.
                </p>
                <label className="flex items-center gap-2 cursor-pointer pt-1 text-slate-200">
                  <input
                    type="checkbox"
                    checked={shareConsent}
                    onChange={(e) => setShareConsent(e.target.checked)}
                    className="rounded bg-slate-950 border-slate-700 text-cyan-500 focus:ring-0"
                  />
                  <span>Include sanitized application context (recommended for exact troubleshooting)</span>
                </label>
              </div>

              <div className="flex justify-end gap-3 mt-6">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-medium rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-900"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleExplain}
                  disabled={loading}
                  className="px-4 py-2 text-xs font-medium rounded-lg bg-cyan-500 text-slate-950 hover:bg-cyan-400 font-semibold flex items-center gap-2 disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Analyzing with AI Helpdesk...
                    </>
                  ) : (
                    <>
                      Explain &amp; Troubleshoot
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="max-h-80 overflow-y-auto p-4 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-200 leading-relaxed whitespace-pre-wrap font-sans">
                {result.explanation}
              </div>

              {result.citations && result.citations.length > 0 && (
                <div className="text-xs text-slate-400">
                  <span className="font-semibold text-slate-300">Approved Documentation Referenced:</span>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {result.citations.map((c: any, idx: number) => (
                      <span key={idx} className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-cyan-400 font-mono text-[11px]">
                        {c.document} ({c.section})
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700"
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
