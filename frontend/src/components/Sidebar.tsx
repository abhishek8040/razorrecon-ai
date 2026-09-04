"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { LayoutDashboard, FileSpreadsheet, AlertCircle, FileText, CheckCircle, Activity, MessageSquare, UploadCloud, BookOpen, Menu, X } from "lucide-react";

const navItems = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "About", href: "/about", icon: BookOpen },
  { name: "Reconciliation", href: "/reconciliation", icon: FileSpreadsheet },
  { name: "Exceptions", href: "/exceptions", icon: AlertCircle },
  { name: "Transactions", href: "/transactions", icon: FileText },
  { name: "Evaluations", href: "/evaluations", icon: CheckCircle },
  { name: "Audit Trail", href: "/audit", icon: Activity },
  { name: "Finance Q&A", href: "/qa", icon: MessageSquare },
  { name: "Data Ingestion", href: "/ingestion", icon: UploadCloud },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Mobile Top Bar */}
      <div className="md:hidden flex h-16 items-center justify-between bg-slate-900 px-4 text-white flex-shrink-0 z-50">
        <h1 className="text-xl font-bold tracking-tight">
          <span className="text-blue-400">Razor</span><span className="text-emerald-400">Recon</span> <span className="text-white/80 text-sm font-medium">AI</span>
        </h1>
        <button onClick={() => setIsOpen(!isOpen)} className="text-slate-300 hover:text-white p-2">
          {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Sidebar (Mobile Dropdown or Desktop Fixed) */}
      <div className={`${isOpen ? 'flex' : 'hidden'} md:flex absolute md:relative top-16 md:top-0 z-40 h-[calc(100vh-4rem)] md:h-full w-full md:w-64 flex-col bg-slate-900 text-white flex-shrink-0 border-t md:border-t-0 border-slate-800 transition-all duration-200`}>
        <div className="hidden md:flex h-16 items-center border-b border-slate-800 px-6">
          <h1 className="text-xl font-bold tracking-tight">
            <span className="text-blue-400">Razor</span><span className="text-emerald-400">Recon</span> <span className="text-white/80 text-sm font-medium">AI</span>
          </h1>
        </div>
        <div className="flex-1 overflow-y-auto py-4">
          <nav className="space-y-1 px-3">
            {navItems.map((item) => {
              const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={() => setIsOpen(false)}
                  className={`flex items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150 ${
                    isActive
                      ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                      : "text-slate-400 hover:bg-slate-800 hover:text-white border border-transparent"
                  }`}
                >
                  <item.icon className={`mr-3 h-[18px] w-[18px] flex-shrink-0 ${isActive ? "text-blue-400" : "text-slate-500"}`} />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="border-t border-slate-800 p-4 text-xs text-slate-500 text-center">
          RazorRecon AI v1.0 — Razorpay Buildathon 2026
        </div>
      </div>
    </>
  );
}
