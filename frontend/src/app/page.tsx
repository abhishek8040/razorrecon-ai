"use client";
import { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import { Activity, AlertCircle, FileSpreadsheet, TrendingUp, CheckCircle, Clock, Zap, ShieldCheck } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

export default function Dashboard() {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchApi("/metrics")
      .then(data => {
        setMetrics(data);
        setLoading(false);
      })
      .catch(err => {
        setError("Failed to load metrics. Is the backend running?");
        setLoading(false);
      });
  }, []);

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-pulse text-slate-400 flex items-center gap-2">
        <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" />
        <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:0.1s]" />
        <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:0.2s]" />
        <span className="ml-2">Loading dashboard...</span>
      </div>
    </div>
  );

  if (error) return (
    <div className="max-w-2xl mx-auto mt-20 p-6 bg-red-50 border border-red-200 rounded-xl text-center">
      <AlertCircle className="h-10 w-10 text-red-400 mx-auto mb-3" />
      <h3 className="font-semibold text-red-800 mb-1">Connection Error</h3>
      <p className="text-red-600 text-sm">{error}</p>
    </div>
  );

  const run = metrics?.latest_run;
  const eval_ = metrics?.latest_eval;
  const autoMatchRate = run ? ((run.auto_matched / run.total_records) * 100).toFixed(1) : "—";
  const exceptionRate = metrics?.exception_rate ? (metrics.exception_rate * 100).toFixed(1) : (run ? ((run.escalated / run.total_records) * 100).toFixed(1) : "—");

  const chartData = run ? [
    { name: 'Auto-Matched', value: run.auto_matched, fill: '#22c55e' },
    { name: 'Fee-Adjusted', value: (run.total_records - run.auto_matched - run.unresolved - run.escalated) || 0, fill: '#3b82f6' },
    { name: 'Exceptions', value: run.escalated, fill: '#ef4444' },
    { name: 'Unresolved', value: run.unresolved, fill: '#f59e0b' },
  ].filter(d => d.value > 0) : [];

  const pieColors = ['#22c55e', '#3b82f6', '#ef4444', '#f59e0b'];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Dashboard</h2>
          <p className="text-slate-500 text-sm">Financial reconciliation overview — all metrics computed from live data.</p>
        </div>
        {run && (
          <span className="text-xs bg-slate-100 text-slate-600 px-3 py-1.5 rounded-full font-medium">
            Last run: {new Date(run.created_at).toLocaleString()}
          </span>
        )}
      </div>

      {/* Primary Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard title="Total Payments" value={metrics?.total_payments?.toLocaleString() || 0} icon={<FileSpreadsheet className="h-5 w-5" />} color="blue" />
        <MetricCard title="Total Value" value={`₹${((metrics?.total_value || 0) / 100000).toFixed(1)}L`} icon={<TrendingUp className="h-5 w-5" />} color="emerald" />
        <MetricCard title="Auto-Match Rate" value={`${autoMatchRate}%`} icon={<Zap className="h-5 w-5" />} color="green" />
        <MetricCard title="Verified Precision" value={eval_ ? `${(eval_.precision * 100).toFixed(1)}%` : "—"} icon={<ShieldCheck className="h-5 w-5" />} color="purple" />
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard title="Open Exceptions" value={run?.escalated || 0} icon={<AlertCircle className="h-5 w-5" />} color="red" />
        <MetricCard title="Unresolved" value={run?.unresolved || 0} icon={<AlertCircle className="h-5 w-5" />} color="amber" />
        <MetricCard title="Processing Time" value={run?.processing_time_ms ? `${(run.processing_time_ms / 1000).toFixed(1)}s` : "—"} icon={<Clock className="h-5 w-5" />} color="slate" />
        <MetricCard title="Records/sec" value={metrics?.records_per_second ? metrics.records_per_second.toFixed(0) : "—"} icon={<Activity className="h-5 w-5" />} color="indigo" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-4">Reconciliation Outcomes</h3>
          <div className="h-64">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} barSize={40}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(value: any) => [Number(value).toLocaleString(), "Records"]} />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                    {chartData.map((entry, i) => (
                      <Cell key={i} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-400">
                <div className="text-center">
                  <Activity className="h-10 w-10 mx-auto mb-2 text-slate-300" />
                  <p>No reconciliation runs yet.</p>
                  <a href="/reconciliation" className="text-blue-500 text-sm mt-1 inline-block hover:underline">Run your first reconciliation →</a>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-4">Exception Breakdown</h3>
          <div className="h-64">
            {metrics?.exception_breakdown && Object.keys(metrics.exception_breakdown).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(metrics.exception_breakdown).sort((a: any, b: any) => b[1] - a[1]).map(([type, count]: [string, any]) => (
                  <div key={type} className="flex items-center gap-3">
                    <span className="text-xs font-mono text-slate-600 w-44 truncate" title={type}>{type}</span>
                    <div className="flex-1 bg-slate-100 rounded-full h-5 overflow-hidden">
                      <div
                        className="bg-red-400 h-full rounded-full transition-all duration-500"
                        style={{ width: `${Math.max(5, (count / (run?.escalated || 1)) * 100)}%` }}
                      />
                    </div>
                    <span className="text-sm font-semibold text-slate-700 w-10 text-right">{count}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-400 text-center">
                <div>
                  <CheckCircle className="h-10 w-10 mx-auto mb-2 text-slate-300" />
                  <p>No exceptions to display.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <a href="/reconciliation" className="block p-4 border border-blue-100 bg-blue-50/50 rounded-lg hover:bg-blue-100/50 transition-colors group">
            <div className="flex items-center">
              <Activity className="h-5 w-5 text-blue-600 mr-3 group-hover:scale-110 transition-transform" />
              <div>
                <h4 className="font-semibold text-blue-900 text-sm">Run Reconciliation</h4>
                <p className="text-xs text-blue-600">Process payments & settlements</p>
              </div>
            </div>
          </a>
          <a href="/exceptions" className="block p-4 border border-red-100 bg-red-50/50 rounded-lg hover:bg-red-100/50 transition-colors group">
            <div className="flex items-center">
              <AlertCircle className="h-5 w-5 text-red-600 mr-3 group-hover:scale-110 transition-transform" />
              <div>
                <h4 className="font-semibold text-red-900 text-sm">Review Exceptions</h4>
                <p className="text-xs text-red-600">{run?.escalated || 0} cases need attention</p>
              </div>
            </div>
          </a>
          <a href="/evaluations" className="block p-4 border border-purple-100 bg-purple-50/50 rounded-lg hover:bg-purple-100/50 transition-colors group">
            <div className="flex items-center">
              <CheckCircle className="h-5 w-5 text-purple-600 mr-3 group-hover:scale-110 transition-transform" />
              <div>
                <h4 className="font-semibold text-purple-900 text-sm">View Evaluation</h4>
                <p className="text-xs text-purple-600">Verify accuracy metrics</p>
              </div>
            </div>
          </a>
        </div>
      </div>
    </div>
  );
}

const colorMap: Record<string, string> = {
  blue: "bg-blue-50 text-blue-600",
  emerald: "bg-emerald-50 text-emerald-600",
  green: "bg-green-50 text-green-600",
  purple: "bg-purple-50 text-purple-600",
  red: "bg-red-50 text-red-600",
  amber: "bg-amber-50 text-amber-600",
  slate: "bg-slate-100 text-slate-600",
  indigo: "bg-indigo-50 text-indigo-600",
};

function MetricCard({ title, value, icon, color }: { title: string; value: string | number; icon: React.ReactNode; color: string }) {
  return (
    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-3">
        <div className={`p-2 rounded-lg ${colorMap[color] || colorMap.blue}`}>
          {icon}
        </div>
      </div>
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{title}</p>
      <p className="text-2xl font-bold text-slate-900 mt-0.5">{value}</p>
    </div>
  );
}
