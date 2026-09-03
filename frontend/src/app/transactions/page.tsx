"use client";
import { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import { ChevronRight, CheckCircle, AlertCircle, XCircle } from "lucide-react";

export default function TransactionsPage() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<any>(null);
  const [page, setPage] = useState(1);
  const pageSize = 50;

  useEffect(() => {
    fetchApi("/transactions?limit=2000")
      .then(res => {
        setData(res);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const statusIcon = (type: string) => {
    if (!type) return <span className="text-slate-400 text-xs">Pending</span>;
    if (type.includes("MATCHED")) return <CheckCircle className="h-4 w-4 text-green-500" />;
    if (type === "UNRESOLVED") return <XCircle className="h-4 w-4 text-red-500" />;
    return <AlertCircle className="h-4 w-4 text-amber-500" />;
  };

  const statusBadge = (type: string) => {
    if (!type) return "bg-slate-100 text-slate-600";
    if (type.includes("MATCHED")) return "bg-green-100 text-green-800";
    return "bg-red-100 text-red-800";
  };

  return (
    <div className="max-w-7xl mx-auto h-[calc(100vh-64px)] flex flex-col gap-4">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Transactions</h2>
        <p className="text-slate-500 text-sm">View payments and their reconciliation lineage.</p>
      </div>

      <div className="flex-1 flex gap-4 overflow-hidden min-h-0">
        {/* Table */}
        <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
          <div className="overflow-auto flex-1">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50 sticky top-0">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Payment ID</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Time</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase">Amount</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Match</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-400 text-sm">Loading...</td></tr>
                ) : data.slice((page - 1) * pageSize, page * pageSize).map((row, i) => (
                  <tr
                    key={i}
                    onClick={() => setSelected(row)}
                    className={`hover:bg-slate-50 cursor-pointer transition-colors ${selected?.payment?.id === row.payment?.id ? 'bg-blue-50' : ''}`}
                  >
                    <td className="px-4 py-3 text-sm font-mono text-slate-800 truncate max-w-[160px]">{row.payment?.id}</td>
                    <td className="px-4 py-3 text-sm text-slate-500 whitespace-nowrap">{row.payment?.payment_time ? new Date(row.payment.payment_time).toLocaleDateString() : "—"}</td>
                    <td className="px-4 py-3 text-sm font-medium text-slate-900 text-right whitespace-nowrap">₹{Number(row.payment?.amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                    <td className="px-4 py-3 text-center">{statusIcon(row.reconciliation?.result_type)}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${statusBadge(row.reconciliation?.result_type)}`}>
                        {row.reconciliation?.result_type?.replace(/_/g, ' ') || 'PENDING'}
                      </span>
                    </td>
                    <td className="px-4 py-3"><ChevronRight className="h-4 w-4 text-slate-300" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!loading && data.length > pageSize && (
            <div className="bg-slate-50 border-t border-slate-200 px-4 py-3 flex items-center justify-between sm:px-6">
              <div className="text-sm text-slate-700">
                Showing <span className="font-medium">{(page - 1) * pageSize + 1}</span> to <span className="font-medium">{Math.min(page * pageSize, data.length)}</span> of <span className="font-medium">{data.length}</span> results
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 border border-slate-300 rounded-md text-sm font-medium bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={page * pageSize >= data.length}
                  className="px-3 py-1 border border-slate-300 rounded-md text-sm font-medium bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Detail Panel */}
        {selected && (
          <div className="w-[380px] flex-shrink-0 bg-white rounded-xl border border-slate-200 shadow-sm overflow-y-auto">
            <div className="p-5 space-y-5">
              <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Transaction Lineage</h3>

              {/* Payment */}
              <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg">
                <p className="text-xs font-bold text-blue-700 uppercase mb-2">Payment</p>
                <Detail label="ID" value={selected.payment?.id} />
                <Detail label="Amount" value={`₹${Number(selected.payment?.amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`} />
                <Detail label="Time" value={selected.payment?.payment_time ? new Date(selected.payment.payment_time).toLocaleString() : "—"} />
                <Detail label="Customer" value={selected.payment?.customer_reference || "—"} />
                <Detail label="Order" value={selected.payment?.order_reference || "—"} />
              </div>

              {/* Reconciliation */}
              {selected.reconciliation && (
                <div className={`border p-4 rounded-lg ${
                  selected.reconciliation.result_type?.includes('MATCHED') ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
                }`}>
                  <p className="text-xs font-bold uppercase mb-2" style={{ color: selected.reconciliation.result_type?.includes('MATCHED') ? '#15803d' : '#b91c1c' }}>
                    Reconciliation Result
                  </p>
                  <Detail label="Result" value={selected.reconciliation.result_type?.replace(/_/g, ' ')} />
                  <Detail label="Confidence" value={`${(selected.reconciliation.confidence * 100).toFixed(0)}%`} />
                  <Detail label="Decision" value={selected.reconciliation.decision_source} />
                  {selected.reconciliation.matched_record_id && (
                    <Detail label="Matched Settlement" value={selected.reconciliation.matched_record_id} />
                  )}
                  {selected.reconciliation.bank_transaction_id && (
                    <Detail label="Matched Bank Tx" value={selected.reconciliation.bank_transaction_id} />
                  )}
                  {selected.reconciliation.amount_difference !== null && selected.reconciliation.amount_difference !== undefined && Number(selected.reconciliation.amount_difference) !== 0 && (
                    <Detail label="Amt Diff" value={`₹${Number(selected.reconciliation.amount_difference).toFixed(2)}`} />
                  )}
                  {selected.reconciliation.amount_difference !== null && selected.reconciliation.amount_difference !== undefined && Number(selected.reconciliation.amount_difference) === 0 && (
                    <Detail label="Amt Diff" value="₹0.00" />
                  )}
                  {selected.reconciliation.time_difference_seconds && (
                    <Detail label="Time Diff" value={`${(selected.reconciliation.time_difference_seconds / 3600).toFixed(1)}h`} />
                  )}
                  {selected.reconciliation.explanation && (
                    <div className="mt-2 text-xs text-slate-600 bg-white/50 p-2 rounded">
                      <strong>Explanation:</strong> {selected.reconciliation.explanation}
                    </div>
                  )}
                </div>
              )}

              {!selected.reconciliation && (
                <div className="bg-slate-50 border border-slate-200 p-4 rounded-lg text-center text-sm text-slate-500">
                  Not yet reconciled. Run reconciliation first.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-xs py-1">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-slate-800 text-right max-w-[200px] truncate" title={value}>{value}</span>
    </div>
  );
}
