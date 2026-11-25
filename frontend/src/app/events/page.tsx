"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "../../components/layout/AppShell";
import { fetchApi } from "../../lib/api";
import { formatLocalDateTime } from "../../lib/date";
import {
  Activity,
  Search,
  Filter,
  RefreshCw,
  Bot,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  Code,
} from "lucide-react";

export default function EventsPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [search, setSearch] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const loadEvents = async () => {
    try {
      let url = "/events?hours=72&limit=200";
      if (severityFilter) url += `&severity=${severityFilter}`;
      if (typeFilter) url += `&event_type=${typeFilter}`;
      const data = await fetchApi(url);
      setEvents(data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [severityFilter, typeFilter]);

  const filteredEvents = events.filter((e) => {
    const q = search.toLowerCase();
    return (
      e.title.toLowerCase().includes(q) ||
      (e.source_ip && e.source_ip.toLowerCase().includes(q)) ||
      (e.destination_ip && e.destination_ip.toLowerCase().includes(q)) ||
      e.event_type.toLowerCase().includes(q)
    );
  });

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
              <Activity className="w-5 h-5 text-cyan-400" />
              Security Event Telemetry Ledger
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Auditable event log with tenant isolation, source attribution, and raw payload verification
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadEvents}
              className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-cyan-400"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by title, IP, or type..."
              className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-[#0F172A] border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-3 py-2 text-xs rounded-lg bg-[#0F172A] border border-slate-800 text-slate-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="">All Severities</option>
            <option value="Critical">Critical</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
            <option value="Informational">Informational</option>
          </select>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-2 text-xs rounded-lg bg-[#0F172A] border border-slate-800 text-slate-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="">All Event Types</option>
            <option value="auth_failure">Authentication Failure</option>
            <option value="port_scan">Port Scan</option>
            <option value="outbound_conn">Outbound Connection</option>
            <option value="lan_device">LAN Device</option>
            <option value="aws_event">AWS Security</option>
          </select>

          <span className="text-xs text-slate-400 font-mono ml-auto">
            {filteredEvents.length} Events Listed
          </span>
        </div>

        {/* Events Table */}
        <div className="rounded-xl bg-[#0F172A] border border-slate-800 overflow-hidden shadow-sm">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                <th className="py-3 px-4 w-8"></th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Event Title &amp; Description</th>
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Source &rarr; Destination</th>
                <th className="py-3 px-4">Telemetry Class</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredEvents.length > 0 ? (
                filteredEvents.map((ev) => {
                  const isExpanded = expandedId === ev.id;
                  return (
                    <React.Fragment key={ev.id}>
                      <tr className="hover:bg-slate-900/40 transition-colors">
                        <td className="py-3 px-4">
                          <button
                            onClick={() => setExpandedId(isExpanded ? null : ev.id)}
                            className="text-slate-400 hover:text-cyan-400"
                          >
                            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                          </button>
                        </td>
                        <td className="py-3 px-4 font-mono text-[11px] text-slate-400 whitespace-nowrap">
                          {formatLocalDateTime(ev.timestamp)}
                        </td>
                        <td className="py-3 px-4">
                          <div className="font-semibold text-slate-200">{ev.title}</div>
                          <div className="text-[11px] text-slate-400 truncate max-w-sm">{ev.description}</div>
                        </td>
                        <td className="py-3 px-4 text-slate-300 font-mono text-[11px]">{ev.event_type}</td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                              ev.severity === "Critical"
                                ? "bg-red-950 text-red-400 border border-red-800/40"
                                : ev.severity === "High"
                                ? "bg-orange-950 text-orange-400 border border-orange-800/40"
                                : ev.severity === "Medium"
                                ? "bg-amber-950 text-amber-400 border border-amber-800/40"
                                : "bg-slate-800 text-slate-300"
                            }`}
                          >
                            {ev.severity}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-[11px] text-slate-300 whitespace-nowrap">
                          {ev.source_ip || "Internal"}
                          {ev.destination_ip && (
                            <>
                              {" "}&rarr; {ev.destination_ip}
                              {ev.destination_port && `:${ev.destination_port}`}
                            </>
                          )}
                        </td>
                        <td className="py-3 px-4">
                          {ev.is_simulated ? (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-purple-950 text-purple-300 border border-purple-800">
                              SIMULATED
                            </span>
                          ) : (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800/40">
                              REAL TELEMETRY
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <a
                            href={`/ai-analyst?type=general&query=${encodeURIComponent(
                              `Analyze event: ${ev.title}. Source IP: ${ev.source_ip}, Destination: ${ev.destination_ip}:${ev.destination_port}`
                            )}`}
                            className="p-1.5 rounded hover:bg-slate-800 text-cyan-400 hover:text-cyan-300 inline-flex items-center gap-1 text-[11px]"
                            title="Investigate with AI"
                          >
                            <Bot className="w-3.5 h-3.5" />
                          </a>
                        </td>
                      </tr>

                      {/* Raw Payload Expansion */}
                      {isExpanded && (
                        <tr className="bg-slate-950/80">
                          <td colSpan={8} className="p-4">
                            <div className="space-y-2 text-xs">
                              <div className="flex items-center justify-between text-slate-400 font-mono text-[11px]">
                                <span className="flex items-center gap-1.5">
                                  <Code className="w-3.5 h-3.5 text-cyan-400" />
                                  Raw Security Event Record (ID: {ev.id})
                                </span>
                                {ev.source_ip && (
                                  <a
                                    href={`/ip-intel?ip=${ev.source_ip}`}
                                    className="text-cyan-400 hover:underline flex items-center gap-1"
                                  >
                                    Investigate Source IP ({ev.source_ip}) &rarr;
                                  </a>
                                )}
                              </div>
                              <pre className="p-3 rounded bg-slate-900 border border-slate-800 text-cyan-300 font-mono text-[11px] overflow-x-auto whitespace-pre-wrap">
                                {ev.raw_payload || JSON.stringify(ev, null, 2)}
                              </pre>
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
                    {loading ? "Loading event ledger..." : "No events match current filter."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}
