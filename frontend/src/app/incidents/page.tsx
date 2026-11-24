"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "../../components/layout/AppShell";
import { fetchApi } from "../../lib/api";
import {
  AlertOctagon,
  Plus,
  RefreshCw,
  Bot,
  MessageSquare,
  Clock,
  CheckCircle,
  Shield,
  Send,
  Download,
  FileText,
  User,
  Activity,
  Layers,
  Zap,
  AlertTriangle,
  Check,
  X
} from "lucide-react";

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIncident, setSelectedIncident] = useState<any | null>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [activeDetailTab, setActiveDetailTab] = useState<"overview" | "timeline" | "comments">("overview");

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newSeverity, setNewSeverity] = useState("High");
  const [commentText, setCommentText] = useState("");

  // Response Playbooks state
  const [playbookModalOpen, setPlaybookModalOpen] = useState(false);
  const [playbooks, setPlaybooks] = useState<any[]>([]);
  const [executions, setExecutions] = useState<any[]>([]);
  const [selectedPlaybookId, setSelectedPlaybookId] = useState("");
  const [playbookReason, setPlaybookReason] = useState("");
  const [playbookLoading, setPlaybookLoading] = useState(false);

  const loadPlaybooksAndExecutions = async () => {
    try {
      const [pbs, execs] = await Promise.all([
        fetchApi("/response/playbooks"),
        fetchApi("/response/executions")
      ]);
      setPlaybooks(pbs || []);
      if (pbs && pbs.length > 0 && !selectedPlaybookId) {
        setSelectedPlaybookId(pbs[0].id);
      }
      setExecutions(execs || []);
    } catch (e) {
      console.error(e);
    }
  };

  const handleTriggerPlaybook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPlaybookId) return;
    setPlaybookLoading(true);
    try {
      let targetAssetId = null;
      let targetIp = null;
      if (selectedIncident) {
        try {
          const assetIds = JSON.parse(selectedIncident.related_asset_ids_json || "[]");
          if (assetIds.length > 0) targetAssetId = assetIds[0];
          const ips = JSON.parse(selectedIncident.related_ip_addresses_json || "[]");
          if (ips.length > 0) targetIp = ips[0];
        } catch {}
      }
      await fetchApi("/response/trigger", {
        method: "POST",
        body: JSON.stringify({
          playbook_id: selectedPlaybookId,
          target_asset_id: targetAssetId,
          target_ip: targetIp,
          incident_id: selectedIncident?.id,
          reason: playbookReason || "Analyst initiated from Incident Management"
        })
      });
      setPlaybookReason("");
      await loadPlaybooksAndExecutions();
      if (selectedIncident) loadTimeline(selectedIncident.id);
      alert("Response playbook triggered successfully.");
    } catch (err: any) {
      alert(`Trigger failed: ${err.message}`);
    } finally {
      setPlaybookLoading(false);
    }
  };

  const handleDecision = async (executionId: string, decision: "Approved" | "Rejected") => {
    try {
      await fetchApi(`/response/executions/${executionId}/decision`, {
        method: "POST",
        body: JSON.stringify({ decision, notes: `Decision: ${decision}` })
      });
      await loadPlaybooksAndExecutions();
      if (selectedIncident) loadTimeline(selectedIncident.id);
    } catch (err: any) {
      alert(`Decision failed: ${err.message}`);
    }
  };

  useEffect(() => {
    if (playbookModalOpen) {
      loadPlaybooksAndExecutions();
    }
  }, [playbookModalOpen]);

  const loadIncidents = async () => {
    try {
      const data = await fetchApi("/incidents");
      setIncidents(data || []);
      if (data && data.length > 0) {
        if (!selectedIncident) {
          setSelectedIncident(data[0]);
          loadTimeline(data[0].id);
        } else {
          const fresh = data.find((i: any) => i.id === selectedIncident.id) || data[0];
          setSelectedIncident(fresh);
          loadTimeline(fresh.id);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadTimeline = async (incidentId: string) => {
    setTimelineLoading(true);
    try {
      const tl = await fetchApi(`/incidents/${incidentId}/timeline`);
      setTimeline(tl || []);
    } catch (e) {
      console.error("Failed to load timeline", e);
    } finally {
      setTimelineLoading(false);
    }
  };

  useEffect(() => {
    loadIncidents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSelectIncident = (inc: any) => {
    setSelectedIncident(inc);
    loadTimeline(inc.id);
  };

  const handleCreateIncident = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await fetchApi("/incidents", {
        method: "POST",
        body: JSON.stringify({
          title: newTitle,
          description: newDesc,
          severity: newSeverity,
        }),
      });
      setCreateModalOpen(false);
      setNewTitle("");
      setNewDesc("");
      loadIncidents();
      setSelectedIncident(created);
      loadTimeline(created.id);
    } catch (err: any) {
      alert(`Failed to create incident: ${err.message}`);
    }
  };

  const handleUpdateStatus = async (newStatus: string) => {
    if (!selectedIncident) return;
    try {
      const updated = await fetchApi(`/incidents/${selectedIncident.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus }),
      });
      setSelectedIncident(updated);
      loadTimeline(selectedIncident.id);
      loadIncidents();
    } catch (err: any) {
      alert(`Status update failed: ${err.message}`);
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedIncident || !commentText.trim()) return;
    try {
      await fetchApi(`/incidents/${selectedIncident.id}/comments`, {
        method: "POST",
        body: JSON.stringify({ comment: commentText.trim() }),
      });
      setCommentText("");
      const fresh = await fetchApi(`/incidents/${selectedIncident.id}`);
      setSelectedIncident(fresh);
      loadTimeline(selectedIncident.id);
      loadIncidents();
    } catch (err: any) {
      alert(`Failed to post comment: ${err.message}`);
    }
  };

  const handleExportTimelineCsv = () => {
    if (!selectedIncident) return;
    const token = localStorage.getItem("sentinel_token");
    const orgId = localStorage.getItem("sentinel_active_org") || localStorage.getItem("sentinel_org_id");
    const url = `${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1"}/incidents/${selectedIncident.id}/export/csv`;
    
    // Download using bearer auth fetch
    fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Organization-Id": orgId || ""
      }
    })
      .then((res) => res.blob())
      .then((blob) => {
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = `incident_${selectedIncident.id.slice(0, 8)}_timeline.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      })
      .catch((err) => alert(`Export failed: ${err}`));
  };

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
              <AlertOctagon className="w-5 h-5 text-amber-400" />
              Incident Management &amp; Case Response
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Structured lifecycle triage: New &rarr; Acknowledged &rarr; Investigating &rarr; Contained &rarr; Resolved &rarr; Closed
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadIncidents}
              className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-cyan-400"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={() => setCreateModalOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-semibold"
            >
              <Plus className="w-4 h-4" />
              <span>Create Incident</span>
            </button>
          </div>
        </div>

        {/* Master-Detail Incident Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Incident List Column */}
          <div className="space-y-3">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
              <span>Incident Cases</span>
              <span className="font-mono">{incidents.length} Total</span>
            </div>

            <div className="space-y-2 max-h-[700px] overflow-y-auto pr-1">
              {incidents.length > 0 ? (
                incidents.map((inc) => (
                  <div
                    key={inc.id}
                    onClick={() => handleSelectIncident(inc)}
                    className={`p-3.5 rounded-xl border text-xs cursor-pointer transition-all ${
                      selectedIncident?.id === inc.id
                        ? "bg-slate-900 border-cyan-500/50 shadow-md shadow-cyan-950/20"
                        : "bg-[#0F172A] border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono text-[10px] text-slate-400">INC-{inc.id.slice(0, 8)}</span>
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                          inc.severity === "Critical"
                            ? "bg-red-950 text-red-400"
                            : inc.severity === "High"
                            ? "bg-orange-950 text-orange-400"
                            : "bg-amber-950 text-amber-400"
                        }`}
                      >
                        {inc.severity}
                      </span>
                    </div>
                    <h3 className="font-semibold text-slate-200 line-clamp-1">{inc.title}</h3>
                    <p className="text-slate-400 text-[11px] line-clamp-2 mt-1 leading-relaxed">{inc.description}</p>
                    <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-500">
                      <span className="px-2 py-0.5 rounded bg-slate-950 text-cyan-400 font-mono font-medium">
                        {inc.status}
                      </span>
                      <span>{new Date(inc.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-12 text-center text-slate-500 text-xs">No active incidents found.</div>
              )}
            </div>
          </div>

          {/* Incident Detail Column */}
          <div className="lg:col-span-2">
            {selectedIncident ? (
              <div className="p-6 rounded-xl bg-[#0F172A] border border-slate-800 shadow-sm space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-xs text-cyan-400 font-semibold">INC-{selectedIncident.id}</span>
                      <span className="text-xs text-slate-500">&bull;</span>
                      <span className="text-xs text-slate-400">{new Date(selectedIncident.created_at).toLocaleString()}</span>
                    </div>
                    <h2 className="text-lg font-bold text-slate-100">{selectedIncident.title}</h2>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleExportTimelineCsv}
                      className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                      title="Export Incident Timeline CSV"
                    >
                      <Download className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Export Timeline CSV</span>
                    </button>
                    <button
                      onClick={() => setPlaybookModalOpen(true)}
                      className="px-3 py-1.5 rounded-lg bg-red-950/80 border border-red-800/80 hover:bg-red-900/80 text-red-300 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                      title="Automated Response Playbooks"
                    >
                      <Zap className="w-3.5 h-3.5 text-red-400" />
                      <span>Run Playbook</span>
                    </button>
                    <a
                      href={`/ai-analyst?type=incident&target=${selectedIncident.id}`}
                      className="px-3 py-1.5 rounded-lg bg-cyan-950 border border-cyan-800 text-cyan-300 hover:bg-cyan-900 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                    >
                      <Bot className="w-4 h-4 text-cyan-400" />
                      <span>AI Advisory Briefing</span>
                    </a>
                  </div>
                </div>

                {/* Status Progression Controls */}
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Incident Lifecycle State
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {["New", "Acknowledged", "Investigating", "Contained", "Resolved", "Closed"].map((st) => (
                      <button
                        key={st}
                        onClick={() => handleUpdateStatus(st)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                          selectedIncident.status === st
                            ? "bg-cyan-500 text-slate-950 font-bold shadow-md shadow-cyan-950"
                            : "bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        {st}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Detail View Tabs: Overview vs Timeline vs Notes */}
                <div className="flex border-b border-slate-800 text-xs font-semibold gap-6 pt-2">
                  <button
                    onClick={() => setActiveDetailTab("overview")}
                    className={`pb-2.5 border-b-2 transition-colors flex items-center gap-1.5 ${
                      activeDetailTab === "overview"
                        ? "border-cyan-400 text-cyan-300"
                        : "border-transparent text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>Case Overview</span>
                  </button>
                  <button
                    onClick={() => setActiveDetailTab("timeline")}
                    className={`pb-2.5 border-b-2 transition-colors flex items-center gap-1.5 ${
                      activeDetailTab === "timeline"
                        ? "border-cyan-400 text-cyan-300"
                        : "border-transparent text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <Clock className="w-3.5 h-3.5" />
                    <span>Chronological Timeline ({timeline.length})</span>
                  </button>
                  <button
                    onClick={() => setActiveDetailTab("comments")}
                    className={`pb-2.5 border-b-2 transition-colors flex items-center gap-1.5 ${
                      activeDetailTab === "comments"
                        ? "border-cyan-400 text-cyan-300"
                        : "border-transparent text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    <span>Analyst Notes ({selectedIncident.comments?.length || 0})</span>
                  </button>
                </div>

                {/* TAB 1: Case Overview */}
                {activeDetailTab === "overview" && (
                  <div className="space-y-4 text-xs">
                    <div>
                      <span className="font-semibold text-slate-400 uppercase tracking-wider text-[11px]">Executive Overview</span>
                      <p className="text-slate-300 leading-relaxed bg-slate-950/60 p-4 rounded-lg border border-slate-800 mt-1.5">
                        {selectedIncident.description}
                      </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                        <span className="text-slate-400 font-medium">Related IP Addresses:</span>
                        <div className="flex flex-wrap gap-1.5 mt-1">
                          {(() => {
                            try {
                              const ips = JSON.parse(selectedIncident.related_ip_addresses_json || "[]");
                              return ips.length > 0 ? (
                                ips.map((ip: string, i: number) => (
                                  <a
                                    key={i}
                                    href={`/ip-intel?target=${ip}`}
                                    className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 font-mono text-[11px] border border-cyan-800 hover:underline"
                                  >
                                    {ip}
                                  </a>
                                ))
                              ) : (
                                <span className="text-slate-500">None attached</span>
                              );
                            } catch {
                              return <span className="text-slate-500">None attached</span>;
                            }
                          })()}
                        </div>
                      </div>

                      <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                        <span className="text-slate-400 font-medium">Impacted Internal Assets:</span>
                        <div className="flex flex-wrap gap-1.5 mt-1">
                          {(() => {
                            try {
                              const assets = JSON.parse(selectedIncident.related_asset_ids_json || "[]");
                              return assets.length > 0 ? (
                                assets.map((aid: string, i: number) => (
                                  <span key={i} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[11px]">
                                    {aid.slice(0, 8)}
                                  </span>
                                ))
                              ) : (
                                <span className="text-slate-500">None attached</span>
                              );
                            } catch {
                              return <span className="text-slate-500">None attached</span>;
                            }
                          })()}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* TAB 2: Unified Chronological Timeline */}
                {activeDetailTab === "timeline" && (
                  <div className="space-y-4 text-xs">
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span>Unified record of all alert attachments, status mutations, analyst notes, and AI briefings</span>
                      <button
                        onClick={handleExportTimelineCsv}
                        className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-semibold"
                      >
                        <Download className="w-3 h-3" />
                        <span>Download CSV</span>
                      </button>
                    </div>

                    {timelineLoading ? (
                      <div className="py-8 text-center text-slate-500">Loading timeline records...</div>
                    ) : timeline.length > 0 ? (
                      <div className="space-y-3 relative pl-6 border-l border-slate-800 ml-2">
                        {timeline.map((entry: any, idx: number) => (
                          <div key={idx} className="relative group">
                            <div className="absolute -left-[31px] top-1 w-2.5 h-2.5 rounded-full bg-cyan-400 ring-4 ring-[#0F172A]" />
                            <div className="p-3.5 rounded-lg bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition-colors">
                              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[11px] mb-1">
                                <div className="flex items-center gap-2">
                                  <span className="font-bold text-slate-200">{entry.title}</span>
                                  <span className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 text-[9px] font-mono">
                                    {entry.entry_type}
                                  </span>
                                </div>
                                <span className="text-slate-500 font-mono">{new Date(entry.timestamp).toLocaleString()}</span>
                              </div>
                              <p className="text-slate-300 text-[11px] leading-relaxed">{entry.description}</p>
                              <div className="mt-1.5 text-[10px] text-slate-500 flex items-center gap-1">
                                <User className="w-3 h-3" />
                                <span>{entry.actor_name || entry.actor_type}</span>
                                {entry.is_ai_generated && (
                                  <span className="px-1 rounded bg-purple-950 text-purple-300 border border-purple-800 font-bold">
                                    AI
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="py-6 text-center text-slate-500 italic">No timeline entries recorded yet.</p>
                    )}
                  </div>
                )}

                {/* TAB 3: Comments & Analyst Notes */}
                {activeDetailTab === "comments" && (
                  <div className="space-y-4 text-xs">
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {selectedIncident.comments?.length > 0 ? (
                        selectedIncident.comments.map((cm: any) => (
                          <div key={cm.id} className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-xs">
                            <div className="flex items-center justify-between text-slate-400 mb-1">
                              <span className="font-semibold text-slate-200">{cm.user_name || "Analyst"}</span>
                              <span className="text-[10px] font-mono">{new Date(cm.created_at).toLocaleTimeString()}</span>
                            </div>
                            <p className="text-slate-300">{cm.comment}</p>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-slate-500 italic">No notes added to this incident case yet.</p>
                      )}
                    </div>

                    {/* Add Note Form */}
                    <form onSubmit={handleAddComment} className="flex gap-2">
                      <input
                        type="text"
                        value={commentText}
                        onChange={(e) => setCommentText(e.target.value)}
                        placeholder="Add investigation findings or containment note..."
                        className="flex-1 px-3 py-2 text-xs rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                      />
                      <button
                        type="submit"
                        disabled={!commentText.trim()}
                        className="px-4 py-2 rounded-lg bg-cyan-500 text-slate-950 font-semibold text-xs hover:bg-cyan-400 disabled:opacity-50 flex items-center gap-1.5"
                      >
                        <Send className="w-3.5 h-3.5" />
                        <span>Post</span>
                      </button>
                    </form>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-12 text-center text-slate-500 text-xs rounded-xl bg-[#0F172A] border border-slate-800">
                Select an incident from the ledger to inspect evidence and update case status.
              </div>
            )}
          </div>
        </div>

        {/* Modal: Create Incident */}
        {createModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
            <div className="w-full max-w-lg rounded-xl border border-slate-800 bg-[#0B1120] p-6 shadow-2xl">
              <h2 className="text-base font-semibold text-slate-100 mb-1">Open Security Incident Case</h2>
              <p className="text-xs text-slate-400 mb-4">Initialize tracking for a confirmed threat or anomaly</p>
              <form onSubmit={handleCreateIncident} className="space-y-4 text-xs">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Incident Title</label>
                  <input
                    type="text"
                    required
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    placeholder="e.g. Inbound Credential Stuffing Burst on Production Database"
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Severity Rating</label>
                  <select
                    value={newSeverity}
                    onChange={(e) => setNewSeverity(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="Critical">Critical (Immediate Outage / Breach)</option>
                    <option value="High">High (Active Targeted Attack)</option>
                    <option value="Medium">Medium (Suspicious Anomaly)</option>
                    <option value="Low">Low (Policy / Informational)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Incident Description &amp; Initial Evidence</label>
                  <textarea
                    rows={4}
                    required
                    value={newDesc}
                    onChange={(e) => setNewDesc(e.target.value)}
                    placeholder="Document affected hosts, source IP addresses, detection indicators, and triage steps..."
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setCreateModalOpen(false)}
                    className="px-4 py-2 rounded-lg border border-slate-800 text-slate-400 hover:bg-slate-900"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-lg bg-cyan-500 text-slate-950 font-semibold hover:bg-cyan-400"
                  >
                    Open Incident Case
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal: Response Playbooks & Execution Approval */}
        {playbookModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
            <div className="w-full max-w-2xl rounded-xl border border-slate-800 bg-[#0B1120] p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Zap className="w-5 h-5 text-red-400" />
                  <div>
                    <h2 className="text-base font-bold text-slate-100">Automated Response Playbooks</h2>
                    <p className="text-xs text-slate-400">Approval-gated containment and remediation workflows</p>
                  </div>
                </div>
                <button
                  onClick={() => setPlaybookModalOpen(false)}
                  className="p-1 rounded-lg hover:bg-slate-900 text-slate-400 hover:text-slate-200"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Safety Notice */}
              <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/50 flex items-start gap-2.5 text-xs text-amber-300">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <span>
                  <strong>Approval-Based Guardrail:</strong> Destructive containment actions (such as host network isolation and credential revocation) require explicit analyst authorization before execution. No AI or automated rule can isolate infrastructure autonomously.
                </span>
              </div>

              {/* Trigger Playbook Form */}
              <form onSubmit={handleTriggerPlaybook} className="space-y-4 text-xs">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Select Playbook to Trigger</label>
                  <select
                    value={selectedPlaybookId}
                    onChange={(e) => setSelectedPlaybookId(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    {playbooks.map((pb) => (
                      <option key={pb.id} value={pb.id}>
                        {pb.name} ({pb.requires_approval ? "Requires Approval" : "Instant Execution"})
                      </option>
                    ))}
                  </select>
                  {selectedPlaybookId && (
                    <p className="mt-1 text-[11px] text-slate-400">
                      {playbooks.find((p) => p.id === selectedPlaybookId)?.description}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Target Context</label>
                  <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 font-mono text-[11px] space-y-1">
                    <div>Incident: {selectedIncident?.title || "N/A"}</div>
                    <div>Asset ID: {selectedIncident?.related_asset_ids_json || "None"}</div>
                    <div>Target IP: {selectedIncident?.related_ip_addresses_json || "None"}</div>
                  </div>
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Invocation Rationale / Justification</label>
                  <input
                    type="text"
                    required
                    value={playbookReason}
                    onChange={(e) => setPlaybookReason(e.target.value)}
                    placeholder="e.g. Active C2 beacon observed on endpoint; isolating to prevent lateral movement"
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <button
                    type="submit"
                    disabled={playbookLoading}
                    className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
                  >
                    <Zap className="w-3.5 h-3.5" />
                    <span>{playbookLoading ? "Dispatching..." : "Trigger Playbook"}</span>
                  </button>
                </div>
              </form>

              {/* Execution Ledger & Approval Controls */}
              <div className="pt-4 border-t border-slate-800">
                <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                  Response Execution Ledger &amp; Authorization History
                </h3>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {executions.length > 0 ? (
                    executions.map((exec) => (
                      <div
                        key={exec.id}
                        className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 text-xs space-y-2"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-200 line-clamp-1">{exec.action_preview}</span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              exec.status === "Pending Approval"
                                ? "bg-amber-950 text-amber-400 border border-amber-800"
                                : exec.status === "Completed"
                                ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                                : "bg-red-950 text-red-400 border border-red-800"
                            }`}
                          >
                            {exec.status}
                          </span>
                        </div>
                        {exec.execution_log && (
                          <div className="text-[11px] text-slate-400 font-mono bg-slate-900/60 p-2 rounded border border-slate-800">
                            {exec.execution_log}
                          </div>
                        )}
                        {exec.status === "Pending Approval" && (
                          <div className="flex items-center justify-end gap-2 pt-1">
                            <button
                              onClick={() => handleDecision(exec.id, "Rejected")}
                              className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 hover:bg-slate-800 text-red-400 text-[11px] font-semibold flex items-center gap-1"
                            >
                              <X className="w-3 h-3" />
                              <span>Reject</span>
                            </button>
                            <button
                              onClick={() => handleDecision(exec.id, "Approved")}
                              className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-slate-950 text-[11px] font-bold flex items-center gap-1"
                            >
                              <Check className="w-3 h-3" />
                              <span>Authorize Execution</span>
                            </button>
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="py-6 text-center text-slate-500 text-xs">No response actions recorded yet.</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
