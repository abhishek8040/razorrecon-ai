"use client";
import React from "react";
import { BookOpen, ShieldCheck, BrainCircuit, Search, Database, ArrowRight, Server, FileSearch } from "lucide-react";

export default function AboutPage() {
  return (
    <div className="max-w-5xl mx-auto space-y-10">
      
      {/* Header */}
      <div className="border-b border-slate-200 pb-6">
        <h1 className="text-3xl font-bold text-slate-900 flex items-center">
          <BookOpen className="w-8 h-8 mr-3 text-blue-600" />
          About RazorRecon AI
        </h1>
        <p className="mt-2 text-slate-500 text-lg">
          AI investigates. Deterministic financial controls decide.
        </p>
      </div>

      {/* The Problem Section */}
      <section className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm">
        <h2 className="text-2xl font-bold text-slate-800 mb-4">1. The Problem</h2>
        <p className="text-slate-600 mb-6 leading-relaxed">
          In the fintech world, <strong>reconciliation</strong> is the process of proving that the money a customer paid actually landed in your bank account. It is a messy, three-way problem:
        </p>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
          <div className="p-4 bg-slate-50 rounded-lg border border-slate-100">
            <h3 className="font-bold text-slate-700 mb-2">1. Payment</h3>
            <p className="text-sm text-slate-500">The customer clicks "Buy". You record a ₹1,000 sale.</p>
          </div>
          <div className="p-4 bg-slate-50 rounded-lg border border-slate-100">
            <h3 className="font-bold text-slate-700 mb-2">2. Settlement</h3>
            <p className="text-sm text-slate-500">The payment gateway (like Razorpay) processes it and takes a ₹20 fee.</p>
          </div>
          <div className="p-4 bg-slate-50 rounded-lg border border-slate-100">
            <h3 className="font-bold text-slate-700 mb-2">3. Bank Deposit</h3>
            <p className="text-sm text-slate-500">The bank deposits ₹980 into your account 3 days later.</p>
          </div>
        </div>

        <p className="mt-6 text-slate-600 leading-relaxed">
          Finance teams spend hundreds of hours manually hunting for these matches in spreadsheets, dealing with missing references, delayed bank payouts, and unpredictable fees.
        </p>
      </section>

      {/* The Solution Section */}
      <section className="bg-blue-50/50 p-8 rounded-xl border border-blue-100">
        <h2 className="text-2xl font-bold text-blue-900 mb-4">2. Our Solution</h2>
        <p className="text-blue-800 mb-8 leading-relaxed">
          RazorRecon AI automates this entire pipeline using a hybrid approach: a strict, mathematically precise rules engine handles the math, while a generative AI copilot explains the anomalies.
        </p>

        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          
          <div className="flex-1 bg-white p-6 rounded-xl border border-blue-100 shadow-sm text-center relative z-10 w-full">
            <Database className="w-10 h-10 mx-auto text-blue-500 mb-3" />
            <h4 className="font-bold text-slate-800">Raw Data</h4>
            <p className="text-xs text-slate-500 mt-1">Payments, Settlements, Banks</p>
          </div>

          <ArrowRight className="text-blue-300 hidden md:block w-8 h-8 flex-shrink-0" />

          <div className="flex-1 bg-white p-6 rounded-xl border border-emerald-200 shadow-sm text-center relative z-10 border-t-4 border-t-emerald-500 w-full">
            <Server className="w-10 h-10 mx-auto text-emerald-500 mb-3" />
            <h4 className="font-bold text-slate-800">Deterministic Engine</h4>
            <p className="text-xs text-slate-500 mt-1">Strict matching & math</p>
          </div>

          <ArrowRight className="text-blue-300 hidden md:block w-8 h-8 flex-shrink-0" />

          <div className="flex-1 bg-white p-6 rounded-xl border border-purple-200 shadow-sm text-center relative z-10 border-t-4 border-t-purple-500 w-full">
            <FileSearch className="w-10 h-10 mx-auto text-purple-500 mb-3" />
            <h4 className="font-bold text-slate-800">Exceptions</h4>
            <p className="text-xs text-slate-500 mt-1">Isolated anomalies</p>
          </div>

          <ArrowRight className="text-blue-300 hidden md:block w-8 h-8 flex-shrink-0" />

          <div className="flex-1 bg-white p-6 rounded-xl border border-orange-200 shadow-sm text-center relative z-10 border-t-4 border-t-orange-500 w-full">
            <BrainCircuit className="w-10 h-10 mx-auto text-orange-500 mb-3" />
            <h4 className="font-bold text-slate-800">AI Copilot</h4>
            <p className="text-xs text-slate-500 mt-1">Human-friendly insights</p>
          </div>

        </div>
      </section>

      {/* Why Not Pure AI? Section */}
      <section className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm">
        <h2 className="text-2xl font-bold text-slate-800 mb-4 flex items-center">
          <ShieldCheck className="w-6 h-6 mr-2 text-emerald-600" />
          3. Why Not "Just Use AI"?
        </h2>
        <p className="text-slate-600 mb-4 leading-relaxed">
          Large Language Models (like Gemini or ChatGPT) are incredible at summarizing text, but they are notoriously bad at math, and they occasionally hallucinate facts. 
        </p>
        <p className="text-slate-600 mb-6 leading-relaxed font-medium">
          In financial software, a hallucination is unacceptable. You cannot let an AI "guess" where ₹10,000 went.
        </p>
        
        <div className="bg-slate-50 rounded-lg p-6 border border-slate-200">
          <h3 className="font-bold text-slate-800 mb-3">Our Tool-Grounded Safety Architecture:</h3>
          <ul className="space-y-3 text-sm text-slate-600">
            <li className="flex items-start">
              <span className="text-emerald-500 mr-2">✓</span>
              <span><strong>Read-Only Copilot:</strong> The AI has absolutely no permission to modify the database. It cannot "resolve" a transaction.</span>
            </li>
            <li className="flex items-start">
              <span className="text-emerald-500 mr-2">✓</span>
              <span><strong>Tool-Grounded Answers:</strong> The AI doesn't calculate metrics itself. It asks the backend for metrics using restricted tools, then simply formats the answer for the user in plain English.</span>
            </li>
            <li className="flex items-start">
              <span className="text-emerald-500 mr-2">✓</span>
              <span><strong>Ambiguity Thresholds:</strong> If two bank transactions look identical, the math engine flags them as "Ambiguous" and stops. It forces a human to review, ensuring complete financial integrity.</span>
            </li>
          </ul>
        </div>
      </section>

      <div className="pb-10"></div>
    </div>
  );
}
