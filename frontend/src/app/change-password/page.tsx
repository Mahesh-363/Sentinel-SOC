"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { ShieldAlert, Lock, ArrowRight, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { useAuth } from "../../lib/auth-context";

export default function ChangePasswordPage() {
  const router = useRouter();
  const { user, loading: authLoading, changePassword, logout } = useAuth();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (newPassword.length < 12) {
      setError("New password must be at least 12 characters long");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("New password and confirmation do not match");
      return;
    }

    if (currentPassword === newPassword) {
      setError("New password cannot be identical to current password");
      return;
    }

    setLoading(true);
    try {
      await changePassword(currentPassword, newPassword);
    } catch (err: any) {
      setError(err.message || "Failed to update password. Please verify current password.");
    } finally {
      setLoading(false);
    }
  };

  if (authLoading || !user) {
    return (
      <div className="min-h-screen bg-[#070B14] flex items-center justify-center text-cyan-400">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#070B14] soc-grid-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-[#0B1120]/95 backdrop-blur-md p-8 shadow-2xl">
        <div className="flex flex-col items-center text-center">
          <div className="relative w-20 h-20 rounded-2xl bg-[#070B14] border border-cyan-500/30 p-2.5 flex items-center justify-center shadow-lg shadow-cyan-950/60 mb-4">
            <Image
              src="/branding/sentinel-logo.png"
              alt="Sentinel SOC"
              width={64}
              height={64}
              className="object-contain"
              priority
            />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-400" />
            Mandatory Credential Rotation
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-sm">
            For operational security compliance, initial credentials must be replaced with a private, high-entropy password before console access is granted.
          </p>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-red-950/40 border border-red-500/30 text-red-300 text-xs flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Current / Bootstrap Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-slate-900 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                placeholder="Current password"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              New Password (Minimum 12 Characters)
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="password"
                required
                minLength={12}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-slate-900 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                placeholder="New high-entropy password"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Confirm New Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="password"
                required
                minLength={12}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-slate-900 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
                placeholder="Re-enter new password"
              />
            </div>
          </div>

          <div className="rounded-lg bg-slate-900/60 border border-slate-800/80 p-3 space-y-1.5 text-[11px] text-slate-400">
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className={`w-3.5 h-3.5 ${newPassword.length >= 12 ? "text-cyan-400" : "text-slate-600"}`} />
              <span>At least 12 characters long</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className={`w-3.5 h-3.5 ${newPassword && newPassword === confirmPassword ? "text-cyan-400" : "text-slate-600"}`} />
              <span>Passwords match</span>
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
                  Updating Credentials...
                </>
              ) : (
                <>
                  Update Password & Enter Console
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => logout()}
            className="text-xs text-slate-500 hover:text-slate-400 transition-colors underline"
          >
            Cancel & Return to Login
          </button>
        </div>
      </div>
    </div>
  );
}
