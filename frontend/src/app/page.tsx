"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../lib/auth-context";
import { Loader2 } from "lucide-react";

export default function HomePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      if (user) {
        router.push("/dashboard");
      } else {
        router.push("/login");
      }
    }
  }, [user, loading, router]);

  return (
    <div className="min-h-screen bg-[#090D16] flex items-center justify-center text-cyan-400">
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="w-8 h-8 animate-spin" />
        <p className="text-xs text-slate-400 font-mono tracking-wider">SENTINEL SOC INITIALIZING...</p>
      </div>
    </div>
  );
}
