"use client";
import { useState } from "react";
import { fetchApi } from "@/lib/api";
import { Play, CheckCircle, AlertCircle, Clock, Zap, ShieldCheck, Loader2 } from "lucide-react";

export default function ReconciliationPage() {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const startReconciliation = async () => {
    setRunning(true);
    setResult(null);
    setError(null);
    try {
      const data = await fetchApi("/reconcile", { method: "POST" });
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Reconciliation failed");
    } finally {
      setRunning(false);
    }
  };

  const autoMatchRate = result ? ((result.auto_matched / result.total_records) * 100).toFixed(1) : null;
  const exceptionRate = result ? ((result.escalated / result.total_records) * 100).toFixed(1) : null;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Run Reconciliation</h2>
        <p className="text-slate-500 text-sm">Process all payments against settlements and bank records using the deterministic matching engine.</p>
      </div>

      {/* How It Works */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-3">Reconciliation Pipeline</h3>
        <div className="flex items-center gap-2 text-xs text-slate-500 overflow-x-auto pb-1">
          {["Validation", "Normalization", "Exact Match", "Fee Tolerance", "Candidate Scoring", "Exception Detection", "Audit Log"].map((step, i) => (
            <span key={step} className="flex items-center gap-1 whitespace-nowrap">
              {i > 0 && <span className="text-slate-300 mx-1">→</span>}
              <span className="bg-slate-100 px-2 py-1 rounded font-medium">{step}</span>
            </span>
          ))}
        </div>
      </div>

      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <button
          onClick={startReconciliation}
          disabled={running}
          className={`flex items-center px-5 py-2.5 rounded-lg font-medium text-white transition-all ${
            running ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 hover:shadow-md'
          }`}
        >
          {running ? (
            <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Processing...</>
          ) : (
            <><Play className="mr-2 h-4 w-4" />Start Reconciliation Run</>
          )}
        </button>

        {error && (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
            <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-red-800">Reconciliation failed</p>
              <p className="text-sm text-red-600 mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {result && (
          <div className="mt-6 space-y-5">
            <div className="flex items-center text-green-600 gap-2">
              <CheckCircle className="h-5 w-5" />
              <h3 className="text-lg font-semibold">Run Completed — {result.id}</h3>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Stat label="Total Records" value={result.total_records} />
              <Stat label="Auto-Matched" value={result.auto_matched} highlight="green" />
              <Stat label="Exceptions" value={result.escalated} highlight="red" />
              <Stat label="Unresolved" value={result.unresolved} highlight="amber" />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <Stat label="Auto-Match Rate" value={`${autoMatchRate}%`} icon={<Zap className="h-4 w-4 text-green-500" />} />
              <Stat label="Exception Rate" value={`${exceptionRate}%`} icon={<AlertCircle className="h-4 w-4 text-red-500" />} />
              <Stat label="Processing Time" value={result.processing_time_ms ? `${(result.processing_time_ms / 1000).toFixed(2)}s` : "—"} icon={<Clock className="h-4 w-4 text-blue-500" />} />
            </div>

            <div className="flex gap-3 pt-2">
              <a href="/exceptions" className="text-sm text-red-600 hover:underline font-medium">Review exceptions →</a>
              <a href="/evaluations" className="text-sm text-purple-600 hover:underline font-medium">View evaluation →</a>
              <a href="/audit" className="text-sm text-slate-600 hover:underline font-medium">Audit trail →</a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value, highlight, icon }: { label: string; value: string | number; highlight?: string; icon?: React.ReactNode }) {
  const borderColor = highlight === 'green' ? 'border-green-200 bg-green-50/50' : highlight === 'red' ? 'border-red-200 bg-red-50/50' : highlight === 'amber' ? 'border-amber-200 bg-amber-50/50' : 'border-slate-100 bg-slate-50';
  return (
    <div className={`p-4 rounded-lg border ${borderColor}`}>
      <div className="flex items-center gap-1.5">
        {icon}
        <span className="text-xs text-slate-500 font-medium">{label}</span>
      </div>
      <div className="text-xl font-bold text-slate-900 mt-1">{value}</div>
    </div>
  );
}
