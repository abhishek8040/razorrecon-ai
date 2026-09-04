"use client";
import { useState } from "react";
import { MessageSquare, Send, CheckCircle2 } from "lucide-react";

export default function QAPage() {
  const [messages, setMessages] = useState<{role: string, content: string, tools_used?: string[]}[]>([
    { role: 'ai', content: 'Hello! I am your Finance Copilot. I can answer questions about your live reconciliation data using deterministic backend tools.' }
  ]);
  const [input, setInput] = useState("");

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    
    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";
      const res = await fetch(`${API_BASE}/qa`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userMsg }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'ai', content: data.answer || "Error processing response.", tools_used: data.tools_used }]);
    } catch (err: any) {
      setMessages(prev => [...prev, { role: 'ai', content: `Error: ${err.message}` }]);
    }
  };

  return (
    <div className="max-w-4xl mx-auto h-[calc(100vh-64px)] flex flex-col space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <MessageSquare className="w-6 h-6 text-blue-600"/> Finance Copilot
        </h2>
        <p className="text-slate-500">Ask questions about live reconciliation data.</p>
      </div>

      <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
        <div className="flex-1 p-6 overflow-y-auto space-y-4">
          {messages.map((m, i) => (
            <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-800'}`}>
                <p className="text-sm whitespace-pre-wrap">{m.content}</p>
              </div>
              {m.tools_used && m.tools_used.length > 0 && (
                <div className="mt-2 ml-2 flex flex-col gap-1">
                  <div className="flex items-center text-xs text-green-600 font-medium">
                    <CheckCircle2 className="w-3 h-3 mr-1" /> Grounded in live reconciliation data
                  </div>
                  <div className="flex flex-wrap gap-1">
                    <span className="text-[10px] text-slate-400">Sources:</span>
                    {m.tools_used.map((t, idx) => (
                      <span key={idx} className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 text-slate-500 rounded text-[10px] font-mono">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
        
        <div className="p-4 bg-white border-t border-slate-100">
          <div className="flex items-center space-x-2">
            <input 
              type="text" 
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              placeholder="E.g. What is the current exception rate?"
              className="flex-1 px-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button 
              onClick={handleSend}
              className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Send className="h-5 w-5" />
            </button>
          </div>
          <div className="mt-2 text-xs text-slate-400 flex gap-4">
             <span>Try: "How many transactions were reconciled?"</span>
             <span>"Show unresolved transactions."</span>
          </div>
        </div>
      </div>
    </div>
  );
}
