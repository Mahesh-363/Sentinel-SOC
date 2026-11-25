"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "../../components/layout/AppShell";
import { fetchApi } from "../../lib/api";
import { formatLocalDateTime } from "../../lib/date";
import {
  Globe,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Bot,
  ExternalLink,
  Loader2,
  Clock,
  MapPin,
  FileText,
  Tag,
  CheckCircle2,
  Activity,
  Layers,
  Database,
  Info
} from "lucide-react";

export default function IpIntelPage() {
  const [queryIp, setQueryIp] = useState("185.220.101.5");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Provider health overview
  const [providers, setProviders] = useState<any[]>([]);

  // Case note / verdict form state
  const [verdict, setVerdict] = useState("Inconclusive");
  const [notes, setNotes] = useState("");
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [savingNote, setSavingNote] = useState(false);
  const [noteSavedMsg, setNoteSavedMsg] = useState<string | null>(null);

  // Grounding active tab
  const [activeGroundingTab, setActiveGroundingTab] = useState<"directly_observed" | "imported" | "enriched" | "inferred" | "unavailable">("directly_observed");

  useEffect(() => {
    fetchProviders();
  }, []);

  const fetchProviders = async () => {
    try {
      const data = await fetchApi("/ip-intelligence/providers");
      setProviders(data);
    } catch (err) {
      console.error("Failed to load providers", err);
    }
  };

  const handleInvestigate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!queryIp.trim()) return;
    setLoading(true);
    setError(null);
    setNoteSavedMsg(null);
    try {
      const data = await fetchApi(`/ip-intelligence/investigate?ip=${encodeURIComponent(queryIp.trim())}`);
      setResult(data);
      if (data.saved_investigation) {
        setVerdict(data.saved_investigation.verdict || "Inconclusive");
        setNotes(data.saved_investigation.notes || "");
        setTags(data.saved_investigation.tags || []);
      } else {
        setVerdict(data.reputation === "Malicious" ? "Malicious" : data.reputation === "Suspicious" ? "Suspicious" : "Inconclusive");
        setNotes("");
        setTags([]);
      }
    } catch (err: any) {
      setError(err.message || "Failed to investigate IP address");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveInvestigation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!result) return;
    setSavingNote(true);
    setNoteSavedMsg(null);
    try {
      await fetchApi("/ip-intelligence/investigations", {
        method: "POST",
        body: JSON.stringify({
          ip_address: result.ip_address,
          verdict,
          notes,
          tags
        })
      });
      setNoteSavedMsg("Analyst case notes and verdict successfully committed to dossier.");
      // Refresh investigation
      handleInvestigate();
    } catch (err: any) {
      setError(err.message || "Failed to save investigation notes");
    } finally {
      setSavingNote(false);
    }
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !tags.includes(tagInput.trim())) {
      setTags([...tags, tagInput.trim()]);
      setTagInput("");
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter((t) => t !== tagToRemove));
  };

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
              <Globe className="w-5 h-5 text-cyan-400" />
              Advanced IP Investigation &amp; Threat Feeds
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Dual IPv4/IPv6 classification, multi-feed threat correlation (AbuseIPDB, GreyNoise, OTX, Spamhaus), and strict grounding breakdown.
            </p>
          </div>

          {/* Quick Provider Status Badges */}
          <div className="flex flex-wrap items-center gap-2">
            {providers.map((p, idx) => (
              <div
                key={idx}
                className="px-2.5 py-1 rounded-md bg-[#0F172A] border border-slate-800 text-[11px] flex items-center gap-1.5"
                title={`${p.provider_name}: ${p.status} (Attribution: ${p.attribution})`}
              >
                <div
                  className={`w-1.5 h-1.5 rounded-full ${
                    p.status === "CONFIGURED" || p.status === "ACTIVE"
                      ? "bg-emerald-400"
                      : "bg-slate-500"
                  }`}
                />
                <span className="font-semibold text-slate-300">{p.provider_name}</span>
                <span className="text-[10px] text-slate-500">
                  {p.status === "CONFIGURED" || p.status === "ACTIVE" ? `${p.requests_today}/${p.daily_limit}` : "UNSET"}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Search Bar */}
        <form onSubmit={handleInvestigate} className="flex gap-3 max-w-3xl">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              type="text"
              required
              value={queryIp}
              onChange={(e) => setQueryIp(e.target.value)}
              placeholder="Enter IPv4 or IPv6 address (e.g. 185.220.101.5, 8.8.8.8, 2001:4860::8888)..."
              className="w-full pl-9 pr-3 py-2.5 text-xs rounded-lg bg-[#0F172A] border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs flex items-center gap-2 transition-colors disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            <span>Investigate IP</span>
          </button>
        </form>

        {error && (
          <div className="p-3.5 rounded-lg bg-red-950/40 border border-red-900/50 text-red-300 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Results Area */}
        {result && (
          <div className="space-y-6">
            {/* Primary Identification Header */}
            <div className="p-5 rounded-xl bg-[#0F172A] border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-5">
              <div>
                <div className="flex flex-wrap items-center gap-2.5">
                  <span className="text-2xl font-bold font-mono text-cyan-300">{result.ip_address}</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300 font-mono font-medium">
                    {result.ip_version || `IPv${result.version}`}
                  </span>
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded font-semibold ${
                      result.classification === "Public"
                        ? "bg-cyan-950 text-cyan-400 border border-cyan-800/50"
                        : "bg-slate-800 text-slate-300 border border-slate-700"
                    }`}
                  >
                    {result.classification} Space
                  </span>
                  {result.saved_investigation && (
                    <span className="text-xs px-2.5 py-0.5 rounded font-semibold bg-purple-950 text-purple-300 border border-purple-800/50 flex items-center gap-1">
                      <FileText className="w-3 h-3" /> Dossier: {result.saved_investigation.verdict}
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-slate-400">
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-slate-500" />
                    {result.geolocation?.city ? `${result.geolocation.city}, ` : ""}{result.geolocation?.country || "Country Unknown"}
                  </span>
                  <span>&bull;</span>
                  <span>{result.geolocation?.asn || "ASN N/A"}</span>
                  {result.geolocation?.as_org && <span>({result.geolocation.as_org})</span>}
                </div>
              </div>

              {/* Threat Score & Verdict Callout */}
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <div className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">Overall Reputation</div>
                  <div
                    className={`text-xl font-bold font-mono ${
                      result.reputation === "Malicious"
                        ? "text-red-400"
                        : result.reputation === "Suspicious"
                        ? "text-amber-400"
                        : "text-emerald-400"
                    }`}
                  >
                    {result.reputation}
                  </div>
                  <div className="text-[11px] text-slate-400">
                    Confidence: {result.confidence}%
                  </div>
                </div>

                <a
                  href={`/ai-analyst?type=ip&target=${result.ip_address}`}
                  className="px-4 py-2.5 rounded-lg bg-cyan-950 border border-cyan-800/60 hover:bg-cyan-900/60 text-cyan-300 font-semibold text-xs flex items-center gap-2 transition-colors"
                >
                  <Bot className="w-4 h-4 text-cyan-400" />
                  <span>Analyze with Advisory AI</span>
                </a>
              </div>
            </div>

            {/* 4 Threat Intelligence Providers Cards */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                  <Shield className="w-4 h-4 text-cyan-400" />
                  Threat Intelligence Adapters (TTL Cached)
                </h2>
                <span className="text-[11px] text-slate-400">Normalized standard indicators</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {["AbuseIPDB", "GreyNoise", "AlienVault OTX", "Spamhaus"].map((providerName) => {
                  const pData = result.threat_providers?.[providerName] || result.threat_providers?.[providerName.toLowerCase()] || null;
                  return (
                    <div
                      key={providerName}
                      className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 text-xs flex flex-col justify-between space-y-3"
                    >
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-slate-200">{providerName}</span>
                          <span
                            className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${
                              pData?.status === "SUCCESS"
                                ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                                : pData?.status === "NOT CONFIGURED"
                                ? "bg-slate-900 text-slate-400 border border-slate-800"
                                : pData?.status === "RATE_LIMITED"
                                ? "bg-amber-950 text-amber-300 border border-amber-800"
                                : "bg-slate-900 text-slate-500 border border-slate-800"
                            }`}
                          >
                            {pData?.status || "INACTIVE"}
                          </span>
                        </div>

                        <div className="mt-2.5">
                          <div className="text-[11px] text-slate-400">Classification:</div>
                          <div
                            className={`font-semibold text-sm ${
                              pData?.reputation === "Malicious"
                                ? "text-red-400"
                                : pData?.reputation === "Suspicious"
                                ? "text-amber-400"
                                : pData?.reputation === "Benign"
                                ? "text-emerald-400"
                                : "text-slate-400"
                            }`}
                          >
                            {pData?.reputation || "Not Evaluated"}
                          </div>
                          {pData?.confidence !== undefined && pData.confidence > 0 && (
                            <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                              Confidence: {pData.confidence}%
                            </div>
                          )}
                        </div>

                        {pData?.raw_details?.message && (
                          <p className="mt-2 text-[11px] text-slate-400 leading-relaxed">
                            {pData.raw_details.message}
                          </p>
                        )}
                        {pData?.raw_details?.total_reports !== undefined && (
                          <div className="mt-1 text-[11px] text-slate-300 font-mono">
                            Reports Count: {pData.raw_details.total_reports}
                          </div>
                        )}
                      </div>

                      <div className="pt-2 border-t border-slate-800/80 text-[10px] text-slate-400 flex items-center justify-between">
                        <span className="truncate" title={pData?.attribution || "Official Adapter"}>
                          {pData?.attribution?.substring(0, 32) || providerName}...
                        </span>
                        {pData?.reference && (
                          <a
                            href={pData.reference}
                            target="_blank"
                            rel="noreferrer"
                            className="text-cyan-400 hover:text-cyan-300 flex items-center gap-0.5"
                          >
                            <span>Ref</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Strict Grounding Breakdown Tabs (Truth in Telemetry) */}
            <div className="p-5 rounded-xl bg-[#0F172A] border border-slate-800 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-800 pb-3 gap-3">
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-cyan-400" />
                  <div>
                    <h2 className="text-sm font-semibold text-slate-200">Evidence Grounding Breakdown</h2>
                    <p className="text-[11px] text-slate-400">Strict separation of observed facts, imported intelligence, and inferred context.</p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-1">
                  {[
                    { id: "directly_observed", label: "Directly Observed" },
                    { id: "imported", label: "Imported Intel" },
                    { id: "enriched", label: "Third-Party Geo" },
                    { id: "inferred", label: "Inferred Context" },
                    { id: "unavailable", label: "Unavailable" }
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveGroundingTab(tab.id as any)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                        activeGroundingTab === tab.id
                          ? "bg-cyan-500/10 text-cyan-300 border border-cyan-800/60"
                          : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tab Contents */}
              {activeGroundingTab === "directly_observed" && (
                <div className="space-y-3 text-xs">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                      <span className="text-slate-400">Observed in Organization:</span>
                      <div className="font-semibold text-slate-200 mt-0.5">
                        {result.grounding_breakdown?.["Directly Observed"]?.is_observed_in_tenant ? "YES (Active Telemetry)" : "NO (External Probing Only)"}
                      </div>
                    </div>
                    <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                      <span className="text-slate-400">Total Local Socket Observations:</span>
                      <div className="font-semibold text-slate-200 mt-0.5 font-mono">
                        {result.connection_history?.total_count || 0}
                      </div>
                    </div>
                    <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                      <span className="text-slate-400">Related Security Events:</span>
                      <div className="font-semibold text-slate-200 mt-0.5 font-mono">
                        {result.related_events?.total_count || 0}
                      </div>
                    </div>
                  </div>

                  {result.associations?.assets?.length > 0 && (
                    <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                      <span className="text-slate-400 font-medium">Enrolled Internal Hosts Assigned This IP:</span>
                      <div className="flex flex-wrap gap-2 mt-1.5">
                        {result.associations.assets.map((a: any, i: number) => (
                          <span key={i} className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 font-mono text-[11px] border border-cyan-800">
                            {a.hostname} ({a.type})
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeGroundingTab === "imported" && (
                <div className="space-y-3 text-xs">
                  <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="text-slate-400 font-medium">Aggregated Provider Feeds:</span>
                    <p className="text-slate-300 text-[11px] mt-1">
                      Data imported from external threat databases under standard attribution. IP reputational scores reflect historical reports and are not definitive proof of current threat status.
                    </p>
                  </div>
                  <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-slate-300 font-mono overflow-x-auto">
                    {JSON.stringify(result.threat_providers, null, 2)}
                  </pre>
                </div>
              )}

              {activeGroundingTab === "enriched" && (
                <div className="space-y-3 text-xs">
                  <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1.5">
                    <div><span className="text-slate-400">Autonomous System:</span> <span className="font-mono text-slate-200">{result.geolocation?.asn || "N/A"} - {result.geolocation?.as_org || "Unknown"}</span></div>
                    <div><span className="text-slate-400">Country:</span> <span className="text-slate-200">{result.geolocation?.country || "Unknown"} ({result.geolocation?.country_code || "N/A"})</span></div>
                    <div><span className="text-slate-400">City / Region:</span> <span className="text-slate-200">{result.geolocation?.city || "Unknown City"}</span></div>
                    <p className="text-[10px] text-slate-400 pt-1 border-t border-slate-800 mt-2">
                      * Geolocation data is approximate down to metropolitan/ASN boundary and does not indicate physical device location.
                    </p>
                  </div>
                </div>
              )}

              {activeGroundingTab === "inferred" && (
                <div className="space-y-3 text-xs">
                  <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="text-slate-400 font-medium">Heuristic &amp; Inferred Context:</span>
                    <ul className="list-disc list-inside mt-2 space-y-1 text-slate-300 text-[11px]">
                      <li>Address scope classification based on IANA/RFC registries.</li>
                      <li>Estimated operational risk determined by presence of public listening ports and prior incident links.</li>
                      <li>Attribution to threat actor groups remains unverified without cryptographic host artifacts.</li>
                    </ul>
                  </div>
                </div>
              )}

              {activeGroundingTab === "unavailable" && (
                <div className="space-y-3 text-xs">
                  <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="text-slate-400 font-medium">Explicitly Unavailable Telemetry:</span>
                    <ul className="list-disc list-inside mt-2 space-y-1 text-slate-400 text-[11px]">
                      <li>Real-time raw packet payload inspection (Sentinel respects privacy &amp; metadata boundaries).</li>
                      <li>Encrypted TLS session contents without host-based sensor decryption.</li>
                      <li>Global routing path changes beyond direct BGP ASN announcement.</li>
                    </ul>
                  </div>
                </div>
              )}
            </div>

            {/* Investigation Notes & Verdict Editor (Dossier) */}
            <div className="p-5 rounded-xl bg-[#0F172A] border border-slate-800 text-xs">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-cyan-400" />
                  <h2 className="text-sm font-semibold text-slate-200">Analyst Investigation Dossier &amp; Verdict</h2>
                </div>
                {noteSavedMsg && (
                  <span className="text-emerald-400 flex items-center gap-1 text-[11px]">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    {noteSavedMsg}
                  </span>
                )}
              </div>

              <form onSubmit={handleSaveInvestigation} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                      Analyst Verdict
                    </label>
                    <select
                      value={verdict}
                      onChange={(e) => setVerdict(e.target.value)}
                      className="w-full px-3 py-2 text-xs rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                    >
                      <option value="Benign">Benign (Authorized / Known Good)</option>
                      <option value="Suspicious">Suspicious (Requires Monitoring / Caution)</option>
                      <option value="Malicious">Malicious (Confirmed Threat Indicator)</option>
                      <option value="Inconclusive">Inconclusive (Insufficient Telemetry)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                      Case Tags (Press Enter or Add)
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={tagInput}
                        onChange={(e) => setTagInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            handleAddTag();
                          }
                        }}
                        placeholder="e.g. reconnaissance, c2-beacon, staging..."
                        className="flex-1 px-3 py-2 text-xs rounded-lg bg-slate-900 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                      />
                      <button
                        type="button"
                        onClick={handleAddTag}
                        className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs"
                      >
                        Add Tag
                      </button>
                    </div>
                  </div>
                </div>

                {tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {tags.map((t, idx) => (
                      <span
                        key={idx}
                        className="px-2.5 py-0.5 rounded-md bg-cyan-950 text-cyan-300 border border-cyan-800 text-[11px] flex items-center gap-1.5"
                      >
                        <Tag className="w-3 h-3 text-cyan-400" />
                        <span>{t}</span>
                        <button
                          type="button"
                          onClick={() => handleRemoveTag(t)}
                          className="text-cyan-400 hover:text-cyan-200 ml-1 font-bold"
                        >
                          &times;
                        </button>
                      </span>
                    ))}
                  </div>
                )}

                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                    Investigation Findings &amp; Rationale
                  </label>
                  <textarea
                    rows={3}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Document contextual findings, observed behavioral anomalies, or firewall policy actions..."
                    className="w-full px-3 py-2 text-xs rounded-lg bg-slate-900 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={savingNote}
                    className="px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs flex items-center gap-2 disabled:opacity-50"
                  >
                    {savingNote ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                    <span>Save Investigation Notes</span>
                  </button>
                </div>
              </form>
            </div>

            {/* Chronological Investigation Timeline */}
            <div className="p-5 rounded-xl bg-[#0F172A] border border-slate-800 text-xs">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-cyan-400" />
                  <h2 className="text-sm font-semibold text-slate-200">Chronological Investigation Timeline</h2>
                </div>
                <span className="text-slate-400 font-mono text-[11px]">
                  {result.investigation_timeline?.length || 0} Events
                </span>
              </div>

              {result.investigation_timeline?.length > 0 ? (
                <div className="space-y-3 relative pl-6 border-l border-slate-800/80 ml-2">
                  {result.investigation_timeline.map((item: any, idx: number) => (
                    <div key={idx} className="relative group">
                      <div className="absolute -left-[31px] top-1 w-2.5 h-2.5 rounded-full bg-cyan-400 ring-4 ring-[#0F172A]" />
                      <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors">
                        <div className="flex items-center justify-between text-[11px] mb-1">
                          <span className="font-semibold text-slate-200">{item.event}</span>
                          <span className="text-slate-400 font-mono">{formatLocalDateTime(item.timestamp)}</span>
                        </div>
                        <p className="text-slate-400 text-[11px] leading-relaxed">{item.details}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="py-6 text-center text-slate-400">
                  No chronological events recorded for this IP address yet.
                </p>
              )}
            </div>

            {/* Local Organization Observations Table */}
            <div className="p-5 rounded-xl bg-[#0F172A] border border-slate-800 text-xs">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  <h2 className="text-sm font-semibold text-slate-200">
                    Local Telemetry Observations in Your Organization
                  </h2>
                </div>
                <span className="text-slate-400 font-mono">
                  {result.connection_history?.total_count || 0} Total Observations
                </span>
              </div>

              {result.connection_history?.recent?.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400">
                        <th className="pb-2">Direction</th>
                        <th className="pb-2">Port</th>
                        <th className="pb-2">Protocol</th>
                        <th className="pb-2">Observation Point</th>
                        <th className="pb-2 text-right">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {result.connection_history.recent.map((obs: any, i: number) => (
                        <tr key={i} className="hover:bg-slate-900/40">
                          <td className="py-2.5 font-medium text-slate-300">{obs.direction}</td>
                          <td className="py-2.5 font-mono text-cyan-300">{obs.port || "N/A"}</td>
                          <td className="py-2.5 text-slate-400">{obs.protocol}</td>
                          <td className="py-2.5 text-slate-400">{obs.source}</td>
                          <td className="py-2.5 text-slate-400 text-right font-mono">
                            {formatLocalDateTime(obs.timestamp)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="py-6 text-center text-slate-400">
                  This IP address has not been observed connecting to or from your registered endpoints.
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
