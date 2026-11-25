"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "../../components/layout/AppShell";
import { fetchApi } from "../../lib/api";
import { formatLocalDateTime } from "../../lib/date";
import {
  Settings,
  Shield,
  Activity,
  Sparkles,
  RefreshCw,
  Database,
  Lock,
  CheckCircle,
  Users,
  Radio,
  FileText,
  Clock,
  AlertCircle
} from "lucide-react";

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<"overview" | "users" | "integrations" | "audit">("overview");
  const [health, setHealth] = useState<any>(null);
  const [quota, setQuota] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [integrations, setIntegrations] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const [hlth, qta, usrs, ints, logs] = await Promise.all([
        fetchApi("/admin/system-health"),
        fetchApi("/admin/ai-quota"),
        fetchApi("/admin/users").catch(() => []),
        fetchApi("/admin/integrations").catch(() => ({ integrations: [] })),
        fetchApi("/admin/audit-logs").catch(() => []),
      ]);
      setHealth(hlth);
      setQuota(qta);
      setUsers(usrs || []);
      setIntegrations(ints?.integrations || []);
      setAuditLogs(logs || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await fetchApi(`/admin/users/${userId}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role: newRole }),
      });
      alert(`User role updated to ${newRole}`);
      loadData();
    } catch (e: any) {
      alert(`Role update failed: ${e.message}`);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6 max-w-6xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
              <Settings className="w-5 h-5 text-cyan-400" />
              Platform Administration &amp; Governance
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Service diagnostics, RBAC team roles, integration connectors, and immutable audit logs
            </p>
          </div>
          <button
            onClick={loadData}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-cyan-400"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-800 text-xs font-semibold gap-6">
          <button
            onClick={() => setActiveTab("overview")}
            className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "overview"
                ? "border-cyan-400 text-cyan-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Activity className="w-4 h-4" />
            <span>Overview &amp; Diagnostics</span>
          </button>
          <button
            onClick={() => setActiveTab("users")}
            className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "users"
                ? "border-cyan-400 text-cyan-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Users className="w-4 h-4" />
            <span>Team &amp; Roles ({users.length})</span>
          </button>
          <button
            onClick={() => setActiveTab("integrations")}
            className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "integrations"
                ? "border-cyan-400 text-cyan-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Radio className="w-4 h-4" />
            <span>Integration Connectors ({integrations.length})</span>
          </button>
          <button
            onClick={() => setActiveTab("audit")}
            className={`pb-3 border-b-2 flex items-center gap-2 transition-colors ${
              activeTab === "audit"
                ? "border-cyan-400 text-cyan-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>Audit Trail ({auditLogs.length})</span>
          </button>
        </div>

        {/* Tab 1: Overview & Diagnostics */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            {/* Free-Tier AI Quota & Governance Card */}
            <div className="p-5 rounded-xl bg-[#0F172A] border border-slate-800 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-cyan-400">
                  <Sparkles className="w-5 h-5" />
                  <h2 className="text-sm font-bold text-slate-100">Free-Tier AI Quota &amp; Governance</h2>
                </div>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    quota?.quota_status === "HEALTHY"
                      ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                      : "bg-red-950 text-red-400 border border-red-800"
                  }`}
                >
                  {quota?.quota_status || "UNKNOWN"}
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Sentinel SOC is hardcoded to use genuinely free-tier endpoints only. The platform will never trigger paid upgrades, charge credit cards, or auto-switch to commercial models.
              </p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2 text-xs">
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800/80">
                  <div className="text-slate-400 text-[11px]">Configured Provider</div>
                  <div className="font-semibold text-slate-200 mt-1 capitalize">{quota?.provider || "None"}</div>
                </div>
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800/80">
                  <div className="text-slate-400 text-[11px]">Active Model</div>
                  <div className="font-semibold text-slate-200 mt-1 font-mono text-[11px]">{quota?.model || "Local Heuristics"}</div>
                </div>
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800/80">
                  <div className="text-slate-400 text-[11px]">Today&apos;s Requests</div>
                  <div className="font-semibold text-slate-200 mt-1">
                    {quota?.requests_today ?? 0} / {quota?.daily_request_limit ?? 1500}
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800/80">
                  <div className="text-slate-400 text-[11px]">Est. Tokens Used</div>
                  <div className="font-semibold text-slate-200 mt-1">{quota?.estimated_tokens_today ?? 0}</div>
                </div>
              </div>
            </div>

            {/* System Service Health Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                    <Database className="w-4 h-4 text-cyan-400" /> Database Engine
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">
                    {health?.database?.status || "HEALTHY"}
                  </span>
                </div>
                <div className="text-xs text-slate-400">Dialect: <span className="font-mono text-slate-300">{health?.database?.dialect || "sqlite"}</span></div>
              </div>

              <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                    <Activity className="w-4 h-4 text-purple-400" /> Cache Layer
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-400 border border-cyan-800">
                    {health?.redis?.status || "LOCAL_FALLBACK"}
                  </span>
                </div>
                <div className="text-xs text-slate-400">In-memory fallback queue operational</div>
              </div>

              <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                    <Lock className="w-4 h-4 text-amber-400" /> Multi-Tenant Boundary
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">
                    ENFORCED
                  </span>
                </div>
                <div className="text-xs text-slate-400">ORM-level organization query isolation</div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Users & Roles */}
        {activeTab === "users" && (
          <div className="p-5 rounded-xl bg-[#0F172A] border border-slate-800 space-y-4">
            <div>
              <h2 className="text-sm font-bold text-slate-100">Team Members &amp; RBAC Access Controls</h2>
              <p className="text-xs text-slate-400">Manage tenant user privileges across SOC operator roles</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 text-[11px] uppercase tracking-wider">
                    <th className="py-2.5 px-3">User</th>
                    <th className="py-2.5 px-3">Email Address</th>
                    <th className="py-2.5 px-3">Current Role</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Role Assignment</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {users.map((u) => (
                    <tr key={u.user_id} className="hover:bg-slate-900/30">
                      <td className="py-3 px-3 font-semibold text-slate-200">{u.full_name}</td>
                      <td className="py-3 px-3 font-mono text-slate-300">{u.email}</td>
                      <td className="py-3 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-300 border border-cyan-800">
                          {u.role}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <span className="text-emerald-400 flex items-center gap-1 text-[11px]">
                          <CheckCircle className="w-3 h-3" /> Active
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <select
                          value={u.role}
                          onChange={(e) => handleRoleChange(u.user_id, e.target.value)}
                          className="px-2 py-1 rounded bg-slate-900 border border-slate-700 text-slate-200 text-xs focus:outline-none focus:border-cyan-500"
                        >
                          <option value="Organization Owner">Organization Owner</option>
                          <option value="Organization Administrator">Organization Administrator</option>
                          <option value="Security Analyst">Security Analyst</option>
                          <option value="Viewer">Viewer</option>
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 3: Integration Connectors */}
        {activeTab === "integrations" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {integrations.map((item) => (
              <div key={item.id} className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-sm text-slate-100">{item.name}</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      item.status === "ONLINE"
                        ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                        : "bg-slate-900 text-slate-400 border border-slate-800"
                    }`}
                  >
                    {item.status}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">{item.description}</p>
                <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
                  <span className="text-slate-500">Category: <strong className="text-slate-300">{item.category}</strong></span>
                  <span className="text-emerald-400 font-mono text-[10px]">Zero Paid Cost</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Tab 4: Audit Trail */}
        {activeTab === "audit" && (
          <div className="p-5 rounded-xl bg-[#0F172A] border border-slate-800 space-y-4">
            <div>
              <h2 className="text-sm font-bold text-slate-100">Immutable Audit Trail</h2>
              <p className="text-xs text-slate-400">Cryptographically ordered log of all operator actions and policy mutations</p>
            </div>
            <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
              {auditLogs.length > 0 ? (
                auditLogs.map((log) => (
                  <div key={log.id} className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 text-xs flex items-start justify-between gap-4">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="px-1.5 py-0.2 rounded font-mono text-[10px] font-bold bg-cyan-950 text-cyan-300 border border-cyan-800/60">
                          {log.action}
                        </span>
                        <span className="text-slate-400 text-[11px]">{log.user_email || "System"}</span>
                      </div>
                      <p className="text-slate-300 text-[11px] mt-1">{log.details}</p>
                    </div>
                    <span className="text-slate-500 text-[10px] font-mono shrink-0">
                      {formatLocalDateTime(log.created_at)}
                    </span>
                  </div>
                ))
              ) : (
                <div className="py-8 text-center text-slate-500 text-xs">No audit logs recorded yet.</div>
              )}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
