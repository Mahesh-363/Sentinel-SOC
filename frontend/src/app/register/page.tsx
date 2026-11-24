"use client";

import React, { useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { Shield, Lock, Mail, User, Building, ArrowRight, Loader2, AlertCircle } from "lucide-react";
import { useAuth } from "../../lib/auth-context";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [orgName, setOrgName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await register(email, password, fullName, orgName);
    } catch (err: any) {
      setError(err.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070B14] soc-grid-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-[#0B1120]/95 backdrop-blur-md p-8 shadow-2xl">
        <div className="flex flex-col items-center text-center">
          <div className="relative w-16 h-16 sm:w-20 sm:h-20 rounded-xl bg-[#070B14]/90 border border-cyan-500/40 p-1.5 flex items-center justify-center shadow-lg shadow-cyan-950/50 mb-3 group ring-1 ring-cyan-500/20">
            <Image
              src="/branding/sentinel-logo.png"
              alt="Sentinel SOC Official Emblem"
              width={64}
              height={64}
              className="object-contain drop-shadow-[0_0_8px_rgba(6,182,212,0.3)] transform group-hover:scale-105 transition-transform duration-300"
              priority
            />
          </div>
          <h1 className="text-xl font-bold tracking-wider text-slate-100">
            Sentinel SOC Enrollment
          </h1>
          <p className="text-xs text-slate-400 mt-1 font-medium">Establish New Security Organization</p>
        </div>

        {error && (
          <div className="mt-5 p-3 rounded-lg bg-red-950/40 border border-red-900/50 text-red-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Full Name</label>
            <div className="relative">
              <User className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-slate-900 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                placeholder="Chief Security Officer"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Official Email</label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-slate-900 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                placeholder="cso@defense.org"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Organization Name</label>
            <div className="relative">
              <Building className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="text"
                required
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-slate-900 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                placeholder="Enterprise Security Command"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-slate-900 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
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
                  Creating Organization...
                </>
              ) : (
                <>
                  Establish Organization
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </form>

        <div className="mt-6 pt-4 border-t border-slate-800/80 text-center text-xs text-slate-400">
          Already registered?{" "}
          <a href="/login" className="text-cyan-400 hover:underline font-medium">
            Sign in to existing account
          </a>
        </div>
      </div>
    </div>
  );
}
