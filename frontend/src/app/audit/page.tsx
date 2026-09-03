"use client";
import { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import { Activity, Shield } from "lucide-react";

export default function AuditPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("ALL");

  useEffect(() => {
    fetchApi("/audit")
      .then(data => {
        setEvents(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const actions = Array.from(new Set(events.map(e => e.action)));
  const filtered = filter === "ALL" ? events : events.filter(e => e.action === filter);

  const actionColor: Record<string, string> = {
    MATCH_EXACT: "bg-green-100 text-green-700",
    MATCH_FEE_ADJUSTMENT: "bg-blue-100 text-blue-700",
    ESCALATE_TO_REVIEW: "bg-red-100 text-red-700",
    AI_INVESTIGATION: "bg-purple-100 text-purple-700",
    AI_FAILURE: "bg-red-100 text-red-800",
    START_RECONCILIATION: "bg-slate-100 text-slate-700",
    COMPLETE_RECONCILIATION: "bg-emerald-100 text-emerald-700",
    HUMAN_RESOLVE: "bg-green-100 text-green-700",
    HUMAN_REJECT: "bg-red-100 text-red-700",
  };

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Audit Trail</h2>
          <p className="text-slate-500 text-sm">Immutable chronological ledger of all system, AI, and human actions.</p>
        </div>
        <select value={filter} onChange={e => setFilter(e.target.value)} className="text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white">
          <option value="ALL">All Actions</option>
          {actions.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? <div className="p-8 text-center text-slate-400 text-sm">Loading audit events...</div> : filtered.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">
            <Shield className="h-10 w-10 mx-auto mb-3 text-slate-300" />
            No audit events found.
          </div>
        ) : (
          <div className="divide-y divide-slate-100 max-h-[calc(100vh-200px)] overflow-y-auto">
            {filtered.map(event => (
              <div key={event.id} className="px-5 py-3 hover:bg-slate-50 transition-colors">
                <div className="flex justify-between items-center mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${actionColor[event.action] || 'bg-slate-100 text-slate-700'}`}>
                      {event.action}
                    </span>
                    <span className="text-xs font-medium text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded">
                      {event.actor}
                    </span>
                  </div>
                  <span className="text-xs text-slate-400">
                    {new Date(event.created_at).toLocaleString()}
                  </span>
                </div>
                <div className="pl-0.5 text-xs text-slate-600">
                  <span className="font-mono text-slate-500">{event.entity_type}:{event.entity_id}</span>
                  {event.decision && <span className="ml-3">→ <strong>{event.decision}</strong></span>}
                  {event.reason && <span className="ml-2 text-slate-400">— {event.reason}</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
