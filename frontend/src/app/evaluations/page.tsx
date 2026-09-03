"use client";
import { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import { Target, Play, Loader2, CheckCircle, Activity } from "lucide-react";

export default function EvaluationsPage() {
  const [evals, setEvals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningHeldout, setRunningHeldout] = useState(false);

  const loadEvals = () => {
    fetchApi("/evaluations")
      .then(data => {
        setEvals(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => { loadEvals(); }, []);

  const runHeldoutEval = async () => {
    setRunningHeldout(true);
    try {
      await fetchApi("/evaluate/heldout", { method: "POST" });
      loadEvals();
    } catch (err) {
      console.error(err);
    } finally {
      setRunningHeldout(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Evaluations</h2>
          <p className="text-slate-500 text-sm">Accuracy metrics computed from actual reconciliation runs against ground-truth data.</p>
        </div>
        <button
          onClick={runHeldoutEval}
          disabled={runningHeldout}
          className="inline-flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 transition-colors disabled:opacity-50"
        >
          {runningHeldout ? (
            <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Running...</>
          ) : (
            <><Play className="mr-2 h-4 w-4" />Run Held-Out Evaluation</>
          )}
        </button>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
        <strong>Note:</strong> All metrics below are calculated from reproducible evaluation runs — never hardcoded.
        Held-out evaluations use a separate dataset (seed=99, 500 records) not seen during demo reconciliation.
      </div>

      <div className="space-y-4">
        {loading ? (
          <div className="p-8 bg-white rounded-xl border border-slate-200 text-center text-slate-400">Loading...</div>
        ) : evals.length === 0 ? (
          <div className="bg-white p-8 rounded-xl border border-slate-200 text-center text-slate-500">
            <Activity className="h-12 w-12 mx-auto text-slate-300 mb-4" />
            No evaluations run yet. Run a reconciliation first, then evaluate.
          </div>
        ) : evals.map(run => (
          <div key={run.id} className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Target className={`h-5 w-5 ${run.dataset_type === 'HELDOUT' ? 'text-purple-500' : 'text-blue-500'}`} />
                <span className="font-semibold text-slate-800">
                  {run.dataset_name.toUpperCase()}
                </span>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                  run.dataset_type === 'HELDOUT' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
                }`}>{run.dataset_type}</span>
              </div>
              <span className="text-xs text-slate-400">{new Date(run.created_at).toLocaleString()}</span>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <EvalStat label="Total Records" value={run.total_records} />
                <EvalStat label="Correct" value={run.correct_matches} highlight="green" />
                <EvalStat label="Incorrect" value={run.incorrect_matches} highlight={run.incorrect_matches > 0 ? "red" : undefined} />
                <EvalStat label="Unresolved" value={run.unresolved_records} />
                <EvalStat label="Precision" value={`${(run.precision * 100).toFixed(1)}%`} large />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                <EvalStat label="Recall" value={`${(run.recall * 100).toFixed(1)}%`} />
                <EvalStat label="Accuracy" value={`${(run.accuracy * 100).toFixed(1)}%`} />
                <EvalStat label="Unresolved Rate" value={`${((run.unresolved_records / run.total_records) * 100).toFixed(1)}%`} />
                <EvalStat label="Auto-Res. Precision" value={run.auto_resolution_precision !== null ? `${(run.auto_resolution_precision * 100).toFixed(1)}%` : "—"} />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 border-t border-slate-100 pt-4">
                <EvalStat label="3-Way Precision" value={run.three_way_precision !== null ? `${(run.three_way_precision * 100).toFixed(1)}%` : "—"} highlight="blue" />
                <EvalStat label="3-Way Recall" value={run.three_way_recall !== null ? `${(run.three_way_recall * 100).toFixed(1)}%` : "—"} />
                <EvalStat label="3-Way Match Rate" value={run.three_way_match_rate !== null ? `${(run.three_way_match_rate * 100).toFixed(1)}%` : "—"} />
                <EvalStat label="Throughput (rec/s)" value={run.throughput_records_per_second ? run.throughput_records_per_second.toFixed(1) : "—"} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function EvalStat({ label, value, highlight, large }: { label: string; value: string | number; highlight?: string; large?: boolean }) {
  const bg = highlight === 'green' ? 'bg-green-50 border-green-200' : 
             highlight === 'red' ? 'bg-red-50 border-red-200' : 
             highlight === 'blue' ? 'bg-blue-50 border-blue-200 text-blue-900' :
             'bg-slate-50 border-slate-100';
  return (
    <div className={`p-3 rounded-lg border ${bg}`}>
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      <div className={`font-bold text-slate-900 ${large ? 'text-2xl' : 'text-lg'}`}>{value}</div>
    </div>
  );
}
