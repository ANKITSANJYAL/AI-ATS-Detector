"use client";

import { useState } from "react";
import { ArrowLeft, Target, TrendingUp } from "lucide-react";

interface ATSResultsProps {
  results: any;
  onReset: () => void;
}

export default function ATSResults({ results, onReset }: ATSResultsProps) {
  const [activeTab, setActiveTab] = useState<"score" | "recommendations">("score");

  // Calculate score percentage
  const score = Math.round(results.overall_score || 0);

  return (
    <main className="min-h-screen bg-gradient-to-br from-emerald-900 via-slate-900 to-slate-900">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <button
          onClick={onReset}
          className="inline-flex items-center text-emerald-400 hover:text-emerald-300 mb-8"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          New Analysis
        </button>

        <h1 className="text-4xl font-bold text-white mb-12">ATS Analysis Results</h1>

        {/* Tabs */}
        <div className="flex space-x-4 mb-8 border-b border-slate-700">
          <button
            onClick={() => setActiveTab("score")}
            className={`px-6 py-3 font-semibold transition-colors ${
              activeTab === "score"
                ? "text-emerald-400 border-b-2 border-emerald-400"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Target className="w-5 h-5 inline-block mr-2" />
            ATS Score
          </button>
          <button
            onClick={() => setActiveTab("recommendations")}
            className={`px-6 py-3 font-semibold transition-colors ${
              activeTab === "recommendations"
                ? "text-emerald-400 border-b-2 border-emerald-400"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <TrendingUp className="w-5 h-5 inline-block mr-2" />
            Recommendations
          </button>
        </div>

        {/* Score Tab */}
        {activeTab === "score" && (
          <div className="space-y-8">
            {/* Clock-style Score Display */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-12">
              <div className="flex flex-col items-center">
                <div className="relative w-64 h-64">
                  {/* Circular Progress */}
                  <svg className="transform -rotate-90 w-64 h-64">
                    <circle
                      cx="128"
                      cy="128"
                      r="120"
                      stroke="currentColor"
                      strokeWidth="16"
                      fill="transparent"
                      className="text-slate-700"
                    />
                    <circle
                      cx="128"
                      cy="128"
                      r="120"
                      stroke="currentColor"
                      strokeWidth="16"
                      fill="transparent"
                      strokeDasharray={`${2 * Math.PI * 120}`}
                      strokeDashoffset={`${2 * Math.PI * 120 * (1 - score / 100)}`}
                      className="text-emerald-500 transition-all duration-1000 ease-out"
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-6xl font-bold text-white">{score}</span>
                    <span className="text-2xl text-slate-400">/ 100</span>
                  </div>
                </div>
                <h2 className="text-2xl font-bold text-white mt-8">
                  {score >= 80 ? "Excellent Match!" : score >= 60 ? "Good Match" : "Needs Improvement"}
                </h2>
                <p className="text-slate-400 mt-2 text-center max-w-md">
                  {results.explanation || "Your resume has been analyzed for ATS compatibility"}
                </p>
              </div>
            </div>

            {/* Skills Analysis */}
            <div className="grid md:grid-cols-2 gap-8">
              {/* Matched Skills */}
              <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8">
                <h3 className="text-xl font-bold text-emerald-400 mb-6">
                  ✓ Matched Skills ({results.skill_matches?.filter((s: any) => s.matched).length || results.matched_skills?.length || 0})
                </h3>
                <div className="space-y-3">
                  {(results.skill_matches
                    ? results.skill_matches.filter((s: any) => s.matched).map((s: any) => ({
                        name: s.skill,
                        relevance: s.relevance ?? 1,
                      }))
                    : (results.matched_skills || []).map((skill: string) => ({
                        name: skill,
                        relevance: 1,
                      }))
                  ).map((item: { name: string; relevance: number }, index: number) => (
                    <div key={index} className="flex items-center">
                      <div className="w-full bg-slate-700 rounded-full h-8">
                        <div
                          className="bg-emerald-500 h-8 rounded-full flex items-center px-4"
                          style={{ width: `${Math.max(40, Math.round(item.relevance * 100))}%` }}
                        >
                          <span className="text-white text-sm font-medium truncate">{item.name}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                  {(!results.skill_matches || results.skill_matches.filter((s: any) => s.matched).length === 0) &&
                   (!results.matched_skills || results.matched_skills.length === 0) && (
                    <p className="text-slate-500">No skills data available</p>
                  )}
                </div>
              </div>

              {/* Missing Skills */}
              <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8">
                <h3 className="text-xl font-bold text-red-400 mb-6">
                  ✗ Missing Skills ({results.gap_analysis?.missing_required_skills?.length || results.missing_skills?.length || 0})
                </h3>
                <div className="space-y-3">
                  {(results.gap_analysis?.missing_required_skills || results.missing_skills || []).map((skill: string, index: number) => (
                    <div key={index} className="flex items-center">
                      <div className="w-full bg-slate-700 rounded-full h-8">
                        <div
                          className="bg-red-500/50 h-8 rounded-full flex items-center px-4"
                          style={{ width: "100%" }}
                        >
                          <span className="text-white text-sm font-medium">{skill}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                  {(!results.missing_skills || results.missing_skills.length === 0) &&
               (!results.gap_analysis?.missing_required_skills || results.gap_analysis.missing_required_skills.length === 0) && (
                    <p className="text-slate-500">No missing skills identified</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Recommendations Tab */}
        {activeTab === "recommendations" && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6">
              How to Improve Your ATS Score
            </h2>
            <div className="space-y-6">
              {(results.gap_analysis?.recommendations || results.recommendations || []).map((rec: string, index: number) => (
                <div key={index} className="flex items-start space-x-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-emerald-500/20 rounded-full flex items-center justify-center">
                    <span className="text-emerald-400 font-bold">{index + 1}</span>
                  </div>
                  <div className="flex-1">
                    <p className="text-slate-300 leading-relaxed">{rec}</p>
                  </div>
                </div>
              ))}
              {(!results.recommendations || results.recommendations.length === 0) &&
               (!results.gap_analysis?.recommendations || results.gap_analysis.recommendations.length === 0) && (
                <p className="text-slate-500">No recommendations available at this time</p>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
