"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "../../components/layout/AppShell";
import { fetchApi } from "../../lib/api";
import {
  ShieldAlert,
  Server,
  Cpu,
  Activity,
  AlertOctagon,
  Network,
  ArrowUpRight,
  RefreshCw,
  Sparkles,
  CheckCircle,
  AlertTriangle,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  Cell,
} from "recharts";

export default function DashboardPage() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadStats = async () => {
    try {
      const data = await fetchApi("/dashboard/stats");
      setStats(data);
    } catch (e) {
      console.error("Failed to load dashboard metrics", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, 15000); // 15s refresh
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    loadStats();
  };

  const severityColors: Record<string, string> = {
    Critical: "#ef4444",
    High: "#f97316",
    Medium: "#f59e0b",
    Low: "#3b82f6",
    Informational: "#64748b",
  };

  const barData = stats
    ? Object.entries(stats.severity_distribution || {}).map(([sev, count]) => ({
        name: sev,
        count: count,
        color: severityColors[sev] || "#06b6d4",
      }))
    : [];

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
              Security Operations Center Overview
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Live telemetry, endpoint sensor status, network visibility, and threat detections
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleRefresh}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 hover:text-cyan-400 hover:border-slate-700 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
              <span>Refresh Metrics</span>
            </button>
            <a
              href="/simulation"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-950/80 border border-cyan-500/40 text-xs font-semibold text-cyan-300 hover:bg-cyan-900/80 transition-colors"
            >
              <span>Attack Simulation Lab</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>

        {/* Primary Metric KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 shadow-sm">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[11px] font-medium uppercase tracking-wider">Registered Assets</span>
              <Server className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="mt-2 text-2xl font-bold text-slate-100">{stats?.total_assets ?? 0}</div>
            <div className="mt-1 text-[10px] text-slate-400">Monitored endpoints &amp; servers</div>
          </div>

          <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 shadow-sm">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[11px] font-medium uppercase tracking-wider">Active Sensors</span>
              <Cpu className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="mt-2 text-2xl font-bold text-emerald-400">
              {stats?.online_sensors ?? 0} <span className="text-xs text-slate-400 font-normal">/ {(stats?.online_sensors || 0) + (stats?.offline_sensors || 0)}</span>
            </div>
            <div className="mt-1 text-[10px] text-slate-400">{stats?.offline_sensors ?? 0} offline or pending</div>
          </div>

          <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 shadow-sm">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[11px] font-medium uppercase tracking-wider">Events (24h)</span>
              <Activity className="w-4 h-4 text-blue-400" />
            </div>
            <div className="mt-2 text-2xl font-bold text-slate-100">{stats?.total_events_24h ?? 0}</div>
            <div className="mt-1 text-[10px] text-slate-400">Real &amp; simulated logs</div>
          </div>

          <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 shadow-sm">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[11px] font-medium uppercase tracking-wider">Critical/High</span>
              <ShieldAlert className="w-4 h-4 text-red-400" />
            </div>
            <div className="mt-2 text-2xl font-bold text-red-400">{stats?.critical_high_alerts ?? 0}</div>
            <div className="mt-1 text-[10px] text-slate-400">Active threat detections</div>
          </div>

          <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 shadow-sm">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[11px] font-medium uppercase tracking-wider">Open Incidents</span>
              <AlertOctagon className="w-4 h-4 text-amber-400" />
            </div>
            <div className="mt-2 text-2xl font-bold text-amber-400">{stats?.open_incidents ?? 0}</div>
            <div className="mt-1 text-[10px] text-slate-400">Under SOC investigation</div>
          </div>

          <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 shadow-sm">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[11px] font-medium uppercase tracking-wider">LAN Devices</span>
              <Network className="w-4 h-4 text-purple-400" />
            </div>
            <div className="mt-2 text-2xl font-bold text-purple-300">{stats?.network_devices_count ?? 0}</div>
            <div className="mt-1 text-[10px] text-slate-400">Discovered neighbors</div>
          </div>
        </div>

        {/* Fleet Risk & Telemetry Segregation Strip */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between text-xs">
            <div>
              <span className="text-slate-400 text-[11px] block">Fleet Average Risk Score</span>
              <span className="font-semibold text-slate-200 mt-0.5 block">
                {stats?.fleet_average_risk_score ?? 15} / 100
                <span className={`ml-2 px-1.5 py-0.2 rounded text-[10px] ${
                  (stats?.fleet_average_risk_score ?? 15) >= 60 ? "bg-red-950 text-red-400" :
                  (stats?.fleet_average_risk_score ?? 15) >= 30 ? "bg-amber-950 text-amber-400" :
                  "bg-emerald-950 text-emerald-400"
                }`}>
                  {(stats?.fleet_average_risk_score ?? 15) >= 60 ? "Elevated" : (stats?.fleet_average_risk_score ?? 15) >= 30 ? "Moderate" : "Nominal"}
                </span>
              </span>
            </div>
            <div className="text-right">
              <span className="text-[11px] text-slate-400 block">High Risk Endpoints</span>
              <span className="text-sm font-bold text-red-400">{stats?.high_risk_assets_count ?? 0}</span>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between text-xs">
            <div>
              <span className="text-slate-400 text-[11px] block">Verified Genuine Telemetry</span>
              <span className="font-semibold text-cyan-300 mt-0.5 block">
                {stats?.genuine_events_24h ?? 0} observations (24h)
              </span>
            </div>
            <span className="px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800/60 text-cyan-300 font-mono text-[10px]">
              OBSERVED
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between text-xs">
            <div>
              <span className="text-slate-400 text-[11px] block">Attack Lab Simulated Signals</span>
              <span className="font-semibold text-amber-400 mt-0.5 block">
                {stats?.simulated_events_24h ?? 0} events &bull; {stats?.simulated_incidents_count ?? 0} incident(s)
              </span>
            </div>
            <span className="px-2 py-0.5 rounded bg-amber-950 border border-amber-800/60 text-amber-400 font-mono text-[10px]">
              SIMULATED
            </span>
          </div>
        </div>

        {/* Charts: Event Trends & Severity Distribution */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 p-5 rounded-xl bg-[#0F172A] border border-slate-800">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold text-slate-200">Security Telemetry Ingestion Trend (24h)</h2>
                <p className="text-xs text-slate-400">Hourly volume of endpoint and network security events</p>
              </div>
              <span className="text-[11px] text-cyan-400 font-mono">Real Application Data</span>
            </div>
            <div className="h-60 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={stats?.event_trend_24h || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0b1120", borderColor: "#334155", borderRadius: "8px", fontSize: "12px" }}
                  />
                  <Line type="monotone" dataKey="events" stroke="#06b6d4" strokeWidth={2} dot={{ r: 3, fill: "#06b6d4" }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="p-5 rounded-xl bg-[#0F172A] border border-slate-800">
            <h2 className="text-sm font-semibold text-slate-200 mb-1">Severity Distribution</h2>
            <p className="text-xs text-slate-400 mb-4">Categorized threat weight</p>
            <div className="h-60 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                  <XAxis type="number" stroke="#64748b" tick={{ fontSize: 11 }} allowDecimals={false} />
                  <YAxis type="category" dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} width={90} />
                  <Tooltip contentStyle={{ backgroundColor: "#0b1120", borderColor: "#334155", borderRadius: "8px", fontSize: "12px" }} />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {barData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Tables: Suspicious IPs & Security Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Recently Detected Suspicious IPs */}
          <div className="p-5 rounded-xl bg-[#0F172A] border border-slate-800">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-slate-200">Observed Suspicious IP Indicators</h2>
              <a href="/ip-intel" className="text-xs text-cyan-400 hover:underline">
                Investigate in IP Explorer &rarr;
              </a>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 font-medium">
                    <th className="pb-2">IP Address</th>
                    <th className="pb-2">Triggered Rule</th>
                    <th className="pb-2">Severity</th>
                    <th className="pb-2">Source</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {stats?.recent_suspicious_ips?.length > 0 ? (
                    stats.recent_suspicious_ips.map((item: any, idx: number) => (
                      <tr key={idx} className="hover:bg-slate-900/50">
                        <td className="py-2.5 font-mono text-cyan-300 font-medium">{item.ip}</td>
                        <td className="py-2.5 text-slate-300 truncate max-w-[160px]">{item.rule}</td>
                        <td className="py-2.5">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                              item.severity === "Critical"
                                ? "bg-red-950/80 text-red-400 border border-red-800/50"
                                : item.severity === "High"
                                ? "bg-orange-950/80 text-orange-400 border border-orange-800/50"
                                : "bg-amber-950/80 text-amber-400 border border-amber-800/50"
                            }`}
                          >
                            {item.severity}
                          </span>
                        </td>
                        <td className="py-2.5">
                          {item.is_simulated ? (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800">
                              SIMULATED
                            </span>
                          ) : (
                            <span className="text-[10px] text-slate-400">TELEMETRY</span>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="py-6 text-center text-slate-500">
                        No suspicious IPs observed in recent telemetry window.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recent Security Activity Stream */}
          <div className="p-5 rounded-xl bg-[#0F172A] border border-slate-800">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-slate-200">Recent Security Activity Stream</h2>
              <a href="/events" className="text-xs text-cyan-400 hover:underline">
                View All Events &rarr;
              </a>
            </div>
            <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
              {stats?.recent_activity?.length > 0 ? (
                stats.recent_activity.map((ev: any) => (
                  <div
                    key={ev.id}
                    className="p-2.5 rounded-lg bg-slate-900/70 border border-slate-800 flex items-center justify-between text-xs"
                  >
                    <div className="truncate pr-2">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-200 truncate">{ev.title}</span>
                        {ev.is_simulated && (
                          <span className="text-[9px] px-1 py-0.2 rounded bg-purple-950 text-purple-300 border border-purple-800">
                            SIMULATED
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                        {ev.source_ip || "Internal"} &rarr; {ev.destination_ip || "N/A"}
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${
                          ev.severity === "Critical"
                            ? "text-red-400"
                            : ev.severity === "High"
                            ? "text-orange-400"
                            : "text-slate-400"
                        }`}
                      >
                        {ev.severity}
                      </span>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        {new Date(ev.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-8 text-center text-slate-500 text-xs">No recent events logged.</div>
              )}
            </div>
          </div>
        </div>

        {/* Integration Health Matrix */}
        <div className="p-4 rounded-xl bg-[#0B1120] border border-slate-800">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            System &amp; Integration Health Matrix
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
            <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
              <div className="text-slate-400 text-[11px]">Database Dialect</div>
              <div className="font-semibold text-slate-200 mt-1 uppercase flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                {stats?.integration_health?.database?.dialect || "SQL"}
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
              <div className="text-slate-400 text-[11px]">AI Assistant Provider</div>
              <div className="font-semibold text-cyan-300 mt-1 flex items-center gap-1.5 truncate">
                <Sparkles className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
                <span className="truncate">{stats?.integration_health?.ai_provider?.status || "CONFIGURED"}</span>
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
              <div className="text-slate-400 text-[11px]">Queue &amp; Caching</div>
              <div className="font-semibold text-slate-200 mt-1 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                <span>{stats?.integration_health?.redis?.status || "ACTIVE"}</span>
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
              <div className="text-slate-400 text-[11px]">Threat Intel Feed</div>
              <div className="font-semibold text-slate-300 mt-1 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
                <span>{stats?.integration_health?.abuseipdb?.status || "LOCAL CACHE"}</span>
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
              <div className="text-slate-400 text-[11px]">Email Dispatcher</div>
              <div className="font-semibold text-slate-400 mt-1 flex items-center gap-1.5 truncate">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
                <span className="truncate">SAFE DEV MOCK</span>
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800">
              <div className="text-slate-400 text-[11px]">AWS Cloud Security</div>
              <div className="font-semibold text-slate-400 mt-1">
                {stats?.integration_health?.aws_cloud?.status || "NOT CONFIGURED"}
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
