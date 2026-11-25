"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "../../components/layout/AppShell";
import { fetchApi } from "../../lib/api";
import { formatLocalDateTime } from "../../lib/date";
import {
  FileText,
  Download,
  BarChart2,
  ShieldCheck,
  CheckCircle,
  AlertTriangle,
  Server,
  Cloud,
  Network as NetworkIcon,
  Radio,
  FileSpreadsheet,
  FileCode,
  Calendar,
  Layers,
} from "lucide-react";

export default function ReportsPage() {
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState<string | null>(null);

  useEffect(() => {
    fetchApi("/reports/summary")
      .then((data) => setSummary(data))
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  const downloadFile = async (endpoint: string, filename: string, typeKey: string) => {
    try {
      setDownloading(typeKey);
      const token = localStorage.getItem("sentinel_token");
      const activeOrg = localStorage.getItem("sentinel_active_org") || localStorage.getItem("sentinel_org_id");
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const res = await fetch(`${apiBase}/reports/${endpoint}`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Organization-Id": activeOrg || "",
        },
      });

      if (!res.ok) {
        throw new Error(`Export failed with HTTP ${res.status}`);
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      alert(`Export failed: ${e.message}`);
    } finally {
      setDownloading(null);
    }
  };

  const reportItems = [
    {
      id: "incidents",
      title: "Incident Cases Ledger",
      category: "Case Management",
      icon: ShieldCheck,
      iconColor: "text-amber-400",
      description: "Comprehensive audit trail of all security incidents, severity levels, assignees, creation dates, and resolution notes.",
      actions: [
        { label: "CSV Export", ext: "csv", endpoint: "incidents/csv", icon: FileSpreadsheet },
        { label: "JSON Export", ext: "json", endpoint: "incidents/json", icon: FileCode },
      ],
    },
    {
      id: "events",
      title: "Security Telemetry Events",
      category: "Telemetry Ingestion",
      icon: Radio,
      iconColor: "text-cyan-400",
      description: "Chronological log of raw security events with source/destination IPs, ports, protocols, and simulation tags.",
      actions: [
        { label: "CSV Export", ext: "csv", endpoint: "events/csv", icon: FileSpreadsheet },
        { label: "JSON Export", ext: "json", endpoint: "events/json", icon: FileCode },
      ],
    },
    {
      id: "threat-intel",
      title: "Threat Intelligence Indicators",
      category: "Threat Intel",
      icon: AlertTriangle,
      iconColor: "text-red-400",
      description: "Normalized indicator database from AbuseIPDB, GreyNoise, AlienVault OTX, and Spamhaus with confidence ratings and timestamps.",
      actions: [
        { label: "CSV Export", ext: "csv", endpoint: "threat-intel/csv", icon: FileSpreadsheet },
      ],
    },
    {
      id: "network",
      title: "Network Inventory & Devices",
      category: "Asset Intelligence",
      icon: NetworkIcon,
      iconColor: "text-emerald-400",
      description: "Discovered network assets, MAC addresses, hostnames, hardware vendors, discovery mechanisms, and authorization status.",
      actions: [
        { label: "CSV Export", ext: "csv", endpoint: "network/csv", icon: FileSpreadsheet },
      ],
    },
    {
      id: "aws",
      title: "AWS Cloud Security Findings",
      category: "Cloud Security",
      icon: Cloud,
      iconColor: "text-indigo-400",
      description: "Security Hub, GuardDuty, and IAM findings for AWS accounts with remediation guidance and simulation flags.",
      actions: [
        { label: "CSV Export", ext: "csv", endpoint: "aws/csv", icon: FileSpreadsheet },
      ],
    },
  ];

  return (
    <AppShell>
      <div className="space-y-6 max-w-6xl">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
              <FileText className="w-5 h-5 text-cyan-400" />
              Security Reports &amp; Compliance Exports
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Generate structured, audit-ready data exports across incidents, telemetry, threat intelligence, and cloud posture
            </p>
          </div>
          {summary?.generated_at && (
            <div className="text-xs text-slate-500 font-mono flex items-center gap-1.5 self-start sm:self-auto bg-slate-900/60 border border-slate-800 px-3 py-1.5 rounded-lg">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              <span>Synced: {formatLocalDateTime(summary.generated_at)}</span>
            </div>
          )}
        </div>

        {/* Executive Summary Cards */}
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="p-3.5 rounded-xl bg-[#0F172A] border border-slate-800">
              <div className="text-[10px] text-slate-400 uppercase font-semibold">Monitored Assets</div>
              <div className="text-xl font-bold font-mono text-slate-100 mt-1">{summary.total_assets_monitored}</div>
            </div>
            <div className="p-3.5 rounded-xl bg-[#0F172A] border border-slate-800">
              <div className="text-[10px] text-slate-400 uppercase font-semibold">Discovered Devices</div>
              <div className="text-xl font-bold font-mono text-emerald-400 mt-1">{summary.total_network_devices_discovered}</div>
            </div>
            <div className="p-3.5 rounded-xl bg-[#0F172A] border border-slate-800">
              <div className="text-[10px] text-slate-400 uppercase font-semibold">Recorded Events</div>
              <div className="text-xl font-bold font-mono text-cyan-400 mt-1">{summary.total_security_events_recorded}</div>
            </div>
            <div className="p-3.5 rounded-xl bg-[#0F172A] border border-slate-800">
              <div className="text-[10px] text-slate-400 uppercase font-semibold">Total Incidents</div>
              <div className="text-xl font-bold font-mono text-amber-400 mt-1">{summary.total_incidents}</div>
            </div>
            <div className="p-3.5 rounded-xl bg-[#0F172A] border border-slate-800">
              <div className="text-[10px] text-slate-400 uppercase font-semibold">Cloud Findings</div>
              <div className="text-xl font-bold font-mono text-indigo-400 mt-1">{summary.active_aws_findings}</div>
            </div>
            <div className="p-3.5 rounded-xl bg-[#0F172A] border border-slate-800">
              <div className="text-[10px] text-slate-400 uppercase font-semibold">Resolution Rate</div>
              <div className="text-xl font-bold font-mono text-emerald-400 mt-1">{summary.incident_resolution_rate}</div>
            </div>
          </div>
        )}

        {/* Export Artifacts Grid */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <h2 className="text-sm font-semibold text-slate-200">Export Modules &amp; Compliance Ledgers</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {reportItems.map((item) => {
              const Icon = item.icon;
              return (
                <div
                  key={item.id}
                  className="p-5 rounded-xl bg-[#0F172A] border border-slate-800 hover:border-slate-700 transition flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                          <Icon className={`w-4 h-4 ${item.iconColor}`} />
                        </div>
                        <div>
                          <h3 className="text-sm font-semibold text-slate-200">{item.title}</h3>
                          <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                            {item.category}
                          </span>
                        </div>
                      </div>
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed pt-1">
                      {item.description}
                    </p>
                  </div>

                  <div className="pt-4 mt-4 border-t border-slate-800/80 flex items-center gap-2">
                    {item.actions.map((act) => {
                      const ActIcon = act.icon;
                      const key = `${item.id}-${act.ext}`;
                      const isCurrentDownloading = downloading === key;
                      return (
                        <button
                          key={act.ext}
                          onClick={() =>
                            downloadFile(
                              act.endpoint,
                              `sentinel_${item.id}_${Date.now()}.${act.ext}`,
                              key
                            )
                          }
                          disabled={isCurrentDownloading}
                          className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium flex items-center gap-1.5 border border-slate-700/60 transition disabled:opacity-50"
                        >
                          <ActIcon className="w-3.5 h-3.5 text-cyan-400" />
                          <span>{isCurrentDownloading ? "Exporting..." : act.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Free-tier Compliance & Audit Note */}
        <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 text-xs text-slate-400 flex items-start gap-3">
          <ShieldCheck className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-slate-300">Data Portability &amp; Tenant Isolation Standard</div>
            <div className="mt-1 text-[11px] leading-relaxed">
              All exports are scoped exclusively to the authenticated tenant organization. Simulated telemetry and threat intelligence feeds are explicitly identified in exported schemas to prevent falsification of audit evidence.
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
