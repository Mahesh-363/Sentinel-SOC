"use client";

import React, { useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { Shield, Lock, Mail, ArrowRight, Loader2, AlertCircle } from "lucide-react";
import { useAuth } from "../../lib/auth-context";
import { ExplainErrorModal } from "../../components/ExplainErrorModal";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("admin@sentinelsoc.com");
  const [password, setPassword] = useState("SentinelAdmin123!");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [explainOpen, setExplainOpen] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070B14] soc-grid-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-[#0B1120]/95 backdrop-blur-md p-8 shadow-2xl">
        <div className="flex flex-col items-center text-center">
          <div className="relative w-20 h-20 sm:w-24 sm:h-24 rounded-2xl bg-[#070B14]/90 border border-cyan-500/40 p-2 flex items-center justify-center shadow-xl shadow-cyan-950/60 mb-4 group ring-1 ring-cyan-500/20 backdrop-blur-sm">
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-b from-cyan-500/10 via-transparent to-slate-800/30 pointer-events-none" />
            <Image
              src="/branding/sentinel-logo.png"
              alt="Sentinel SOC Official Emblem"
              width={88}
              height={88}
              className="object-contain drop-shadow-[0_0_12px_rgba(6,182,212,0.35)] transform group-hover:scale-105 transition-transform duration-300"
              priority
            />
          </div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-wider text-slate-100 flex items-center gap-2">
            SENTINEL <span className="text-cyan-400 text-xs px-2 py-0.5 rounded bg-cyan-950/90 border border-cyan-800/50 font-mono tracking-normal">SOC</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">AI-Assisted Security Operations Center Platform</p>
        </div>

        {error && (
          <div className="mt-5 p-3 rounded-lg bg-red-950/40 border border-red-900/50 text-red-300 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
              <span>{error}</span>
            </div>
            <button
              type="button"
              onClick={() => setExplainOpen(true)}
              className="text-[11px] underline text-cyan-400 hover:text-cyan-300 font-medium ml-2"
            >
              Explain Error
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Operator Email</label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-slate-900 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                placeholder="analyst@defense.org"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Security Credential / Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-slate-900 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                placeholder="••••••••••••"
              />
            </div>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs tracking-wider uppercase flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Authenticating...
                </>
              ) : (
                <>
                  Access Sentinel Console
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </form>

        <div className="mt-6 pt-4 border-t border-slate-800/80 text-center text-xs text-slate-400">
          New deployment?{" "}
          <a href="/register" className="text-cyan-400 hover:underline font-medium">
            Register initial administrator
          </a>
        </div>
      </div>

      <ExplainErrorModal
        isOpen={explainOpen}
        onClose={() => setExplainOpen(false)}
        errorMessage={error || "Authentication failure"}
        moduleName="Authentication"
        errorCode="AUTH_ERR_401"
      />
    </div>
  );
}
