"use client";
import { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import { AlertTriangle, ChevronRight, Search, CheckCircle, XCircle, Shield, Loader2 } from "lucide-react";

export default function ExceptionsPage() {
  const [exceptions, setExceptions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedExc, setSelectedExc] = useState<any>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [filter, setFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [page, setPage] = useState(1);
  const pageSize = 50;

  useEffect(() => {
    fetchApi("/exceptions")
      .then(data => {
        setExceptions(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const runInvestigation = async (exc: any) => {
    setAiLoading(true);
    try {
      const data = await fetchApi(`/exceptions/${exc.id}/investigate`, { method: "POST" });
      const inv = data.investigation || data;
      const updatedExc = { ...exc, ai_analysis: inv.explanation, recommended_action: inv.recommended_action, ai_decision: inv.decision, ai_confidence: inv.confidence };
      setExceptions(exceptions.map(e => e.id === exc.id ? updatedExc : e));
      setSelectedExc(updatedExc);
    } catch (err) {
      const updatedExc = { ...exc, ai_analysis: "AI investigation failed. Please try again or proceed with manual review." };
      setSelectedExc(updatedExc);
    } finally {
      setAiLoading(false);
    }
  };

  const resolveException = async (exc: any, action: "resolve" | "reject") => {
    try {
      await fetchApi(`/exceptions/${exc.id}/${action}`, { method: "POST" });
      const newStatus = action === "resolve" ? "RESOLVED" : "REJECTED";
      const updatedExc = { ...exc, status: newStatus };
      setExceptions(exceptions.map(e => e.id === exc.id ? updatedExc : e));
      setSelectedExc(updatedExc);
    } catch (err) {
      console.error(err);
    }
  };

  const types = Array.from(new Set(exceptions.map(e => e.exception_type)));
  const filtered = exceptions.filter(e => {
    if (filter !== "ALL" && e.exception_type !== filter) return false;
    if (statusFilter !== "ALL" && e.status !== statusFilter) return false;
    return true;
  });

  const severityColor: Record<string, string> = {
    CRITICAL: "bg-red-100 text-red-800 border-red-200",
    HIGH: "bg-orange-100 text-orange-800 border-orange-200",
    MEDIUM: "bg-yellow-100 text-yellow-800 border-yellow-200",
    LOW: "bg-slate-100 text-slate-700 border-slate-200",
  };

  const statusColor: Record<string, string> = {
    OPEN: "bg-blue-100 text-blue-800",
    RESOLVED: "bg-green-100 text-green-800",
    REJECTED: "bg-red-100 text-red-800",
  };

  return (
    <div className="max-w-7xl mx-auto h-[calc(100vh-64px)] flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Exceptions</h2>
          <p className="text-slate-500 text-sm">Review ambiguous cases. AI investigates; policies decide; humans approve.</p>
        </div>
        <div className="flex gap-2">
          <select value={filter} onChange={e => setFilter(e.target.value)} className="text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white">
            <option value="ALL">All Types</option>
            {types.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white">
            <option value="ALL">All Status</option>
            <option value="OPEN">Open</option>
            <option value="RESOLVED">Resolved</option>
            <option value="REJECTED">Rejected</option>
          </select>
        </div>
      </div>

      <div className="flex-1 flex gap-4 overflow-hidden min-h-0">
        {/* List */}
        <div className="w-[340px] flex-shrink-0 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 bg-slate-50 text-sm font-semibold text-slate-600">
            {filtered.length} of {exceptions.length} Exceptions
          </div>
          <div className="flex-1 overflow-y-auto">
            {loading ? <div className="p-4 text-slate-400 text-sm">Loading...</div> : filtered.length === 0 ? (
              <div className="p-6 text-center text-slate-400 text-sm">No exceptions match filter.</div>
            ) : filtered.slice((page - 1) * pageSize, page * pageSize).map(exc => (
              <button
                key={exc.id}
                onClick={() => setSelectedExc(exc)}
                className={`w-full text-left px-4 py-3 border-b border-slate-50 hover:bg-slate-50 transition-colors flex justify-between items-center gap-2 ${
                  selectedExc?.id === exc.id ? 'bg-blue-50 border-l-2 border-l-blue-500' : ''
                }`}
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-semibold px-1.5 py-0.5 rounded border ${severityColor[exc.severity] || severityColor.MEDIUM}`}>
                      {exc.severity}
                    </span>
                    <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${statusColor[exc.status] || statusColor.OPEN}`}>
                      {exc.status}
                    </span>
                  </div>
                  <div className="text-sm font-medium text-slate-800 mt-1">{exc.exception_type.replace(/_/g, ' ')}</div>
                  <div className="text-xs text-slate-400 truncate mt-0.5">{exc.id}</div>
                </div>
                <ChevronRight className="h-4 w-4 text-slate-300 flex-shrink-0" />
              </button>
            ))}
          </div>
          
          {!loading && filtered.length > pageSize && (
            <div className="bg-slate-50 border-t border-slate-200 px-3 py-2 flex items-center justify-between">
              <div className="text-xs text-slate-500">
                {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, filtered.length)}
              </div>
              <div className="flex gap-1">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-2 py-1 border border-slate-300 rounded text-xs font-medium bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  Prev
                </button>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={page * pageSize >= filtered.length}
                  className="px-2 py-1 border border-slate-300 rounded text-xs font-medium bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Details */}
        <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-y-auto">
          {selectedExc ? (
            <div className="p-6 space-y-6">
              {/* Header */}
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-xl font-bold text-slate-900">{selectedExc.exception_type.replace(/_/g, ' ')}</h3>
                  <div className="text-xs text-slate-400 mt-1 font-mono">{selectedExc.id}</div>
                </div>
                <div className="flex gap-2">
                  <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${severityColor[selectedExc.severity] || severityColor.MEDIUM}`}>
                    {selectedExc.severity}
                  </span>
                  <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${statusColor[selectedExc.status] || statusColor.OPEN}`}>
                    {selectedExc.status}
                  </span>
                </div>
              </div>

              {/* Why Not Auto-Resolved */}
              <div className="bg-amber-50 border border-amber-200 p-4 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Shield className="h-4 w-4 text-amber-600" />
                  <h4 className="font-semibold text-amber-900 text-sm">Why Not Auto-Resolved?</h4>
                </div>
                <p className="text-sm text-amber-800">{selectedExc.description}</p>
              </div>

              {/* AI Investigation */}
              <div className="border border-slate-200 rounded-lg overflow-hidden">
                <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center gap-2">
                  <Search className="h-4 w-4 text-blue-600" />
                  <h4 className="font-semibold text-slate-800 text-sm">AI Investigator</h4>
                </div>
                <div className="p-4">
                  {selectedExc.ai_analysis ? (
                    <div className="space-y-3">
                      {selectedExc.ai_decision && (
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-semibold text-slate-500">AI Decision:</span>
                          <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                            selectedExc.ai_decision === 'MATCH' ? 'bg-green-100 text-green-800' :
                            selectedExc.ai_decision === 'REVIEW' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-red-100 text-red-800'
                          }`}>{selectedExc.ai_decision}</span>
                          {selectedExc.ai_confidence !== undefined && (
                            <span className="text-xs text-slate-400">Confidence: {(selectedExc.ai_confidence * 100).toFixed(0)}%</span>
                          )}
                        </div>
                      )}
                      <div className="bg-blue-50 p-3 rounded-lg border border-blue-100">
                        <p className="text-sm text-blue-900 whitespace-pre-wrap">
                          {selectedExc.ai_analysis?.split('\n\n[POLICY ENGINE OVERRIDE]: ')[0]}
                        </p>
                      </div>
                      {selectedExc.ai_analysis?.includes('[POLICY ENGINE OVERRIDE]: ') && (
                        <div className="bg-red-50 p-3 rounded-lg border border-red-200">
                           <div className="flex items-center gap-2 mb-1">
                             <Shield className="h-4 w-4 text-red-600" />
                             <h4 className="font-semibold text-red-900 text-xs uppercase">Policy Engine Override</h4>
                           </div>
                           <p className="text-sm text-red-800">
                             {selectedExc.ai_analysis?.split('\n\n[POLICY ENGINE OVERRIDE]: ')[1]}
                           </p>
                        </div>
                      )}
                      {selectedExc.recommended_action && (
                        <div className="bg-emerald-50 p-3 rounded-lg border border-emerald-100">
                          <p className="text-xs font-semibold text-emerald-700 mb-1">Recommended Action</p>
                          <p className="text-sm text-emerald-900">{selectedExc.recommended_action}</p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-4">
                      <p className="text-sm text-slate-500 mb-3">No AI investigation yet.</p>
                      <button
                        onClick={() => runInvestigation(selectedExc)}
                        disabled={aiLoading}
                        className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
                      >
                        {aiLoading ? (
                          <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Investigating...</>
                        ) : (
                          <><Search className="mr-2 h-4 w-4" />Run AI Investigation</>
                        )}
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Human Review Actions */}
              {selectedExc.status === "OPEN" && (
                <div className="border border-slate-200 rounded-lg overflow-hidden">
                  <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
                    <h4 className="font-semibold text-slate-800 text-sm">Human Review</h4>
                  </div>
                  <div className="p-4 flex gap-3">
                    <button
                      onClick={() => resolveException(selectedExc, "resolve")}
                      className="flex-1 inline-flex items-center justify-center px-4 py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
                    >
                      <CheckCircle className="mr-2 h-4 w-4" /> Mark Resolved
                    </button>
                    <button
                      onClick={() => resolveException(selectedExc, "reject")}
                      className="flex-1 inline-flex items-center justify-center px-4 py-2.5 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors"
                    >
                      <XCircle className="mr-2 h-4 w-4" /> Reject
                    </button>
                  </div>
                </div>
              )}
              {selectedExc.status !== "OPEN" && (
                <div className={`p-4 rounded-lg border ${selectedExc.status === 'RESOLVED' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                  <p className="text-sm font-semibold">
                    {selectedExc.status === 'RESOLVED' ? '✓ This exception has been resolved.' : '✗ This exception was rejected.'}
                  </p>
                  {selectedExc.reviewed_at && (
                    <p className="text-xs text-slate-500 mt-1">Reviewed: {new Date(selectedExc.reviewed_at).toLocaleString()}</p>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-400 text-sm">
              <div className="text-center">
                <AlertTriangle className="h-10 w-10 mx-auto mb-3 text-slate-300" />
                Select an exception to view details and investigate
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
