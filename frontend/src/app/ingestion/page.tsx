"use client";
import { useState } from "react";
import { UploadCloud, FileText, CheckCircle, AlertCircle } from "lucide-react";

export default function IngestionPage() {
  const [file, setFile] = useState<File | null>(null);
  const [dataType, setDataType] = useState("payment");
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<{type: 'success'|'error', text: string} | null>(null);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setMessage(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("data_type", dataType);

    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";
      const res = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (res.ok) {
        setMessage({ type: "success", text: data.message });
        setFile(null);
      } else {
        setMessage({ type: "error", text: data.detail || "Upload failed" });
      }
    } catch (err: any) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Data Ingestion</h2>
        <p className="text-slate-500">Upload CSV files for payments, settlements, or bank transactions.</p>
      </div>

      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <form onSubmit={handleUpload} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Record Type</label>
            <select 
              value={dataType} 
              onChange={e => setDataType(e.target.value)}
              className="w-full md:w-1/3 p-2 border border-slate-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="payment">Payments</option>
              <option value="settlement">Settlements</option>
              <option value="bank">Bank Transactions</option>
            </select>
          </div>

          <div className="border-2 border-dashed border-slate-300 rounded-lg p-10 flex flex-col items-center justify-center bg-slate-50 hover:bg-slate-100 transition-colors">
            <UploadCloud className="h-12 w-12 text-slate-400 mb-4" />
            <p className="text-slate-600 font-medium">Click to select a CSV file to upload</p>
            <input 
              type="file" 
              accept=".csv" 
              onChange={e => setFile(e.target.files?.[0] || null)}
              className="mt-4 text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
          </div>

          {file && (
            <div className="flex items-center text-sm text-slate-600 bg-blue-50 p-3 rounded-md">
              <FileText className="h-4 w-4 mr-2 text-blue-500" />
              Selected: <span className="font-semibold ml-1">{file.name}</span> ({(file.size / 1024).toFixed(1)} KB)
            </div>
          )}

          {message && (
            <div className={`p-4 rounded-md flex items-start ${message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
              {message.type === 'success' ? <CheckCircle className="h-5 w-5 mr-2 flex-shrink-0" /> : <AlertCircle className="h-5 w-5 mr-2 flex-shrink-0" />}
              <span>{message.text}</span>
            </div>
          )}

          <button 
            type="submit" 
            disabled={!file || uploading}
            className="px-6 py-2 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {uploading ? 'Uploading...' : 'Upload Data'}
          </button>
        </form>
      </div>
    </div>
  );
}
