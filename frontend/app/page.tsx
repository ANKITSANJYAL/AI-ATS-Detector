"use client";

import Link from "next/link";
import { Shield, Target, Clock, ArrowRight, Sparkles, Users, BarChart3, Zap } from "lucide-react";

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Hero Section */}
      <div className="flex flex-col items-center justify-center min-h-[80vh] px-4 text-center">
        <div className="max-w-4xl w-full">
          {/* Badge */}
          <div className="inline-flex items-center px-4 py-1.5 bg-blue-500/10 border border-blue-500/30 rounded-full text-blue-400 text-sm font-medium mb-8">
            <Sparkles className="w-4 h-4 mr-2" />
            AI-Powered Document Intelligence
          </div>

          <h1 className="text-5xl md:text-7xl font-bold text-white mb-6 leading-tight">
            DocGuard &<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400">
              CareerMatch
            </span>
          </h1>

          <p className="text-slate-400 text-lg md:text-xl max-w-2xl mx-auto mb-10">
            Detect AI-generated content with forensic precision. Score your resume
            against any job description. Powered by multi-model ensemble AI.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
            <Link
              href="/sign-up"
              className="inline-flex items-center justify-center px-8 py-4 bg-blue-500 text-white rounded-lg font-semibold hover:bg-blue-600 transition-colors text-lg"
            >
              Get Started Free
              <ArrowRight className="w-5 h-5 ml-2" />
            </Link>
            <Link
              href="/pricing"
              className="inline-flex items-center justify-center px-8 py-4 bg-slate-800 text-white rounded-lg font-semibold hover:bg-slate-700 transition-colors border border-slate-700 text-lg"
            >
              View Pricing
            </Link>
          </div>

          {/* Social Proof */}
          <div className="flex items-center justify-center gap-8 text-slate-500 text-sm">
            <div className="flex items-center">
              <Users className="w-4 h-4 mr-1.5" />
              <span>1,000+ users</span>
            </div>
            <div className="flex items-center">
              <BarChart3 className="w-4 h-4 mr-1.5" />
              <span>50,000+ scans</span>
            </div>
            <div className="flex items-center">
              <Zap className="w-4 h-4 mr-1.5" />
              <span>98% accuracy</span>
            </div>
          </div>
        </div>
      </div>

      {/* Feature Cards */}
      <div className="max-w-5xl mx-auto px-4 pb-24">
        <h2 className="text-2xl font-bold text-white text-center mb-12">
          Choose Your Tool
        </h2>

        <div className="grid md:grid-cols-3 gap-8 mb-16">
          {/* ATS Score Checker */}
          <Link href="/ats-checker">
            <div className="group relative bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-2xl p-10 hover:border-emerald-500 transition-all duration-300 cursor-pointer hover:shadow-2xl hover:shadow-emerald-500/20 h-full">
              <div className="flex flex-col items-center text-center">
                <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center mb-5 group-hover:bg-emerald-500/20 transition-colors">
                  <Target className="w-8 h-8 text-emerald-500" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">
                  ATS Score Checker
                </h3>
                <p className="text-slate-400 text-sm">
                  Optimize your resume for applicant tracking systems with
                  semantic analysis
                </p>
              </div>
            </div>
          </Link>

          {/* AI Detector */}
          <Link href="/ai-detector">
            <div className="group relative bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-2xl p-10 hover:border-blue-500 transition-all duration-300 cursor-pointer hover:shadow-2xl hover:shadow-blue-500/20 h-full">
              <div className="flex flex-col items-center text-center">
                <div className="w-16 h-16 bg-blue-500/10 rounded-full flex items-center justify-center mb-5 group-hover:bg-blue-500/20 transition-colors">
                  <Shield className="w-8 h-8 text-blue-500" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">
                  AI Detector
                </h3>
                <p className="text-slate-400 text-sm">
                  Detect AI-generated content with multi-model ensemble and
                  sentence-level precision
                </p>
              </div>
            </div>
          </Link>

          {/* History */}
          <Link href="/history">
            <div className="group relative bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-2xl p-10 hover:border-purple-500 transition-all duration-300 cursor-pointer hover:shadow-2xl hover:shadow-purple-500/20 h-full">
              <div className="flex flex-col items-center text-center">
                <div className="w-16 h-16 bg-purple-500/10 rounded-full flex items-center justify-center mb-5 group-hover:bg-purple-500/20 transition-colors">
                  <Clock className="w-8 h-8 text-purple-500" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">History</h3>
                <p className="text-slate-400 text-sm">
                  View all your past analysis results and track improvements
                </p>
              </div>
            </div>
          </Link>
        </div>

        {/* Bottom CTA */}
        <div className="text-center">
          <p className="text-slate-400 mb-4">
            Ready to take your documents to the next level?
          </p>
          <Link
            href="/sign-up"
            className="inline-flex items-center px-6 py-3 bg-blue-500/10 text-blue-400 rounded-lg font-semibold hover:bg-blue-500/20 transition-colors border border-blue-500/30"
          >
            Start Free Trial — No Credit Card Required
            <ArrowRight className="w-4 h-4 ml-2" />
          </Link>
        </div>
      </div>
    </main>
  );
}
