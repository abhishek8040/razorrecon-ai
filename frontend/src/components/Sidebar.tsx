"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, FileSpreadsheet, AlertCircle, FileText, CheckCircle, Activity, MessageSquare, UploadCloud, BookOpen } from "lucide-react";

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

  return (
    <div className="flex h-full w-64 flex-col bg-slate-900 text-white flex-shrink-0">
      <div className="flex h-16 items-center border-b border-slate-800 px-6">
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
  );
}
