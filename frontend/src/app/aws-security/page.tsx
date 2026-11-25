"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "../../components/layout/AppShell";
import { fetchApi } from "../../lib/api";
import { formatLocalDateTime } from "../../lib/date";
import {
  Cloud,
  ShieldCheck,
  AlertTriangle,
  Plus,
  RefreshCw,
  Info,
  Play,
  Key,
  Copy,
  CheckCircle2,
  Trash2,
  Server,
  Layers,
  Lock,
  ExternalLink,
  Loader2
} from "lucide-react";

export default function AwsSecurityPage() {
  const [status, setStatus] = useState<any>(null);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [findings, setFindings] = useState<any[]>([]);
  const [resources, setResources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Active view tab: Findings vs Cloud Resources vs Accounts
  const [activeTab, setActiveTab] = useState<"findings" | "resources" | "accounts">("findings");
  const [serviceFilter, setServiceFilter] = useState<string>("ALL");

  // Modals
  const [registerModalOpen, setRegisterModalOpen] = useState(false);
  const [policyModalOpen, setPolicyModalOpen] = useState(false);
  const [policyData, setPolicyData] = useState<any>(null);
  const [copiedPolicy, setCopiedPolicy] = useState(false);

  // Register account form
  const [accId, setAccId] = useState("");
  const [accName, setAccName] = useState("");
  const [roleArn, setRoleArn] = useState("");
  const [extId, setExtId] = useState("");
  const [region, setRegion] = useState("us-east-1");

  // Loading states
  const [loadingFixtures, setLoadingFixtures] = useState(false);
  const [fixtureSuccessMsg, setFixtureSuccessMsg] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [st, accs, fnds, rscs] = await Promise.all([
        fetchApi("/aws/status"),
        fetchApi("/aws/accounts"),
        fetchApi("/aws/findings"),
        fetchApi("/aws/resources")
      ]);
      setStatus(st);
      setAccounts(accs || []);
      setFindings(fnds || []);
      setResources(rscs || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleLoadAllFixtures = async () => {
    setLoadingFixtures(true);
    setFixtureSuccessMsg(null);
    try {
      const res = await fetchApi("/aws/fixtures/load-all-fixtures", { method: "POST" });
      setFixtureSuccessMsg(res.message || "Offline zero-cost simulated fixtures loaded successfully.");
      loadData();
    } catch (err: any) {
      alert(`Failed to load fixtures: ${err.message}`);
    } finally {
      setLoadingFixtures(false);
    }
  };

  const handleOpenPolicyModal = async () => {
    setPolicyModalOpen(true);
    try {
      const data = await fetchApi("/aws/iam-policy-template");
      setPolicyData(data);
    } catch (err: any) {
      alert(`Failed to load policy template: ${err.message}`);
    }
  };

  const handleCopyPolicy = () => {
    if (policyData?.policy_json) {
      navigator.clipboard.writeText(JSON.stringify(policyData.policy_json, null, 2));
      setCopiedPolicy(true);
      setTimeout(() => setCopiedPolicy(false), 2000);
    }
  };

  const handleRegisterAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await fetchApi("/aws/accounts", {
        method: "POST",
        body: JSON.stringify({
          account_id: accId,
          account_name: accName,
          role_arn: roleArn,
          external_id: extId,
          region
        })
      });
      setRegisterModalOpen(false);
      setAccId("");
      setAccName("");
      setRoleArn("");
      setExtId("");
      loadData();
    } catch (err: any) {
      alert(`Account registration failed: ${err.message}`);
    }
  };

  const handleDisconnectAccount = async (accountId: string) => {
    if (!confirm("Are you sure you want to disconnect this AWS account?")) return;
    try {
      await fetchApi(`/aws/accounts/${accountId}`, { method: "DELETE" });
      loadData();
    } catch (err: any) {
      alert(`Disconnect failed: ${err.message}`);
    }
  };

  const filteredFindings = serviceFilter === "ALL"
    ? findings
    : findings.filter((f) => f.service?.toUpperCase() === serviceFilter);

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
              <Cloud className="w-5 h-5 text-cyan-400" />
              AWS Cloud Security &amp; Findings
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Least-privilege AssumeRole, GuardDuty threat telemetry, IAM posture, and safe offline simulation fixtures.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={handleOpenPolicyModal}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-cyan-400 text-xs font-semibold"
            >
              <Key className="w-3.5 h-3.5 text-cyan-400" />
              <span>IAM Policy Template</span>
            </button>
            <button
              onClick={handleLoadAllFixtures}
              disabled={loadingFixtures}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-950 border border-cyan-800 text-cyan-300 hover:bg-cyan-900/60 text-xs font-semibold disabled:opacity-50 transition-colors"
            >
              {loadingFixtures ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 text-cyan-400" />}
              <span>Load Zero-Cost Fixtures</span>
            </button>
            <button
              onClick={() => setRegisterModalOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-semibold"
            >
              <Plus className="w-4 h-4" />
              <span>Connect Account</span>
            </button>
          </div>
        </div>

        {/* Free-Tier Safety Banner */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-300 flex items-start gap-3">
          <Info className="w-5 h-5 text-cyan-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold text-slate-200">Zero Cost AWS Integration Architecture:</span>
            <p className="text-slate-400 leading-relaxed">
              Sentinel SOC strictly enforces free-tier safety. Cross-account access uses cross-account AssumeRole with External ID and read-only IAM policies. Live AWS queries are optional; you can explore full security correlation using the offline fixtures with zero financial charge.
            </p>
          </div>
        </div>

        {fixtureSuccessMsg && (
          <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-900/50 text-emerald-300 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>{fixtureSuccessMsg}</span>
          </div>
        )}

        {/* Status Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800">
            <div className="text-[11px] text-slate-400 uppercase font-semibold">Integration Status</div>
            <div className="text-base font-bold text-slate-200 mt-1 flex items-center gap-2">
              <span className={`w-2.5 h-2.5 rounded-full ${accounts.length > 0 ? "bg-emerald-400" : "bg-slate-500"}`} />
              <span>{accounts.length > 0 ? "ROLE CONFIGURED" : "NOT CONFIGURED"}</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1">{status?.message || "AssumeRole ready"}</p>
          </div>

          <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800">
            <div className="text-[11px] text-slate-400 uppercase font-semibold">Connected Accounts</div>
            <div className="text-lg font-bold text-slate-200 mt-1 font-mono">{accounts.length}</div>
            <p className="text-[11px] text-slate-500 mt-1">Cross-account AssumeRole</p>
          </div>

          <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800">
            <div className="text-[11px] text-slate-400 uppercase font-semibold">Security Findings</div>
            <div className="text-lg font-bold text-cyan-400 mt-1 font-mono">{findings.length}</div>
            <p className="text-[11px] text-slate-500 mt-1">GuardDuty / IAM / S3 findings</p>
          </div>

          <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800">
            <div className="text-[11px] text-slate-400 uppercase font-semibold">Audited Resources</div>
            <div className="text-lg font-bold text-slate-200 mt-1 font-mono">{resources.length}</div>
            <p className="text-[11px] text-slate-500 mt-1">S3, EC2, IAM, Security Groups</p>
          </div>
        </div>

        {/* View Selection Tabs */}
        <div className="flex border-b border-slate-800 text-xs font-semibold gap-6">
          <button
            onClick={() => setActiveTab("findings")}
            className={`pb-3 border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === "findings"
                ? "border-cyan-400 text-cyan-300"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <AlertTriangle className="w-4 h-4" />
            <span>Security Findings ({findings.length})</span>
          </button>
          <button
            onClick={() => setActiveTab("resources")}
            className={`pb-3 border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === "resources"
                ? "border-cyan-400 text-cyan-300"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Server className="w-4 h-4" />
            <span>Cloud Asset Inventory ({resources.length})</span>
          </button>
          <button
            onClick={() => setActiveTab("accounts")}
            className={`pb-3 border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === "accounts"
                ? "border-cyan-400 text-cyan-300"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Lock className="w-4 h-4" />
            <span>Connected Accounts ({accounts.length})</span>
          </button>
        </div>

        {/* TAB 1: Findings Table */}
        {activeTab === "findings" && (
          <div className="space-y-4">
            {/* Service Filters */}
            <div className="flex flex-wrap items-center gap-2">
              {["ALL", "IAM", "S3", "SECURITYGROUP", "GUARDDUTY"].map((srv) => (
                <button
                  key={srv}
                  onClick={() => setServiceFilter(srv)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                    serviceFilter === srv
                      ? "bg-cyan-500/15 text-cyan-300 border border-cyan-800"
                      : "bg-[#0F172A] border border-slate-800 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {srv === "ALL" ? "All Services" : srv}
                </button>
              ))}
            </div>

            <div className="rounded-xl bg-[#0F172A] border border-slate-800 overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                      <th className="py-3 px-4">Service</th>
                      <th className="py-3 px-4">Finding Type</th>
                      <th className="py-3 px-4">Severity</th>
                      <th className="py-3 px-4">Resource ID</th>
                      <th className="py-3 px-4">Description &amp; Remediation</th>
                      <th className="py-3 px-4">Telemetry Class</th>
                      <th className="py-3 px-4">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {filteredFindings.length > 0 ? (
                      filteredFindings.map((f) => (
                        <tr key={f.id} className="hover:bg-slate-900/40 transition-colors">
                          <td className="py-3 px-4 font-semibold text-cyan-300">{f.service}</td>
                          <td className="py-3 px-4 font-mono text-slate-200 text-[11px]">{f.finding_type}</td>
                          <td className="py-3 px-4">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                f.severity === "Critical"
                                  ? "bg-red-950 text-red-400 border border-red-800/50"
                                  : f.severity === "High"
                                  ? "bg-orange-950 text-orange-400 border border-orange-800/50"
                                  : "bg-amber-950 text-amber-400 border border-amber-800/50"
                              }`}
                            >
                              {f.severity}
                            </span>
                          </td>
                          <td className="py-3 px-4 font-mono text-[11px] text-slate-400 max-w-[160px] truncate" title={f.resource_id}>
                            {f.resource_id || "Global"}
                          </td>
                          <td className="py-3 px-4 text-slate-300 max-w-sm">
                            <div className="line-clamp-2">{f.description}</div>
                            {f.remediation_guidance && (
                              <div className="text-[10px] text-emerald-400 mt-1">
                                Fix: {f.remediation_guidance}
                              </div>
                            )}
                          </td>
                          <td className="py-3 px-4">
                            {f.is_simulated ? (
                              <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-purple-950 text-purple-300 border border-purple-800">
                                SIMULATED
                              </span>
                            ) : (
                              <span className="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-emerald-950 text-emerald-300">
                                LIVE
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4 font-mono text-[11px] text-slate-500 whitespace-nowrap">
                            {formatLocalDateTime(f.created_at)}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={7} className="py-8 text-center text-slate-400 text-xs">
                          {loading ? "Loading cloud findings..." : "No AWS findings matching the selected filter."}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: Audited Resources Table */}
        {activeTab === "resources" && (
          <div className="rounded-xl bg-[#0F172A] border border-slate-800 overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                    <th className="py-3 px-4">Resource ID</th>
                    <th className="py-3 px-4">Name</th>
                    <th className="py-3 px-4">Type</th>
                    <th className="py-3 px-4">Region</th>
                    <th className="py-3 px-4">Compliance Status</th>
                    <th className="py-3 px-4">Last Scanned</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {resources.length > 0 ? (
                    resources.map((r) => (
                      <tr key={r.id} className="hover:bg-slate-900/40 transition-colors">
                        <td className="py-3 px-4 font-mono text-cyan-300 text-[11px]">{r.resource_id}</td>
                        <td className="py-3 px-4 font-medium text-slate-200">{r.resource_name}</td>
                        <td className="py-3 px-4 font-mono text-slate-400 text-[11px]">{r.resource_type}</td>
                        <td className="py-3 px-4 text-slate-400">{r.region}</td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                              r.compliance_status === "Compliant"
                                ? "bg-emerald-950 text-emerald-300 border border-emerald-800/50"
                                : "bg-red-950 text-red-300 border border-red-800/50"
                            }`}
                          >
                            {r.compliance_status}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-500 text-[11px]">
                          {formatLocalDateTime(r.last_scanned_at)}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-slate-400 text-xs">
                        No cloud resources recorded. Click &quot;Load Zero-Cost Fixtures&quot; to populate.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 3: Connected Accounts Table */}
        {activeTab === "accounts" && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {accounts.map((acc) => (
                <div key={acc.id} className="p-5 rounded-xl bg-[#0F172A] border border-slate-800 space-y-3 text-xs">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-bold text-slate-100 text-sm">{acc.account_name}</h3>
                      <div className="text-[11px] text-cyan-400 font-mono mt-0.5">Account ID: {acc.account_id}</div>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800">
                      {acc.status}
                    </span>
                  </div>

                  <div className="space-y-1.5 text-slate-400 text-[11px]">
                    <div>AssumeRole ARN: <span className="font-mono text-slate-200">{acc.role_arn}</span></div>
                    <div>Region: <span className="text-slate-300">{acc.region}</span></div>
                    <div>Connected: <span className="text-slate-300">{formatLocalDateTime(acc.created_at)}</span></div>
                  </div>

                  <div className="pt-3 border-t border-slate-800 flex justify-end">
                    <button
                      onClick={() => handleDisconnectAccount(acc.id)}
                      className="px-3 py-1.5 rounded-lg bg-red-950/60 border border-red-900 text-red-300 hover:bg-red-900/60 font-medium text-xs flex items-center gap-1.5 transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Disconnect</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Modal: Register AWS Account */}
        {registerModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
            <div className="w-full max-w-md rounded-xl border border-slate-800 bg-[#0B1120] p-6 shadow-2xl">
              <h2 className="text-base font-semibold text-slate-100 mb-1">Connect AWS Account via AssumeRole</h2>
              <p className="text-xs text-slate-400 mb-4">Provide the IAM Role ARN and External ID configured in your AWS account</p>
              <form onSubmit={handleRegisterAccount} className="space-y-4 text-xs">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">AWS Account ID (12 digits)</label>
                  <input
                    type="text"
                    required
                    pattern="[0-9]{12}"
                    value={accId}
                    onChange={(e) => setAccId(e.target.value)}
                    placeholder="123456789012"
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Account Friendly Name</label>
                  <input
                    type="text"
                    required
                    value={accName}
                    onChange={(e) => setAccName(e.target.value)}
                    placeholder="Production Core AWS"
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">IAM Role ARN</label>
                  <input
                    type="text"
                    required
                    value={roleArn}
                    onChange={(e) => setRoleArn(e.target.value)}
                    placeholder="arn:aws:iam::123456789012:role/SentinelSOCReadOnlyRole"
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Security External ID (for confused deputy prevention)</label>
                  <input
                    type="text"
                    required
                    value={extId}
                    onChange={(e) => setExtId(e.target.value)}
                    placeholder="e.g. sentinel-soc-org-secret"
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Primary Region</label>
                  <select
                    value={region}
                    onChange={(e) => setRegion(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="us-east-1">US East (N. Virginia) us-east-1</option>
                    <option value="us-west-2">US West (Oregon) us-west-2</option>
                    <option value="eu-west-1">Europe (Ireland) eu-west-1</option>
                    <option value="ap-southeast-1">Asia Pacific (Singapore) ap-southeast-1</option>
                  </select>
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setRegisterModalOpen(false)}
                    className="px-4 py-2 rounded-lg border border-slate-800 text-slate-400 hover:bg-slate-900"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-lg bg-cyan-500 text-slate-950 font-semibold hover:bg-cyan-400"
                  >
                    Connect Account
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal: IAM Policy Template */}
        {policyModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
            <div className="w-full max-w-2xl rounded-xl border border-slate-800 bg-[#0B1120] p-6 shadow-2xl space-y-4 text-xs">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Key className="w-4 h-4 text-cyan-400" />
                  <h2 className="text-base font-semibold text-slate-100">Least-Privilege Read-Only IAM Policy</h2>
                </div>
                <button
                  onClick={() => setPolicyModalOpen(false)}
                  className="text-slate-400 hover:text-slate-200 text-lg font-bold"
                >
                  &times;
                </button>
              </div>

              <p className="text-slate-400 leading-relaxed">
                Attach this policy to your Sentinel cross-account IAM role in the target AWS account. It grants strictly read-only audit capabilities across Security Hub, GuardDuty, S3 metadata, and VPC Flow Logs with zero write permissions.
              </p>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-semibold text-slate-300">Policy Document (JSON):</span>
                  <button
                    onClick={handleCopyPolicy}
                    className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 flex items-center gap-1 text-[11px]"
                  >
                    {copiedPolicy ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedPolicy ? "Copied!" : "Copy JSON"}</span>
                  </button>
                </div>
                <pre className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-cyan-300 max-h-72 overflow-y-auto">
                  {policyData ? JSON.stringify(policyData.policy_json, null, 2) : "Loading policy..."}
                </pre>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setPolicyModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
