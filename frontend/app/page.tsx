"use client";

import Link from "next/link";
import { Shield, Target } from "lucide-react";

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="max-w-4xl w-full">
          <div className="text-center mb-16">
            <h1 className="text-5xl md:text-6xl font-bold text-white mb-4">
              DocGuard & CareerMatch
            </h1>
            <p className="text-slate-400 text-lg">
              Choose your analysis tool
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            <Link href="/ats-checker">
              <div className="group relative bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-2xl p-12 hover:border-emerald-500 transition-all duration-300 cursor-pointer hover:shadow-2xl hover:shadow-emerald-500/20">
                <div className="flex flex-col items-center text-center">
                  <div className="w-20 h-20 bg-emerald-500/10 rounded-full flex items-center justify-center mb-6 group-hover:bg-emerald-500/20 transition-colors">
                    <Target className="w-10 h-10 text-emerald-500" />
                  </div>
                  <h2 className="text-2xl font-bold text-white mb-3">
                    ATS Score Checker
                  </h2>
                  <p className="text-slate-400">
                    Optimize your resume for applicant tracking systems
                  </p>
                </div>
              </div>
            </Link>

            <Link href="/ai-detector">
              <div className="group relative bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-2xl p-12 hover:border-blue-500 transition-all duration-300 cursor-pointer hover:shadow-2xl hover:shadow-blue-500/20">
                <div className="flex flex-col items-center text-center">
                  <div className="w-20 h-20 bg-blue-500/10 rounded-full flex items-center justify-center mb-6 group-hover:bg-blue-500/20 transition-colors">
                    <Shield className="w-10 h-10 text-blue-500" />
                  </div>
                  <h2 className="text-2xl font-bold text-white mb-3">
                    AI Detector
                  </h2>
                  <p className="text-slate-400">
                    Detect AI-generated content with forensic precision
                  </p>
                </div>
              </div>
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
