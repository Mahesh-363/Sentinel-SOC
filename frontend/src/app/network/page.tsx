"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "../../components/layout/AppShell";
import { fetchApi } from "../../lib/api";
import { formatLocalDateTime } from "../../lib/date";
import {
  Network,
  Plus,
  RefreshCw,
  ShieldCheck,
  ShieldAlert,
  Info,
  Server,
  Router,
  Laptop,
  Radio,
  CheckCircle2,
  AlertTriangle,
  GitBranch,
  Layers,
  Activity,
  Cpu,
  Loader2,
  ArrowRight
} from "lucide-react";

export default function NetworkPage() {
  const [subnets, setSubnets] = useState<any[]>([]);
  const [devices, setDevices] = useState<any[]>([]);
  const [coverage, setCoverage] = useState<any>(null);
  const [topology, setTopology] = useState<any>(null);
  const [integrations, setIntegrations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Modals
  const [subnetModalOpen, setSubnetModalOpen] = useState(false);
  const [integrationModalOpen, setIntegrationModalOpen] = useState(false);

  // Subnet form
  const [name, setName] = useState("");
  const [cidr, setCidr] = useState("");
  const [netType, setNetType] = useState("Corporate LAN");

  // Gateway Integration form
  const [integType, setIntegType] = useState("PFSENSE");
  const [integName, setIntegName] = useState("");
  const [integHost, setIntegHost] = useState("192.168.1.1");
  const [integPort, setIntegPort] = useState(443);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  // Active view tab: Inventory vs Topology vs Integrations
  const [activeTab, setActiveTab] = useState<"inventory" | "topology" | "integrations">("inventory");

  const loadData = async () => {
    try {
      const [subs, devs, cov, topo, integs] = await Promise.all([
        fetchApi("/network/subnets"),
        fetchApi("/network/devices"),
        fetchApi("/network/coverage"),
        fetchApi("/network/topology"),
        fetchApi("/network/integrations")
      ]);
      setSubnets(subs || []);
      setDevices(devs || []);
      setCoverage(cov || null);
      setTopology(topo || null);
      setIntegrations(integs || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateSubnet = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await fetchApi("/network/subnets", {
        method: "POST",
        body: JSON.stringify({ name, cidr, network_type: netType }),
      });
      setSubnetModalOpen(false);
      setName("");
      setCidr("");
      loadData();
    } catch (err: any) {
      alert(`Failed to add subnet: ${err.message}`);
    }
  };

  const handleCreateIntegration = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await fetchApi("/network/integrations", {
        method: "POST",
        body: JSON.stringify({
          integration_type: integType,
          name: integName || `${integType} Edge`,
          target_host: integHost,
          port: Number(integPort),
          is_enabled: true
        }),
      });
      setIntegrationModalOpen(false);
      setIntegName("");
      loadData();
    } catch (err: any) {
      alert(`Failed to add gateway integration: ${err.message}`);
    }
  };

  const handleSyncIntegration = async (id: string) => {
    setSyncingId(id);
    setSyncMessage(null);
    try {
      const res = await fetchApi(`/network/integrations/${id}/sync`, { method: "POST" });
      setSyncMessage(res.message || "DHCP and ARP tables synchronized successfully.");
      loadData();
    } catch (err: any) {
      alert(`Sync failed: ${err.message}`);
    } finally {
      setSyncingId(null);
    }
  };

  const handleToggleAuth = async (deviceId: string, currentAuth: boolean) => {
    try {
      await fetchApi(`/network/devices/${deviceId}/authorize?authorize=${!currentAuth}`, {
        method: "PATCH",
      });
      loadData();
    } catch (err: any) {
      alert(`Error toggling device authorization: ${err.message}`);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
              <Network className="w-5 h-5 text-cyan-400" />
              Network Intelligence &amp; Topology
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Subnet coverage, endpoint sensor visibility, router integrations (pfSense/OPNsense/UniFi), and observed vs. inferred topology.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadData}
              className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-cyan-400"
              title="Refresh network tables"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={() => setIntegrationModalOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700"
            >
              <Router className="w-3.5 h-3.5 text-cyan-400" />
              <span>Connect Gateway</span>
            </button>
            <button
              onClick={() => setSubnetModalOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-semibold"
            >
              <Plus className="w-4 h-4" />
              <span>Define Authorized Subnet</span>
            </button>
          </div>
        </div>

        {/* Network & Sensor Visibility Coverage Metrics */}
        {coverage && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 flex items-center gap-3.5">
              <div className="p-2.5 rounded-lg bg-cyan-500/10 text-cyan-400">
                <Network className="w-5 h-5" />
              </div>
              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Subnet Coverage</div>
                <div className="text-lg font-bold font-mono text-slate-100">
                  {coverage.subnet_coverage_percent}%
                </div>
                <div className="text-[10px] text-slate-400">
                  {coverage.monitored_subnets} of {coverage.total_subnets} subnets monitored
                </div>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 flex items-center gap-3.5">
              <div className="p-2.5 rounded-lg bg-purple-500/10 text-purple-400">
                <Radio className="w-5 h-5" />
              </div>
              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Sensor Coverage</div>
                <div className="text-lg font-bold font-mono text-slate-100">
                  {coverage.device_sensor_coverage_percent}%
                </div>
                <div className="text-[10px] text-slate-400">
                  {coverage.monitored_devices_count} active agents / {coverage.total_devices} devices
                </div>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 flex items-center gap-3.5">
              <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-400">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Authorized Devices</div>
                <div className="text-lg font-bold font-mono text-emerald-400">
                  {coverage.authorized_devices_count}
                </div>
                <div className="text-[10px] text-slate-400">
                  Compliant network inventory
                </div>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 flex items-center gap-3.5">
              <div className="p-2.5 rounded-lg bg-red-500/10 text-red-400">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Rogue Devices</div>
                <div className="text-lg font-bold font-mono text-red-400">
                  {coverage.unauthorized_devices_count}
                </div>
                <div className="text-[10px] text-slate-400">
                  Unrecognized MAC/IP on LAN
                </div>
              </div>
            </div>
          </div>
        )}

        {/* View Selection Tabs */}
        <div className="flex border-b border-slate-800 text-xs font-semibold gap-6">
          <button
            onClick={() => setActiveTab("inventory")}
            className={`pb-3 border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === "inventory"
                ? "border-cyan-400 text-cyan-300"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Server className="w-4 h-4" />
            <span>Device Inventory &amp; Subnets</span>
          </button>
          <button
            onClick={() => setActiveTab("topology")}
            className={`pb-3 border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === "topology"
                ? "border-cyan-400 text-cyan-300"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <GitBranch className="w-4 h-4" />
            <span>Interactive Topology Graph</span>
          </button>
          <button
            onClick={() => setActiveTab("integrations")}
            className={`pb-3 border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === "integrations"
                ? "border-cyan-400 text-cyan-300"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Router className="w-4 h-4" />
            <span>Router &amp; Gateway Adapters ({integrations.length})</span>
          </button>
        </div>

        {/* TAB 1: Inventory View */}
        {activeTab === "inventory" && (
          <div className="space-y-6">
            {/* Subnets List */}
            <div>
              <h2 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
                <Layers className="w-4 h-4 text-cyan-400" />
                Authorized CIDR Subnets ({subnets.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {subnets.map((sub) => (
                  <div key={sub.id} className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 shadow-sm space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-200">{sub.name}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/40">
                        {sub.network_type}
                      </span>
                    </div>
                    <div className="text-lg font-mono text-cyan-300 font-bold">{sub.cidr}</div>
                    <div className="text-[11px] text-slate-400 flex items-center gap-1.5 pt-1 border-t border-slate-800/60">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Authorized Segment &bull; {sub.observation_source}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Discovered Devices Table */}
            <div className="rounded-xl bg-[#0F172A] border border-slate-800 overflow-hidden shadow-sm">
              <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-slate-200">Discovered Network Devices &amp; Neighbors</h2>
                  <p className="text-[11px] text-slate-400">Observed via ARP scans, DHCP lease inspection, and socket telemetry.</p>
                </div>
                <span className="text-xs font-mono text-slate-400">{devices.length} Devices Discovered</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                      <th className="py-3 px-4">Device IP</th>
                      <th className="py-3 px-4">MAC Address</th>
                      <th className="py-3 px-4">Hostname / Vendor</th>
                      <th className="py-3 px-4">Type</th>
                      <th className="py-3 px-4">Discovery Method</th>
                      <th className="py-3 px-4">Authorization</th>
                      <th className="py-3 px-4">Last Observed</th>
                      <th className="py-3 px-4 text-right">Policy Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {devices.length > 0 ? (
                      devices.map((dev) => (
                        <tr key={dev.id} className="hover:bg-slate-900/40 transition-colors">
                          <td className="py-3 px-4 font-mono font-medium text-cyan-300">{dev.ip_address}</td>
                          <td className="py-3 px-4 font-mono text-[11px] text-slate-400">{dev.mac_address || "Unknown"}</td>
                          <td className="py-3 px-4 text-slate-300">
                            {dev.hostname || dev.vendor || "Generic LAN Host"}
                          </td>
                          <td className="py-3 px-4 text-slate-400">{dev.device_type}</td>
                          <td className="py-3 px-4 text-slate-400 font-mono text-[10px]">{dev.discovery_method || "ARP Table"}</td>
                          <td className="py-3 px-4">
                            {dev.is_authorized ? (
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800/50">
                                Authorized
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-red-950 text-red-400 border border-red-800/50">
                                Rogue (Alert Triggered)
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                            {formatLocalDateTime(dev.last_seen)}
                          </td>
                          <td className="py-3 px-4 text-right">
                            <button
                              onClick={() => handleToggleAuth(dev.id, dev.is_authorized)}
                              className={`px-2.5 py-1 rounded text-[11px] font-medium border transition-colors ${
                                dev.is_authorized
                                  ? "bg-slate-900 border-slate-800 text-slate-400 hover:text-red-400 hover:border-red-900"
                                  : "bg-emerald-950/80 border-emerald-800 text-emerald-300 hover:bg-emerald-900"
                              }`}
                            >
                              {dev.is_authorized ? "Flag Rogue" : "Authorize"}
                            </button>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={8} className="py-8 text-center text-slate-400 text-xs">
                          {loading ? "Discovering devices..." : "No devices recorded in network table."}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: Topology Graph View */}
        {activeTab === "topology" && (
          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-[#0F172A] border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs">
              <div className="space-y-1">
                <span className="font-semibold text-slate-200">Topological Observation Architecture:</span>
                <p className="text-slate-400">
                  Sentinel SOC strictly separates <strong className="text-cyan-400">OBSERVED</strong> direct connections (verified via host agent socket inspection or active ARP probes) from <strong className="text-amber-400">INFERRED</strong> topology (gateway routing assumptions).
                </p>
              </div>

              {/* Legend */}
              <div className="flex items-center gap-4 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <div className="w-4 h-0.5 bg-cyan-400" />
                  <span className="text-slate-300 font-semibold">OBSERVED ({topology?.observed_links || 0})</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-4 h-0.5 border-t border-dashed border-amber-400" />
                  <span className="text-slate-300 font-semibold">INFERRED ({topology?.inferred_links || 0})</span>
                </div>
              </div>
            </div>

            {/* Topology Nodes Grid Canvas */}
            <div className="p-6 rounded-xl bg-[#0B1120] border border-slate-800 min-h-[400px]">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Gateway Column */}
                <div className="space-y-4">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-800 pb-2">
                    Gateway &amp; Edge
                  </h3>
                  {topology?.nodes?.filter((n: any) => n.node_type === "GATEWAY").map((n: any) => (
                    <div key={n.id} className="p-4 rounded-xl bg-slate-900 border-2 border-cyan-500/60 shadow-lg text-xs space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-cyan-300 flex items-center gap-1.5">
                          <Router className="w-4 h-4 text-cyan-400" />
                          {n.label}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                          {n.status}
                        </span>
                      </div>
                      <div className="font-mono text-slate-400">{n.ip_address}</div>
                    </div>
                  ))}
                </div>

                {/* Subnets Column */}
                <div className="space-y-4">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-800 pb-2">
                    Routed Subnet Segments
                  </h3>
                  {topology?.nodes?.filter((n: any) => n.node_type === "SUBNET").map((n: any) => (
                    <div key={n.id} className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 text-xs space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-200 flex items-center gap-1.5">
                          <Layers className="w-4 h-4 text-purple-400" />
                          {n.label}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                          Segment
                        </span>
                      </div>
                      <div className="font-mono text-cyan-400">{n.ip_address}</div>
                      <div className="text-[10px] text-amber-400 flex items-center gap-1 pt-1 border-t border-slate-800">
                        <ArrowRight className="w-3 h-3" /> Inferred link from gateway route table
                      </div>
                    </div>
                  ))}
                </div>

                {/* Endpoints & Devices Column */}
                <div className="space-y-4">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-800 pb-2">
                    Enrolled Endpoints &amp; Neighbors
                  </h3>
                  <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                    {topology?.nodes?.filter((n: any) => n.node_type === "ASSET" || n.node_type === "DEVICE").map((n: any) => (
                      <div
                        key={n.id}
                        className={`p-3 rounded-lg bg-slate-900/80 border text-xs space-y-1 ${
                          n.is_monitored
                            ? "border-cyan-800/80 hover:border-cyan-500"
                            : "border-slate-800 hover:border-slate-700"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-slate-200 flex items-center gap-1.5">
                            {n.node_type === "ASSET" ? <Laptop className="w-3.5 h-3.5 text-cyan-400" /> : <Server className="w-3.5 h-3.5 text-slate-500" />}
                            {n.label}
                          </span>
                          <span
                            className={`text-[9px] px-1.5 py-0.5 rounded font-semibold ${
                              n.is_monitored
                                ? "bg-cyan-950 text-cyan-300 border border-cyan-800"
                                : "bg-slate-800 text-slate-400"
                            }`}
                          >
                            {n.is_monitored ? "AGENT OBSERVED" : "INFERRED"}
                          </span>
                        </div>
                        <div className="font-mono text-[11px] text-slate-400 flex justify-between">
                          <span>{n.ip_address}</span>
                          <span>{n.mac_address || "MAC Unknown"}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: Integrations View */}
        {activeTab === "integrations" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                  <Router className="w-4 h-4 text-cyan-400" />
                  Router &amp; Gateway Integration Adapters
                </h2>
                <p className="text-xs text-slate-400">
                  Connect official APIs for pfSense, OPNsense, UniFi Dream Machine, or OpenWrt to ingest live ARP/DHCP lease tables.
                </p>
              </div>
              <button
                onClick={() => setIntegrationModalOpen(true)}
                className="px-3 py-1.5 rounded-lg bg-cyan-500 text-slate-950 text-xs font-semibold hover:bg-cyan-400 flex items-center gap-1.5"
              >
                <Plus className="w-4 h-4" />
                <span>Add Router Connection</span>
              </button>
            </div>

            {syncMessage && (
              <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-900/50 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                <span>{syncMessage}</span>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {integrations.map((integ) => (
                <div key={integ.id} className="p-5 rounded-xl bg-[#0F172A] border border-slate-800 space-y-4 text-xs">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-bold text-slate-100 text-sm">{integ.name}</h3>
                      <div className="text-[11px] text-cyan-400 font-mono mt-0.5">{integ.integration_type}</div>
                    </div>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-mono ${
                        integ.status === "CONNECTED"
                          ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                          : "bg-slate-900 text-slate-400 border border-slate-800"
                      }`}
                    >
                      {integ.status}
                    </span>
                  </div>

                  <div className="space-y-1.5 text-slate-400 text-[11px]">
                    <div>Target Host: <span className="font-mono text-slate-200">{integ.target_host}:{integ.port}</span></div>
                    <div>Last Synchronized: <span className="text-slate-300">{formatLocalDateTime(integ.last_sync_at)}</span></div>
                  </div>

                  <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                    <span className="text-[10px] text-slate-500">Zero-cost simulated fallback active</span>
                    <button
                      onClick={() => handleSyncIntegration(integ.id)}
                      disabled={syncingId === integ.id}
                      className="px-3 py-1.5 rounded-lg bg-cyan-950 border border-cyan-800 hover:bg-cyan-900/60 text-cyan-300 font-semibold text-xs flex items-center gap-1.5 transition-colors disabled:opacity-50"
                    >
                      {syncingId === integ.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                      <span>Sync ARP / DHCP</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Modal: Define Subnet */}
        {subnetModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
            <div className="w-full max-w-md rounded-xl border border-slate-800 bg-[#0B1120] p-6 shadow-2xl">
              <h2 className="text-base font-semibold text-slate-100 mb-1">Define Authorized Subnet</h2>
              <p className="text-xs text-slate-400 mb-4">Register an authorized IP CIDR block for your network</p>
              <form onSubmit={handleCreateSubnet} className="space-y-4 text-xs">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Subnet Name</label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="HQ Workstation LAN"
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Network CIDR Block</label>
                  <input
                    type="text"
                    required
                    value={cidr}
                    onChange={(e) => setCidr(e.target.value)}
                    placeholder="192.168.1.0/24 or 10.0.0.0/16"
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Network Type</label>
                  <select
                    value={netType}
                    onChange={(e) => setNetType(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="Corporate LAN">Corporate LAN</option>
                    <option value="Home Office">Home Office</option>
                    <option value="Cloud VPC">Cloud VPC</option>
                    <option value="DMZ">DMZ</option>
                  </select>
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setSubnetModalOpen(false)}
                    className="px-4 py-2 rounded-lg border border-slate-800 text-slate-400 hover:bg-slate-900"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-lg bg-cyan-500 text-slate-950 font-semibold hover:bg-cyan-400"
                  >
                    Save Subnet
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal: Connect Gateway Integration */}
        {integrationModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
            <div className="w-full max-w-md rounded-xl border border-slate-800 bg-[#0B1120] p-6 shadow-2xl">
              <h2 className="text-base font-semibold text-slate-100 mb-1">Connect Gateway / Router</h2>
              <p className="text-xs text-slate-400 mb-4">Ingest DHCP lease tables and neighbor ARP mappings</p>
              <form onSubmit={handleCreateIntegration} className="space-y-4 text-xs">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Appliance Type</label>
                  <select
                    value={integType}
                    onChange={(e) => setIntegType(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="PFSENSE">pfSense (XML-RPC / API)</option>
                    <option value="OPNSENSE">OPNsense (Core REST API)</option>
                    <option value="UNIFI">Ubiquiti UniFi (Network Controller API)</option>
                    <option value="OPENWRT">OpenWrt (ubus RPC)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Display Name</label>
                  <input
                    type="text"
                    required
                    value={integName}
                    onChange={(e) => setIntegName(e.target.value)}
                    placeholder="Core Firewall 01"
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Target Host / IP</label>
                    <input
                      type="text"
                      required
                      value={integHost}
                      onChange={(e) => setIntegHost(e.target.value)}
                      placeholder="192.168.1.1"
                      className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Port</label>
                    <input
                      type="number"
                      required
                      value={integPort}
                      onChange={(e) => setIntegPort(Number(e.target.value))}
                      className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                    />
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-[11px] text-slate-400">
                  Sentinel SOC uses safe read-only queries. If credentials are omitted, offline zero-cost fixture simulation is used automatically.
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setIntegrationModalOpen(false)}
                    className="px-4 py-2 rounded-lg border border-slate-800 text-slate-400 hover:bg-slate-900"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-lg bg-cyan-500 text-slate-950 font-semibold hover:bg-cyan-400"
                  >
                    Save Connection
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
