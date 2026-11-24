"use client";

import React, { useEffect, useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useAuth } from "../../lib/auth-context";
import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";
import { ExplainErrorModal } from "../ExplainErrorModal";
import { HelpCircle, Loader2 } from "lucide-react";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [explainModalOpen, setExplainModalOpen] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#090D16] flex items-center justify-center text-cyan-400">
        <div className="flex flex-col items-center gap-4">
          <div className="relative w-16 h-16 rounded-2xl bg-[#070B14] border border-cyan-500/40 p-2 flex items-center justify-center shadow-lg shadow-cyan-950/60 animate-pulse">
            <Image
              src="/branding/sentinel-logo.png"
              alt="Sentinel SOC"
              width={52}
              height={52}
              className="object-contain"
              priority
            />
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-400 font-mono uppercase tracking-wider">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-400" />
            <span>Loading Sentinel SOC...</span>
          </div>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="flex min-h-screen bg-[#090D16] text-slate-200">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopNav />
        <main className="flex-1 p-6 overflow-y-auto soc-grid-bg">{children}</main>
      </div>

      {/* Floating Explain This Error Button */}
      <button
        onClick={() => setExplainModalOpen(true)}
        className="fixed bottom-4 right-4 z-40 flex items-center gap-2 px-3 py-2 rounded-full bg-cyan-950/90 border border-cyan-500/40 text-cyan-300 text-xs font-semibold shadow-lg shadow-black/50 hover:bg-cyan-900/80 transition-all hover:scale-105"
      >
        <HelpCircle className="w-4 h-4 text-cyan-400" />
        <span>Explain This Error</span>
      </button>

      <ExplainErrorModal
        isOpen={explainModalOpen}
        onClose={() => setExplainModalOpen(false)}
        errorMessage="Manual diagnostic check requested from active view"
        moduleName="Active Interface"
        errorCode="USER_QUERY"
      />
    </div>
  );
}
