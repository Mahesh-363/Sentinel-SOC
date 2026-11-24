"use client";

import React, { useState } from "react";
import { AppShell } from "../../components/layout/AppShell";
import { fetchApi } from "../../lib/api";
import {
  Flame,
  ShieldAlert,
  Play,
  RotateCcw,
  AlertTriangle,
  CheckCircle,
  Loader2,
  Terminal,
} from "lucide-react";

export default function SimulationPage() {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any | null>(null);

  const handleRunSimulation = async (simType: string, intensity: number = 6) => {
    setRunning(true);
    setResult(null);
    try {
      const res = await fetchApi("/simulation/run", {
        method: "POST",
        body: JSON.stringify({
          simulation_type: simType,
          intensity,
        }),
      });
      setResult(res);
    } catch (e: any) {
      alert(`Simulation failed: ${e.message}`);
    } finally {
      setRunning(false);
    }
  };

  const handleResetLab = async () => {
    if (!confirm("Are you sure you want to reset the simulation lab? This will safely purge only simulated events and alerts without touching real telemetry.")) {
      return;
    }
    try {
      const res = await fetchApi("/simulation/reset", { method: "POST" });
      alert(`Lab reset complete: ${res.purged_events} simulated events and ${res.purged_alerts} simulated alerts purged.`);
      setResult(null);
    } catch (e: any) {
      alert(`Reset failed: ${e.message}`);
    }
  };

  const SIMULATION_SCENARIOS = [
    {
      id: "brute_force_login",
      title: "Repeated Failed SSH Logins (Brute Force)",
      description: "Generates 6 rapid failed password attempts against SSH port 22 from lab source IP 198.51.100.24.",
      targetRule: "AUTH_FAILED_BURST",
      expectedSeverity: "High",
    },
    {
      id: "port_scan",
      title: "Sequential TCP Port Scan Probe",
      description: "Probes 8 common ports (21, 22, 23, 80, 443, 445, 3389, 8080) on local target within 60 seconds.",
      targetRule: "PORT_SCAN_ACTIVITY",
      expectedSeverity: "Medium",
    },
    {
      id: "malicious_c2_outbound",
      title: "Outbound C2 Session to Threat Indicator",
      description: "Simulates an outbound TCP beacon to verified threat indicator IP 185.220.101.5 on reverse shell port 4444.",
      targetRule: "MALICIOUS_IP_MATCH & UNUSUAL_OUTBOUND_CONN",
      expectedSeverity: "Critical",
    },
    {
      id: "new_lan_device",
      title: "Unauthorized Rogue Device on Authorized LAN",
      description: "Simulates an unknown MAC address appearing and broadcasting on the authorized 192.168.1.0/24 subnet.",
      targetRule: "NEW_UNAUTHORIZED_LAN_DEVICE",
      expectedSeverity: "Medium",
    },
    {
      id: "aws_iam_escalation",
      title: "Cloud Privilege Escalation: AdministratorAccess Attachment",
      description: "Simulates high-risk IAM policy attachment of AdministratorAccess to a sandbox role.",
      targetRule: "AWS_RISKY_IAM_MODIFICATION",
      expectedSeverity: "Critical",
    },
    {
      id: "credential_spray",
      title: "Distributed Credential Spray Across Multiple Hosts",
      description: "Simulates a coordinated horizontal failed authentication spray across 3 distinct endpoints from a single adversary source.",
      targetRule: "AUTH_FAILED_MULTI_ASSET",
      expectedSeverity: "Critical",
    },
  ];

  return (
    <AppShell>
      <div className="space-y-6 max-w-5xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
              <Flame className="w-5 h-5 text-orange-400" />
              Controlled Attack Simulation Lab
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Safe, localized attack fixtures to test, learn, and verify detection rules without third-party network scanning
            </p>
          </div>
          <button
            onClick={handleResetLab}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-red-400 hover:border-red-800 text-xs font-semibold transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Simulation Lab Data</span>
          </button>
        </div>

        {/* Lab Rules of Engagement */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-300 space-y-2">
          <div className="flex items-center gap-2 text-cyan-400 font-semibold">
            <Terminal className="w-4 h-4" />
            <span>Lab Rules of Engagement &amp; Safety Assurances</span>
          </div>
          <p className="text-slate-400 leading-relaxed">
            All simulation fixtures operate solely against explicitly configured local virtual interfaces or standard documentation test subnets (RFC 5737). No packets are ever transmitted across external public networks. Every event generated by this lab is permanently marked with the <span className="font-mono text-purple-300 font-bold">SIMULATED</span> tag in the telemetry ledger.
          </p>
        </div>

        {/* Scenarios Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {SIMULATION_SCENARIOS.map((scen) => (
            <div
              key={scen.id}
              className="p-5 rounded-xl bg-[#0F172A] border border-slate-800 flex flex-col justify-between space-y-4 shadow-sm"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-bold text-slate-100">{scen.title}</span>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                      scen.expectedSeverity === "Critical"
                        ? "bg-red-950 text-red-400 border border-red-800"
                        : scen.expectedSeverity === "High"
                        ? "bg-orange-950 text-orange-400 border border-orange-800"
                        : "bg-amber-950 text-amber-400 border border-amber-800"
                    }`}
                  >
                    {scen.expectedSeverity}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">{scen.description}</p>
                <div className="mt-3 text-[11px] font-mono text-cyan-400">
                  Target Rule: {scen.targetRule}
                </div>
              </div>

              <button
                onClick={() => handleRunSimulation(scen.id)}
                disabled={running}
                className="w-full py-2 px-3 rounded-lg bg-cyan-950/80 border border-cyan-800/60 hover:bg-cyan-900/80 text-cyan-300 font-semibold text-xs flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
              >
                {running ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Executing Scenario...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Launch Scenario</span>
                  </>
                )}
              </button>
            </div>
          ))}
        </div>

        {/* Simulation Output Result Box */}
        {result && (
          <div className="p-5 rounded-xl bg-[#0F172A] border border-slate-800 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
                <CheckCircle className="w-4 h-4" />
                <span>Simulation Executed Successfully</span>
              </div>
              <span className="text-xs font-mono text-purple-300 uppercase font-bold">
                Tag: {result.is_simulated ? "SIMULATED" : "LIVE"}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                <div className="text-slate-400 text-xs">Events Ingested</div>
                <div className="text-xl font-bold font-mono text-slate-100 mt-1">{result.events_generated}</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                <div className="text-slate-400 text-xs">Alerts Fired</div>
                <div className="text-xl font-bold font-mono text-red-400 mt-1">{result.alerts_triggered}</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                <div className="text-slate-400 text-xs">Incidents Opened</div>
                <div className="text-xl font-bold font-mono text-amber-400 mt-1">{result.incidents_created}</div>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed bg-slate-950 p-3 rounded-lg border border-slate-800">
              {result.summary}
            </p>

            <div className="flex justify-end gap-3 pt-2">
              <a
                href="/detections"
                className="text-xs text-cyan-400 hover:underline font-semibold"
              >
                Inspect Alerts in Detection Center &rarr;
              </a>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
