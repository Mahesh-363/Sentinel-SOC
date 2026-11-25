"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "../../components/layout/AppShell";
import { fetchApi } from "../../lib/api";
import { formatLocalDateTime } from "../../lib/date";
import { Bell, Check, CheckCheck, RefreshCw, AlertTriangle, ShieldAlert, AlertOctagon } from "lucide-react";

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadNotifications = async () => {
    try {
      const data = await fetchApi("/notifications");
      setNotifications(data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNotifications();
  }, []);

  const handleMarkRead = async (id: string) => {
    try {
      await fetchApi(`/notifications/${id}/read`, { method: "PATCH" });
      loadNotifications();
    } catch (e) {}
  };

  const handleMarkAllRead = async () => {
    try {
      await fetchApi("/notifications/mark-all-read", { method: "POST" });
      loadNotifications();
    } catch (e) {}
  };

  return (
    <AppShell>
      <div className="space-y-6 max-w-4xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2">
              <Bell className="w-5 h-5 text-cyan-400" />
              Notifications &amp; Security Broadcasts
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              In-app alerting queue with tenant isolation and severity-based escalation
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadNotifications}
              className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-cyan-400"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={handleMarkAllRead}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 text-xs font-semibold transition-colors"
            >
              <CheckCheck className="w-4 h-4" />
              <span>Mark All as Read</span>
            </button>
          </div>
        </div>

        {/* Notifications List */}
        <div className="rounded-xl bg-[#0F172A] border border-slate-800 overflow-hidden shadow-sm divide-y divide-slate-800/60">
          {notifications.length > 0 ? (
            notifications.map((n) => (
              <div
                key={n.id}
                className={`p-4 flex items-start justify-between gap-4 transition-colors ${
                  n.is_read ? "opacity-75 bg-[#0F172A]" : "bg-slate-900/40"
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5">
                    {n.severity === "Critical" ? (
                      <ShieldAlert className="w-5 h-5 text-red-400" />
                    ) : n.severity === "High" ? (
                      <AlertOctagon className="w-5 h-5 text-orange-400" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-amber-400" />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-slate-200">{n.title}</span>
                      <span
                        className={`text-[10px] px-1.5 py-0.2 rounded font-semibold ${
                          n.severity === "Critical"
                            ? "bg-red-950 text-red-400"
                            : n.severity === "High"
                            ? "bg-orange-950 text-orange-400"
                            : "bg-amber-950 text-amber-400"
                        }`}
                      >
                        {n.severity}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1 leading-relaxed">{n.message}</p>
                    <div className="text-[10px] text-slate-500 font-mono mt-2">
                      {formatLocalDateTime(n.created_at)}
                    </div>
                  </div>
                </div>

                {!n.is_read && (
                  <button
                    onClick={() => handleMarkRead(n.id)}
                    className="p-1.5 rounded bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-cyan-400 text-xs flex items-center gap-1 flex-shrink-0"
                    title="Mark as read"
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>Read</span>
                  </button>
                )}
              </div>
            ))
          ) : (
            <div className="py-12 text-center text-slate-500 text-xs">
              {loading ? "Loading notifications..." : "No notifications in feed."}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
