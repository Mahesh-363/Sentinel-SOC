"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "../../components/layout/AppShell";
import { fetchApi } from "../../lib/api";
import { formatLocalDateTime } from "../../lib/date";
import { Server, Plus, Search, Shield, RefreshCw, Laptop, Database, Cpu } from "lucide-react";

export default function AssetsPage() {
  const [assets, setAssets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [newHostname, setNewHostname] = useState("");
  const [newOsFamily, setNewOsFamily] = useState("Linux");
  const [newAssetType, setNewAssetType] = useState("Server");
  const [newPrivateIp, setNewPrivateIp] = useState("");

  const loadAssets = async () => {
    try {
      const data = await fetchApi("/assets");
      setAssets(data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAssets();
  }, []);

  const handleCreateAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await fetchApi("/assets", {
        method: "POST",
        body: JSON.stringify({
          hostname: newHostname,
          os_family: newOsFamily,
          asset_type: newAssetType,
          private_ips: newPrivateIp ? [newPrivateIp] : [],
        }),
      });
      setModalOpen(false);
      setNewHostname("");
      setNewPrivateIp("");
      loadAssets();
    } catch (err: any) {
      alert(`Failed to add asset: ${err.message}`);
    }
  };

  const filteredAssets = assets.filter(
    (a) =>
      a.hostname.toLowerCase().includes(search.toLowerCase()) ||
      a.os_family.toLowerCase().includes(search.toLowerCase()) ||
      a.asset_type.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
              <Server className="w-5 h-5 text-cyan-400" />
              Asset Inventory &amp; Endpoint Management
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Registered endpoints, database servers, routers, and authorized virtual machines
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadAssets}
              className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-cyan-400"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={() => setModalOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-semibold"
            >
              <Plus className="w-4 h-4" />
              <span>Register Asset</span>
            </button>
          </div>
        </div>

        {/* Filter bar */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search assets by hostname, OS, or type..."
              className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-[#0F172A] border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>
          <span className="text-xs text-slate-400 font-mono">{filteredAssets.length} Assets Registered</span>
        </div>

        {/* Assets Table */}
        <div className="rounded-xl bg-[#0F172A] border border-slate-800 overflow-hidden shadow-sm">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                <th className="py-3 px-4">Hostname</th>
                <th className="py-3 px-4">OS &amp; Version</th>
                <th className="py-3 px-4">Asset Type</th>
                <th className="py-3 px-4">IP Addresses</th>
                <th className="py-3 px-4">Health Status</th>
                <th className="py-3 px-4">Risk Level</th>
                <th className="py-3 px-4">Last Telemetry</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredAssets.length > 0 ? (
                filteredAssets.map((asset) => {
                  let ips: string[] = [];
                  try {
                    ips = JSON.parse(asset.private_ips || "[]");
                  } catch {
                    ips = [asset.private_ips];
                  }

                  return (
                    <tr key={asset.id} className="hover:bg-slate-900/40 transition-colors">
                      <td className="py-3 px-4 font-semibold text-slate-200 flex items-center gap-2">
                        {asset.asset_type === "Server" ? (
                          <Database className="w-4 h-4 text-cyan-400" />
                        ) : (
                          <Laptop className="w-4 h-4 text-slate-400" />
                        )}
                        <span>{asset.hostname}</span>
                      </td>
                      <td className="py-3 px-4 text-slate-300">
                        {asset.os_family} {asset.os_version && <span className="text-slate-500">({asset.os_version})</span>}
                      </td>
                      <td className="py-3 px-4 text-slate-300 font-medium">{asset.asset_type}</td>
                      <td className="py-3 px-4 font-mono text-[11px] text-cyan-300">
                        {ips.join(", ") || asset.public_ip || "DHCP / Unassigned"}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            asset.health_status === "online"
                              ? "bg-emerald-950/80 text-emerald-400 border border-emerald-800/50"
                              : "bg-slate-800 text-slate-400"
                          }`}
                        >
                          {asset.health_status}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                              asset.risk_level === "Critical"
                                ? "bg-red-950 text-red-400 border border-red-800/40"
                                : asset.risk_level === "High"
                                ? "bg-orange-950 text-orange-400 border border-orange-800/40"
                                : asset.risk_level === "Medium"
                                ? "bg-amber-950 text-amber-400 border border-amber-800/40"
                                : "bg-emerald-950/60 text-emerald-400 border border-emerald-800/40"
                            }`}
                          >
                            {asset.risk_level} ({asset.risk_score || 15}/100)
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                        {formatLocalDateTime(asset.last_seen)}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 text-xs">
                    {loading ? "Loading assets..." : "No matching assets found."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Modal: Register Asset */}
        {modalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
            <div className="w-full max-w-md rounded-xl border border-slate-800 bg-[#0B1120] p-6 shadow-2xl">
              <h2 className="text-base font-semibold text-slate-100 mb-1">Register New Monitored Asset</h2>
              <p className="text-xs text-slate-400 mb-4">Add a known endpoint, server, or router to this tenant</p>
              <form onSubmit={handleCreateAsset} className="space-y-4 text-xs">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Hostname / FQDN</label>
                  <input
                    type="text"
                    required
                    value={newHostname}
                    onChange={(e) => setNewHostname(e.target.value)}
                    placeholder="db-primary-node01"
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">OS Family</label>
                    <select
                      value={newOsFamily}
                      onChange={(e) => setNewOsFamily(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                    >
                      <option value="Linux">Linux</option>
                      <option value="Windows">Windows</option>
                      <option value="MacOS">MacOS</option>
                      <option value="NetworkOS">NetworkOS</option>
                      <option value="AWS">AWS EC2</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Asset Type</label>
                    <select
                      value={newAssetType}
                      onChange={(e) => setNewAssetType(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                    >
                      <option value="Server">Server</option>
                      <option value="Endpoint">Workstation</option>
                      <option value="Router">Router / Gateway</option>
                      <option value="Cloud Instance">Cloud Instance</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Private IP Address (Optional)</label>
                  <input
                    type="text"
                    value={newPrivateIp}
                    onChange={(e) => setNewPrivateIp(e.target.value)}
                    placeholder="192.168.1.100"
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setModalOpen(false)}
                    className="px-4 py-2 rounded-lg border border-slate-800 text-slate-400 hover:bg-slate-900"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-lg bg-cyan-500 text-slate-950 font-semibold hover:bg-cyan-400"
                  >
                    Save Asset
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
