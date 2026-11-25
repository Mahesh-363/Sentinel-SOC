"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "../../components/layout/AppShell";
import { fetchApi } from "../../lib/api";
import { formatLocalDateTime, formatLocalTime } from "../../lib/date";
import {
  ShieldAlert,
  ShieldCheck,
  ToggleLeft,
  ToggleRight,
  Bot,
  RefreshCw,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Sparkles,
  GitMerge,
  Sliders,
  CheckCircle2,
  Clock,
  Layers,
  ArrowRight
} from "lucide-react";

export default function DetectionsPage() {
  const [tab, setTab] = useState<"alerts" | "rules" | "correlations">("alerts");
  const [alerts, setAlerts] = useState<any[]>([]);
  const [rules, setRules] = useState<any[]>([]);
  const [correlations, setCorrelations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedAlertId, setExpandedAlertId] = useState<string | null>(null);

  // Correlation trigger state
  const [correlating, setCorrelating] = useState(false);
  const [correlationMsg, setCorrelationMsg] = useState<string | null>(null);

  // Rule parameters edit modal
  const [editRule, setEditRule] = useState<any | null>(null);
  const [editThreshold, setEditThreshold] = useState<number>(5);
  const [editWindow, setEditWindow] = useState<number>(300);
  const [editSeverity, setEditSeverity] = useState<string>("High");
  const [savingRule, setSavingRule] = useState(false);

  const loadData = async () => {
    try {
      const [alertsData, rulesData, corrData] = await Promise.all([
        fetchApi("/detections/alerts"),
        fetchApi("/detections/rules"),
        fetchApi("/detections/correlations")
      ]);
      setAlerts(alertsData || []);
      setRules(rulesData || []);
      setCorrelations(corrData || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggleRule = async (ruleId: string, currentEnabled: boolean) => {
    try {
      await fetchApi(`/detections/rules/${ruleId}/toggle?enabled=${!currentEnabled}`, {
        method: "PATCH",
      });
      loadData();
    } catch (err: any) {
      alert(`Error toggling rule: ${err.message}`);
    }
  };

  const handleOpenEditRule = (rule: any) => {
    setEditRule(rule);
    setEditThreshold(rule.threshold || 5);
    setEditWindow(rule.time_window_seconds || 300);
    setEditSeverity(rule.severity || "High");
  };

  const handleSaveRuleParameters = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editRule) return;
    setSavingRule(true);
    try {
      await fetchApi(`/detections/rules/${editRule.id}/parameters`, {
        method: "PUT",
        body: JSON.stringify({
          threshold: Number(editThreshold),
          time_window_seconds: Number(editWindow),
          severity: editSeverity,
          is_enabled: editRule.is_enabled
        })
      });
      setEditRule(null);
      loadData();
    } catch (err: any) {
      alert(`Failed to update rule parameters: ${err.message}`);
    } finally {
      setSavingRule(false);
    }
  };

  const handleTriggerCorrelation = async () => {
    setCorrelating(true);
    setCorrelationMsg(null);
    try {
      const res = await fetchApi("/detections/correlate?window_seconds=1800", { method: "POST" });
      setCorrelationMsg(res.message || "Attack correlation cycle completed.");
      loadData();
    } catch (err: any) {
      alert(`Correlation failed: ${err.message}`);
    } finally {
      setCorrelating(false);
    }
  };

  const handleUpdateAlertStatus = async (alertId: string, newStatus: string) => {
    try {
      await fetchApi(`/detections/alerts/${alertId}/status?new_status=${encodeURIComponent(newStatus)}`, {
        method: "PATCH",
      });
      loadData();
    } catch (err: any) {
      alert(`Failed to update status: ${err.message}`);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-cyan-400" />
              Detection Center &amp; Threat Rules Engine
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Deterministic detection rules, multi-stage correlation chains, and real-time alert triage.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleTriggerCorrelation}
              disabled={correlating}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-950 border border-cyan-800 text-cyan-300 hover:bg-cyan-900/60 text-xs font-semibold disabled:opacity-50 transition-colors"
            >
              <GitMerge className="w-3.5 h-3.5 text-cyan-400" />
              <span>{correlating ? "Correlating Events..." : "Run Attack Correlation"}</span>
            </button>
            <button
              onClick={loadData}
              className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-cyan-400"
              title="Refresh detections"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {correlationMsg && (
          <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-900/50 text-emerald-300 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>{correlationMsg}</span>
          </div>
        )}

        {/* Tab switch */}
        <div className="flex gap-2 border-b border-slate-800 pb-2">
          <button
            onClick={() => setTab("alerts")}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 ${
              tab === "alerts"
                ? "bg-cyan-950 text-cyan-300 border border-cyan-800/60"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Threat Alerts ({alerts.length})</span>
          </button>
          <button
            onClick={() => setTab("correlations")}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 ${
              tab === "correlations"
                ? "bg-cyan-950 text-cyan-300 border border-cyan-800/60"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <GitMerge className="w-3.5 h-3.5" />
            <span>Correlated Attack Chains ({correlations.length})</span>
          </button>
          <button
            onClick={() => setTab("rules")}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 ${
              tab === "rules"
                ? "bg-cyan-950 text-cyan-300 border border-cyan-800/60"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Configured Rules ({rules.length})</span>
          </button>
        </div>

        {tab === "alerts" ? (
          /* Alerts Table */
          <div className="rounded-xl bg-[#0F172A] border border-slate-800 overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                  <th className="py-3 px-4 w-8"></th>
                  <th className="py-3 px-4">Alert Title &amp; Detection Rule</th>
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Confidence</th>
                  <th className="py-3 px-4">Related IP / Host</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Triggered At</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {alerts.length > 0 ? (
                  alerts.map((al) => {
                    const isExpanded = expandedAlertId === al.id;
                    let evidence: any = {};
                    try {
                      evidence = JSON.parse(al.evidence_json || "{}");
                    } catch {}

                    return (
                      <React.Fragment key={al.id}>
                        <tr className="hover:bg-slate-900/40 transition-colors">
                          <td className="py-3 px-4">
                            <button
                              onClick={() => setExpandedAlertId(isExpanded ? null : al.id)}
                              className="text-slate-400 hover:text-cyan-400"
                            >
                              {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                            </button>
                          </td>
                          <td className="py-3 px-4">
                            <div className="font-semibold text-slate-200 flex items-center gap-2">
                              <span>{al.title}</span>
                              {al.is_simulated && (
                                <span className="text-[9px] px-1 py-0.2 rounded font-bold bg-purple-950 text-purple-300 border border-purple-800">
                                  SIMULATED
                                </span>
                              )}
                            </div>
                            <div className="text-[11px] text-cyan-400 font-mono mt-0.5">{al.rule_name}</div>
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                al.severity === "Critical"
                                  ? "bg-red-950 text-red-400 border border-red-800/40"
                                  : al.severity === "High"
                                  ? "bg-orange-950 text-orange-400 border border-orange-800/40"
                                  : al.severity === "Medium"
                                  ? "bg-amber-950 text-amber-400 border border-amber-800/40"
                                  : "bg-slate-800 text-slate-300"
                              }`}
                            >
                              {al.severity}
                            </span>
                          </td>
                          <td className="py-3 px-4 font-mono text-slate-300">{al.confidence}%</td>
                          <td className="py-3 px-4 font-mono text-cyan-300 text-[11px]">{al.related_ip || "Internal Asset"}</td>
                          <td className="py-3 px-4">
                            <select
                              value={al.status}
                              onChange={(e) => handleUpdateAlertStatus(al.id, e.target.value)}
                              className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-[11px] text-slate-300 focus:outline-none focus:border-cyan-500"
                            >
                              <option value="Open">Open</option>
                              <option value="In Review">In Review</option>
                              <option value="Converted to Incident">Converted to Incident</option>
                              <option value="False Positive">False Positive</option>
                              <option value="Resolved">Resolved</option>
                            </select>
                          </td>
                          <td className="py-3 px-4 text-slate-400 font-mono text-[11px] whitespace-nowrap">
                            {formatLocalDateTime(al.timestamp)}
                          </td>
                          <td className="py-3 px-4 text-right">
                            <a
                              href={`/ai-analyst?type=alert&target=${al.id}`}
                              className="px-2.5 py-1 rounded bg-cyan-950 border border-cyan-800/60 text-cyan-300 hover:bg-cyan-900/60 font-medium inline-flex items-center gap-1.5 text-[11px]"
                            >
                              <Bot className="w-3.5 h-3.5 text-cyan-400" />
                              <span>AI Triage</span>
                            </a>
                          </td>
                        </tr>

                        {isExpanded && (
                          <tr className="bg-slate-950/80">
                            <td colSpan={8} className="p-4">
                              <div className="space-y-3 text-xs">
                                <div>
                                  <span className="font-semibold text-slate-300">Detailed Evidence:</span>
                                  <p className="text-slate-400 mt-1 leading-relaxed">{al.description}</p>
                                </div>
                                <div>
                                  <span className="font-semibold text-slate-400 font-mono text-[11px]">Structured Indicators:</span>
                                  <pre className="mt-1 p-2.5 rounded bg-slate-900 border border-slate-800 text-cyan-300 font-mono text-[11px] overflow-x-auto">
                                    {JSON.stringify(evidence, null, 2)}
                                  </pre>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-500 text-xs">
                      {loading ? "Loading alerts..." : "No active alerts in this organization."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        ) : tab === "correlations" ? (
          /* Correlated Attack Chains Tab */
          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 text-xs text-slate-300">
              <span className="font-semibold text-slate-200">Attack Chain Correlation Engine:</span>
              <p className="text-slate-400 mt-1">
                Sentinel automatically chains individual security events occurring within sliding temporal windows (e.g. initial brute force followed by C2 beacon, or multi-host credential spraying).
              </p>
            </div>

            {correlations.length > 0 ? (
              <div className="grid grid-cols-1 gap-4">
                {correlations.map((grp) => (
                  <div key={grp.id} className="p-5 rounded-xl bg-[#0F172A] border border-cyan-800/40 text-xs space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                      <div className="flex items-center gap-2">
                        <GitMerge className="w-4 h-4 text-cyan-400" />
                        <span className="font-bold text-slate-100 text-sm">{grp.title}</span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-red-950 text-red-300 border border-red-800/60">
                        {grp.severity} Severity Chain
                      </span>
                    </div>

                    <p className="text-slate-300 leading-relaxed">{grp.description}</p>
                    <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-[11px] text-cyan-300 font-mono">
                      {grp.explanation}
                    </div>

                    <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-400 pt-1">
                      <span>Window: {formatLocalTime(grp.time_window_start)} &rarr; {formatLocalTime(grp.time_window_end)}</span>
                      <span>{grp.event_ids?.length || 0} Events Chained</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-12 text-center text-slate-500 text-xs bg-[#0F172A] rounded-xl border border-slate-800">
                No active multi-stage correlation chains detected in current window. Click &quot;Run Attack Correlation&quot; to evaluate recent events.
              </div>
            )}
          </div>
        ) : (
          /* Rules Table */
          <div className="rounded-xl bg-[#0F172A] border border-slate-800 overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                  <th className="py-3 px-4">Rule Code</th>
                  <th className="py-3 px-4">Name &amp; Description</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Default Severity</th>
                  <th className="py-3 px-4">Threshold / Window</th>
                  <th className="py-3 px-4 text-right">Tune &amp; Toggle</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {rules.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-900/40 transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-cyan-300">
                      <div>{r.rule_code}</div>
                      {r.is_correlation_rule && (
                        <span className="text-[9px] px-1 py-0.2 rounded font-bold bg-cyan-950 text-cyan-300 border border-cyan-800 mt-1 inline-block">
                          CORRELATION
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-200">{r.name}</div>
                      <p className="text-[11px] text-slate-400 mt-0.5 max-w-md">{r.description}</p>
                    </td>
                    <td className="py-3 px-4 text-slate-300">{r.category}</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300">
                        {r.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-400">
                      {r.threshold} hits / {r.time_window_seconds}s
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleOpenEditRule(r)}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-cyan-400 border border-slate-700"
                          title="Tune rule parameters"
                        >
                          <Sliders className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleToggleRule(r.id, r.is_enabled)}
                          className={`px-3 py-1 rounded text-[11px] font-semibold flex items-center gap-1.5 ${
                            r.is_enabled
                              ? "bg-emerald-950 text-emerald-300 border border-emerald-800/60"
                              : "bg-slate-800 text-slate-400 border border-slate-700"
                          }`}
                        >
                          {r.is_enabled ? "Enabled" : "Disabled"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Modal: Edit Rule Parameters */}
        {editRule && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
            <div className="w-full max-w-md rounded-xl border border-slate-800 bg-[#0B1120] p-6 shadow-2xl">
              <h2 className="text-base font-semibold text-slate-100 mb-1">Tune Detection Rule Parameters</h2>
              <p className="text-xs text-slate-400 mb-4">{editRule.name}</p>
              <form onSubmit={handleSaveRuleParameters} className="space-y-4 text-xs">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Trigger Threshold (Hit Count)</label>
                  <input
                    type="number"
                    min={1}
                    required
                    value={editThreshold}
                    onChange={(e) => setEditThreshold(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Time Window (Seconds)</label>
                  <input
                    type="number"
                    min={10}
                    step={10}
                    required
                    value={editWindow}
                    onChange={(e) => setEditWindow(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Severity</label>
                  <select
                    value={editSeverity}
                    onChange={(e) => setEditSeverity(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="Critical">Critical</option>
                    <option value="High">High</option>
                    <option value="Medium">Medium</option>
                    <option value="Low">Low</option>
                  </select>
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setEditRule(null)}
                    className="px-4 py-2 rounded-lg border border-slate-800 text-slate-400 hover:bg-slate-900"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={savingRule}
                    className="px-4 py-2 rounded-lg bg-cyan-500 text-slate-950 font-semibold hover:bg-cyan-400 disabled:opacity-50"
                  >
                    Save Changes
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
