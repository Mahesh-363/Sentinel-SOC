"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";
import { ChevronDown, Bell, HelpCircle, ShieldCheck, Sparkles } from "lucide-react";
import { useAuth, OrgInfo } from "../../lib/auth-context";
import { fetchApi } from "../../lib/api";

export function TopNav() {
  const { organizations, activeOrg, setActiveOrg } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (activeOrg) {
      fetchApi("/notifications?unread_only=true")
        .then((res) => setUnreadCount(res.length || 0))
        .catch(() => {});
    }
  }, [activeOrg]);

  return (
    <header className="h-14 border-b border-slate-800 bg-[#0B1120]/90 backdrop-blur-md px-6 flex items-center justify-between z-40">
      {/* Left: Organization Switcher & Mobile Brand */}
      <div className="flex items-center gap-3">
        <div className="md:hidden flex items-center">
          <div className="w-8 h-8 rounded-lg bg-[#070B14] border border-cyan-500/40 p-1 flex items-center justify-center shadow-sm shadow-cyan-950/40">
            <Image
              src="/branding/sentinel-logo.png"
              alt="Sentinel SOC"
              width={26}
              height={26}
              className="object-contain"
            />
          </div>
        </div>
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-medium text-slate-200 hover:border-slate-700 transition-colors"
          >
            <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
            <span>{activeOrg?.name || "Select Organization"}</span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

        {dropdownOpen && (
          <div className="absolute left-0 mt-1.5 w-60 rounded-lg bg-[#0F172A] border border-slate-800 shadow-xl py-1 z-50 text-xs">
            <div className="px-3 py-1.5 text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
              Switch Organization
            </div>
            {organizations.map((org: OrgInfo) => (
              <button
                key={org.id}
                onClick={() => {
                  setActiveOrg(org);
                  setDropdownOpen(false);
                }}
                className={`w-full text-left px-3 py-2 flex items-center justify-between hover:bg-slate-800/80 transition-colors ${
                  activeOrg?.id === org.id ? "text-cyan-400 font-semibold bg-cyan-950/20" : "text-slate-300"
                }`}
              >
                <span className="truncate">{org.name}</span>
                <span className="text-[10px] text-slate-400 uppercase">{org.role}</span>
              </button>
            ))}
          </div>
        )}
        </div>
      </div>

      {/* Right: SOC Status & Controls */}
      <div className="flex items-center gap-4 text-xs">
        {/* Connection status */}
        <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-950/50 border border-emerald-800/50 text-emerald-400 text-[11px] font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>SOC Active</span>
        </div>

        {/* Free Tier AI Badge */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-cyan-950/40 border border-cyan-800/40 text-cyan-300 text-[11px]">
          <Sparkles className="w-3 h-3 text-cyan-400" />
          <span>Free-Tier / Local AI</span>
        </div>

        {/* Helpdesk link */}
        <a
          href="/ai-helpdesk"
          title="Sentinel AI Helpdesk"
          className="p-1.5 rounded-lg border border-slate-800 bg-slate-900/60 text-slate-400 hover:text-cyan-400 hover:border-slate-700 transition-colors"
        >
          <HelpCircle className="w-4 h-4" />
        </a>

        {/* Notifications */}
        <a
          href="/notifications"
          title="Notifications"
          className="relative p-1.5 rounded-lg border border-slate-800 bg-slate-900/60 text-slate-400 hover:text-slate-200 hover:border-slate-700 transition-colors"
        >
          <Bell className="w-4 h-4" />
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 px-1 min-w-[16px] h-4 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center">
              {unreadCount}
            </span>
          )}
        </a>
      </div>
    </header>
  );
}
