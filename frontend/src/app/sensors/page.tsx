"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "../../components/layout/AppShell";
import { fetchApi } from "../../lib/api";
import { formatLocalTime } from "../../lib/date";
import {
  Cpu,
  Key,
  Copy,
  Check,
  RefreshCw,
  Terminal,
  AlertTriangle,
  ShieldAlert,
  HelpCircle,
} from "lucide-react";
import { ExplainErrorModal } from "../../components/ExplainErrorModal";

export default function SensorsPage() {
  const [sensors, setSensors] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [tokenModalOpen, setTokenModalOpen] = useState(false);
  const [sensorName, setSensorName] = useState("");
  const [sensorOs, setSensorOs] = useState("Linux");
  const [generatedToken, setGeneratedToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [explainOpen, setExplainOpen] = useState(false);
  const [selectedError, setSelectedError] = useState("Sensor status error");

  const loadSensors = async () => {
    try {
      setRefreshing(true);
      const data = await fetchApi("/sensors");
      setSensors(data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadSensors();
    const interval = setInterval(loadSensors, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleGenerateToken = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetchApi("/sensors/generate-token", {
        method: "POST",
        body: JSON.stringify({ name: sensorName, os_type: sensorOs }),
      });
      setGeneratedToken(res.enrollment_token);
      loadSensors();
    } catch (err: any) {
      alert(`Error generating token: ${err.message}`);
    }
  };

  const handleRevoke = async (sensorId: string, sensorName: string) => {
    if (!confirm(`Are you sure you want to revoke credentials for sensor '${sensorName}'? It will no longer be permitted to submit telemetry.`)) {
      return;
    }
    try {
      await fetchApi(`/sensors/${sensorId}/revoke`, { method: "POST" });
      loadSensors();
    } catch (err: any) {
      alert(`Failed to revoke sensor: ${err.message}`);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
              <Cpu className="w-5 h-5 text-cyan-400" />
              Sensor Management &amp; Enrollment
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Secure single-use token enrollment, heartbeat health, and credential lifecycle
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadSensors}
              disabled={refreshing}
              title="Refresh Sensor Fleet"
              className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-cyan-400 disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin text-cyan-400" : ""}`} />
            </button>
            <button
              onClick={() => {
                setGeneratedToken(null);
                setSensorName("");
                setTokenModalOpen(true);
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-semibold"
            >
              <Key className="w-4 h-4" />
              <span>Generate Enrollment Token</span>
            </button>
          </div>
        </div>

        {/* Sensor Table */}
        <div className="rounded-xl bg-[#0F172A] border border-slate-800 overflow-hidden shadow-sm">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
                <th className="py-3 px-4">Sensor Name</th>
                <th className="py-3 px-4">Target OS</th>
                <th className="py-3 px-4">Version</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Capabilities</th>
                <th className="py-3 px-4">Last Heartbeat</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {sensors.length > 0 ? (
                sensors.map((sensor) => {
                  let caps: any = {};
                  try {
                    caps = JSON.parse(sensor.capabilities || "{}");
                  } catch {}

                  return (
                    <tr key={sensor.id} className="hover:bg-slate-900/40 transition-colors">
                      <td className="py-3 px-4 font-semibold text-slate-200">
                        {sensor.name}
                        {sensor.error_message && (
                          <div className="text-[11px] text-red-400 flex items-center gap-1 mt-0.5 font-normal">
                            <AlertTriangle className="w-3 h-3" />
                            <span>{sensor.error_message}</span>
                            <button
                              onClick={() => {
                                setSelectedError(sensor.error_message);
                                setExplainOpen(true);
                              }}
                              className="underline text-cyan-400 text-[10px] ml-1"
                            >
                              Explain Error
                            </button>
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-300">{sensor.os_type}</td>
                      <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">{sensor.version}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            sensor.status === "Online"
                              ? "bg-emerald-950 text-emerald-400 border border-emerald-800/50"
                              : sensor.status === "Pending enrollment"
                              ? "bg-cyan-950 text-cyan-400 border border-cyan-800/50"
                              : sensor.status === "Revoked"
                              ? "bg-red-950 text-red-400 border border-red-800/50"
                              : "bg-slate-800 text-slate-400"
                          }`}
                        >
                          {sensor.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-[11px] text-slate-400">
                        <div className="flex flex-wrap gap-1">
                          {Object.keys(caps).map((k) => (
                            <span key={k} className="px-1.5 py-0.2 rounded bg-slate-900 border border-slate-800 text-slate-300 text-[10px]">
                              {k}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-400">
                        {formatLocalTime(sensor.last_heartbeat)}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {sensor.status !== "Revoked" && (
                          <button
                            onClick={() => handleRevoke(sensor.id, sensor.name)}
                            className="px-2 py-1 rounded bg-slate-900 border border-slate-800 hover:border-red-800 text-red-400 hover:bg-red-950/40 text-[11px] transition-colors"
                          >
                            Revoke
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 text-xs">
                    {loading ? "Loading sensors..." : "No sensors enrolled yet."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Installation Instructions Box */}
        <div className="p-5 rounded-xl bg-[#0F172A] border border-slate-800 space-y-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
            <Terminal className="w-4 h-4 text-cyan-400" />
            <span>Endpoint Sensor Quick Deployment Guide (Windows &amp; Linux)</span>
          </div>
          <p className="text-xs text-slate-400">
            Sentinel SOC includes an actual Python-based cross-platform sensor. The sensor initiates outbound HTTPS connections to Sentinel SOC—no open inbound ports required on routers.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pt-1">
            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-2">
              <span className="font-semibold text-cyan-300">Linux / Ubuntu / Debian</span>
              <pre className="p-2.5 rounded bg-slate-900 text-slate-200 overflow-x-auto text-[11px] font-mono leading-relaxed">
{`# 1. Enter sensor directory
cd sensor

# 2. Install lightweight dependencies
pip install -r requirements.txt

# 3. Enroll & start sensor daemon
python install.py --enroll <YOUR_TOKEN> --server http://localhost:8000
python install.py --setup-service`}
              </pre>
            </div>

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-2">
              <span className="font-semibold text-cyan-300">Windows 10 / 11 / Server</span>
              <pre className="p-2.5 rounded bg-slate-900 text-slate-200 overflow-x-auto text-[11px] font-mono leading-relaxed">
{`# 1. Open PowerShell
cd sensor

# 2. Install requirements
pip install -r requirements.txt

# 3. Enroll & start
python install.py --enroll <YOUR_TOKEN> --server http://localhost:8000
python install.py --run`}
              </pre>
            </div>
          </div>
        </div>

        {/* Modal: Generate Token */}
        {tokenModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
            <div className="w-full max-w-lg rounded-xl border border-slate-800 bg-[#0B1120] p-6 shadow-2xl">
              <h2 className="text-base font-semibold text-slate-100 mb-1">Generate Sensor Enrollment Token</h2>
              <p className="text-xs text-slate-400 mb-4">
                Tokens are tenant-bound, single-use, and expire automatically after 48 hours.
              </p>

              {!generatedToken ? (
                <form onSubmit={handleGenerateToken} className="space-y-4 text-xs">
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Sensor Identifier Name</label>
                    <input
                      type="text"
                      required
                      value={sensorName}
                      onChange={(e) => setSensorName(e.target.value)}
                      placeholder="e.g. prod-app-server01"
                      className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Target Operating System</label>
                    <select
                      value={sensorOs}
                      onChange={(e) => setSensorOs(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                    >
                      <option value="Linux">Linux (systemd)</option>
                      <option value="Windows">Windows (Service / Task)</option>
                    </select>
                  </div>
                  <div className="flex justify-end gap-3 pt-2">
                    <button
                      type="button"
                      onClick={() => setTokenModalOpen(false)}
                      className="px-4 py-2 rounded-lg border border-slate-800 text-slate-400 hover:bg-slate-900"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-2 rounded-lg bg-cyan-500 text-slate-950 font-semibold hover:bg-cyan-400"
                    >
                      Generate Secure Token
                    </button>
                  </div>
                </form>
              ) : (
                <div className="space-y-4 text-xs">
                  <div className="p-3 rounded-lg bg-cyan-950/40 border border-cyan-800/50 space-y-2">
                    <div className="font-semibold text-cyan-300">Single-Use Enrollment Token Generated:</div>
                    <div className="flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-800 font-mono text-[11px] text-slate-200">
                      <span className="truncate mr-2">{generatedToken}</span>
                      <button
                        onClick={() => copyToClipboard(generatedToken)}
                        className="text-cyan-400 hover:text-cyan-300 p-1 flex-shrink-0"
                      >
                        {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block font-medium text-slate-300 mb-1">Run on target host to install:</label>
                    <div className="p-2.5 rounded bg-slate-900 border border-slate-800 font-mono text-[11px] text-cyan-300 break-all select-all">
                      python install.py --enroll {generatedToken} --server {window.location.origin.replace(":3000", ":8000")}
                    </div>
                  </div>

                  <div className="flex justify-end pt-2">
                    <button
                      onClick={() => setTokenModalOpen(false)}
                      className="px-4 py-2 rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700 font-semibold"
                    >
                      Done
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        <ExplainErrorModal
          isOpen={explainOpen}
          onClose={() => setExplainOpen(false)}
          errorMessage={selectedError}
          moduleName="Sensor Management"
          errorCode="ERR_SENSOR_DIAGNOSTIC"
        />
      </div>
    </AppShell>
  );
}
