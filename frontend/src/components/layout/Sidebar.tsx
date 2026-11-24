"use client";

import React from "react";
import Image from "next/image";
import Link from "next/navigation";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Server,
  Cpu,
  Network,
  Globe,
  Activity,
  ShieldAlert,
  AlertOctagon,
  Bot,
  HelpCircle,
  Cloud,
  Bell,
  FileText,
  Flame,
  Settings,
  Shield,
  LogOut,
} from "lucide-react";
import { useAuth } from "../../lib/auth-context";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/assets", label: "Assets", icon: Server },
  { href: "/sensors", label: "Sensors", icon: Cpu },
  { href: "/network", label: "Network Intelligence", icon: Network },
  { href: "/ip-intel", label: "IP Intelligence", icon: Globe },
  { href: "/events", label: "Security Events", icon: Activity },
  { href: "/detections", label: "Detection Center", icon: ShieldAlert },
  { href: "/incidents", label: "Incidents", icon: AlertOctagon },
  { href: "/ai-analyst", label: "AI Security Analyst", icon: Bot, badge: "AI" },
  { href: "/ai-helpdesk", label: "AI Helpdesk", icon: HelpCircle, badge: "RAG" },
  { href: "/aws-security", label: "AWS Security", icon: Cloud },
  { href: "/notifications", label: "Notifications", icon: Bell },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/simulation", label: "Simulation Lab", icon: Flame, badge: "Lab" },
  { href: "/admin", label: "Administration", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, activeOrg, logout } = useAuth();

  return (
    <aside className="w-64 flex flex-col bg-[#070b14] border-r border-slate-800/80 text-slate-300 min-h-screen select-none">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="relative w-9 h-9 rounded-lg bg-[#090e1a] border border-cyan-500/40 flex items-center justify-center overflow-hidden shadow-sm shadow-cyan-950/50 flex-shrink-0 group">
            <Image
              src="/branding/sentinel-logo.png"
              alt="Sentinel SOC Metallic Cyber-Eye"
              width={36}
              height={36}
              className="object-contain p-0.5 transform group-hover:scale-105 transition-transform duration-200"
              priority
            />
          </div>
          <div className="min-w-0">
            <h1 className="font-bold text-slate-100 tracking-wider text-sm flex items-center gap-1.5 truncate">
              SENTINEL <span className="text-cyan-400 text-xs px-1.5 py-0.5 rounded bg-cyan-950/80 border border-cyan-800/40 font-mono">SOC</span>
            </h1>
            <p className="text-[10px] text-slate-400 tracking-tight truncate">Monitor &bull; Detect &bull; Investigate &bull; Protect</p>
          </div>
        </div>

        {activeOrg && (
          <div className="mt-3 px-2 py-1.5 rounded-md bg-slate-900/80 border border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
            <span className="truncate max-w-[150px] font-medium text-slate-300">{activeOrg.name}</span>
            <span className="text-[9px] px-1 rounded bg-slate-800 text-cyan-400 border border-slate-700/60 uppercase">{activeOrg.role}</span>
          </div>
        )}
      </div>

      {/* Navigation List */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <a
              key={item.href}
              href={item.href}
              className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                isActive
                  ? "bg-cyan-950/60 text-cyan-300 border border-cyan-800/50 shadow-sm shadow-cyan-950"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/70"
              }`}
            >
              <div className="flex items-center gap-2.5">
                <Icon className={`w-4 h-4 ${isActive ? "text-cyan-400" : "text-slate-400"}`} />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span className="text-[9px] px-1.5 py-0.2 rounded font-semibold bg-slate-800 text-cyan-400 border border-slate-700">
                  {item.badge}
                </span>
              )}
            </a>
          );
        })}
      </nav>

      {/* User Footer */}
      <div className="p-3 border-t border-slate-800/80 bg-[#060910]">
        <div className="flex items-center justify-between">
          <div className="truncate pr-2">
            <p className="text-xs font-semibold text-slate-200 truncate">{user?.full_name || "Analyst"}</p>
            <p className="text-[10px] text-slate-400 truncate">{user?.email}</p>
          </div>
          <button
            onClick={logout}
            title="Log out"
            className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-red-400 transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
