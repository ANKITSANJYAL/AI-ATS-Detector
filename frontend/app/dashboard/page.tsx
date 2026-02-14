"use client";

import Link from "next/link";
import { FileText, Target } from "lucide-react";

export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="max-w-4xl mx-auto px-4 py-16">
        <h1 className="text-4xl font-bold text-white mb-4">Dashboard</h1>
        <p className="text-slate-400 mb-12">Choose a tool to get started</p>

        <div className="grid md:grid-cols-2 gap-8">
          <Link
            href="/ai-detector"
            className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8 hover:border-blue-500/50 transition-colors group"
          >
            <FileText className="w-10 h-10 text-blue-400 mb-4 group-hover:scale-110 transition-transform" />
            <h2 className="text-2xl font-bold text-white mb-2">AI Detector</h2>
            <p className="text-slate-400">
              Analyze documents to detect AI-generated content with sentence-level
              precision.
            </p>
          </Link>

          <Link
            href="/ats-checker"
            className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8 hover:border-emerald-500/50 transition-colors group"
          >
            <Target className="w-10 h-10 text-emerald-400 mb-4 group-hover:scale-110 transition-transform" />
            <h2 className="text-2xl font-bold text-white mb-2">ATS Checker</h2>
            <p className="text-slate-400">
              Score your resume against a job description for ATS compatibility.
            </p>
          </Link>
        </div>
      </div>
    </main>
  );
}
