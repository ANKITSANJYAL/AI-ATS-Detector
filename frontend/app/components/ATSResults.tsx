"use client";

import { useState, useMemo } from "react";
import { ArrowLeft, Target, TrendingUp, BarChart3, Shield, Loader2, Download } from "lucide-react";
import AIDetectorResults from "./AIDetectorResults";
import { exportATSCSV } from "../lib/export";
import { config } from "../lib/config";

interface ATSResultsProps {
  results: any;
  onReset: () => void;
}

/** Radar chart drawn with pure SVG — no dependencies */
function RadarChart({ scores }: { scores: { label: string; value: number; color: string }[] }) {
  const cx = 150;
  const cy = 150;
  const radius = 110;
  const levels = 4; // concentric rings
  const n = scores.length;

  const angleSlice = (2 * Math.PI) / n;

  /** Convert (index, fraction 0-1) to SVG point */
  const point = (i: number, frac: number) => ({
    x: cx + radius * frac * Math.cos(angleSlice * i - Math.PI / 2),
    y: cy + radius * frac * Math.sin(angleSlice * i - Math.PI / 2),
  });

  // Build the polygon path for the data values
  const dataPoints = scores.map((s, i) => point(i, s.value / 100));
  const dataPath = dataPoints.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ") + " Z";

  return (
    <svg viewBox="0 0 300 300" className="w-full max-w-[320px] mx-auto">
      {/* Concentric level rings */}
      {Array.from({ length: levels }, (_, li) => {
        const frac = (li + 1) / levels;
        const pts = scores.map((_, i) => point(i, frac));
        const d = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ") + " Z";
        return <path key={li} d={d} fill="none" stroke="rgb(71 85 105 / 0.5)" strokeWidth="1" />;
      })}

      {/* Axis lines */}
      {scores.map((_, i) => {
        const p = point(i, 1);
        return <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="rgb(71 85 105 / 0.4)" strokeWidth="1" />;
      })}

      {/* Data polygon */}
      <path d={dataPath} fill="rgb(16 185 129 / 0.20)" stroke="rgb(16 185 129)" strokeWidth="2" />

      {/* Data dots + labels */}
      {scores.map((s, i) => {
        const dp = dataPoints[i];
        const lp = point(i, 1.18);
        return (
          <g key={i}>
            <circle cx={dp.x} cy={dp.y} r="4" fill={s.color} />
            <text
              x={lp.x}
              y={lp.y}
              textAnchor="middle"
              dominantBaseline="middle"
              className="fill-slate-300 text-[10px] font-medium"
            >
              {s.label}
            </text>
            <text
              x={dp.x}
              y={dp.y - 10}
              textAnchor="middle"
              className="fill-white text-[10px] font-bold"
            >
              {Math.round(s.value)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/** Horizontal bar for one sub-score */
function SubScoreBar({ label, value, weight, color }: { label: string; value: number; weight: string; color: string }) {
  const pct = Math.round(value);
  return (
    <div>
      <div className="flex justify-between items-baseline mb-1.5">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-slate-200">{label}</span>
          <span className="text-xs text-slate-500">({weight})</span>
        </div>
        <span className="text-sm font-bold text-white">{pct}/100</span>
      </div>
      <div className="w-full bg-slate-700 rounded-full h-3">
        <div
          className="h-3 rounded-full transition-all duration-700 ease-out"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

export default function ATSResults({ results, onReset }: ATSResultsProps) {
  const [activeTab, setActiveTab] = useState<"score" | "breakdown" | "recommendations">("score");
  const [aiCheckLoading, setAiCheckLoading] = useState(false);
  const [aiCheckResults, setAiCheckResults] = useState<any>(null);
  const [aiCheckError, setAiCheckError] = useState("");

  // Calculate score percentage
  const score = Math.round(results.overall_score || 0);

  // Sub-scores from backend
  const subScores = useMemo(() => {
    const semantic = results.semantic_similarity_score ?? 0;
    const keyword = results.keyword_match_score ?? 0;
    const format = results.format_score ?? 0;
    // Skill match percentage — derive from skill_matches array
    const matches = results.skill_matches || [];
    const matched = matches.filter((s: any) => s.matched).length;
    const skill = matches.length > 0 ? (matched / matches.length) * 100 : 50;

    return { semantic, keyword, format, skill };
  }, [results]);

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

        <h1 className="text-4xl font-bold text-white mb-12 flex items-center justify-between">
          <span>ATS Analysis Results</span>
          <button
            onClick={() => exportATSCSV(results)}
            className="inline-flex items-center px-3 py-2 text-sm bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 transition-colors font-normal"
          >
            <Download className="w-4 h-4 mr-1.5" />
            Export CSV
          </button>
        </h1>

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
            onClick={() => setActiveTab("breakdown")}
            className={`px-6 py-3 font-semibold transition-colors ${
              activeTab === "breakdown"
                ? "text-emerald-400 border-b-2 border-emerald-400"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <BarChart3 className="w-5 h-5 inline-block mr-2" />
            Score Breakdown
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

        {/* Score Breakdown Tab */}
        {activeTab === "breakdown" && (
          <div className="space-y-8">
            <div className="grid md:grid-cols-2 gap-8">
              {/* Radar Chart */}
              <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8">
                <h3 className="text-xl font-bold text-white mb-6">Score Radar</h3>
                <RadarChart
                  scores={[
                    { label: "Semantic", value: subScores.semantic, color: "#6366f1" },
                    { label: "Keywords", value: subScores.keyword, color: "#f59e0b" },
                    { label: "Format", value: subScores.format, color: "#06b6d4" },
                    { label: "Skills", value: subScores.skill, color: "#10b981" },
                  ]}
                />
              </div>

              {/* Sub-Score Bars */}
              <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8">
                <h3 className="text-xl font-bold text-white mb-6">Component Scores</h3>
                <div className="space-y-6">
                  <SubScoreBar label="Semantic Similarity" value={subScores.semantic} weight="30%" color="#6366f1" />
                  <SubScoreBar label="Keyword Match" value={subScores.keyword} weight="30%" color="#f59e0b" />
                  <SubScoreBar label="Resume Format" value={subScores.format} weight="20%" color="#06b6d4" />
                  <SubScoreBar label="Skills Match" value={subScores.skill} weight="20%" color="#10b981" />
                </div>

                {/* Weighted formula explanation */}
                <div className="mt-8 p-4 bg-slate-900/50 rounded-lg border border-slate-700">
                  <p className="text-xs text-slate-500 leading-relaxed">
                    <span className="font-semibold text-slate-400">How it is calculated: </span>
                    Overall = Semantic (30%) + Keywords (30%) + Format (20%) + Skills (20%).
                    Semantic similarity uses embedding cosine distance between your resume
                    and the job description. Keyword match counts shared technical terms.
                    Format checks for standard sections, dates, and contact info.
                    Skills match verifies extracted skills against your resume text.
                  </p>
                </div>
              </div>
            </div>

            {/* Score interpretation */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8">
              <h3 className="text-xl font-bold text-white mb-4">What Each Score Means</h3>
              <div className="grid md:grid-cols-2 gap-6">
                {[
                  {
                    title: "Semantic Similarity",
                    score: subScores.semantic,
                    color: "#6366f1",
                    desc: "How closely your resume's meaning aligns with the job description, measured by AI embedding similarity.",
                    tip: subScores.semantic < 60
                      ? "Tailor your summary and experience bullets to echo the job's language and responsibilities."
                      : "Good alignment. Keep using relevant terminology from the job posting.",
                  },
                  {
                    title: "Keyword Match",
                    score: subScores.keyword,
                    color: "#f59e0b",
                    desc: "Percentage of important technical terms from the job posting found in your resume.",
                    tip: subScores.keyword < 60
                      ? "Add missing keywords naturally into your experience and skills sections."
                      : "Solid keyword coverage. Ensure they appear in context, not just listed.",
                  },
                  {
                    title: "Resume Format",
                    score: subScores.format,
                    color: "#06b6d4",
                    desc: "Checks for standard ATS-readable sections like Experience, Education, Skills, contact info, and dates.",
                    tip: subScores.format < 60
                      ? "Add clearly labeled sections (Experience, Education, Skills) and include dates and contact details."
                      : "Your format is ATS-friendly. Avoid graphics and multi-column layouts.",
                  },
                  {
                    title: "Skills Match",
                    score: subScores.skill,
                    color: "#10b981",
                    desc: "How many of the extracted required and preferred skills appear in your resume.",
                    tip: subScores.skill < 60
                      ? "Review the missing skills list and add relevant ones you genuinely possess."
                      : "Strong skills match. Consider adding quantified achievements for each skill.",
                  },
                ].map((item, i) => (
                  <div key={i} className="p-4 bg-slate-900/40 rounded-lg border border-slate-700">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                      <span className="font-semibold text-white text-sm">{item.title}</span>
                      <span className="ml-auto text-sm font-bold" style={{ color: item.color }}>
                        {Math.round(item.score)}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mb-2">{item.desc}</p>
                    <p className="text-xs text-emerald-400/80 italic">{item.tip}</p>
                  </div>
                ))}
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

        {/* Cross-Pipeline: AI Check */}
        {!aiCheckResults && (
          <div className="mt-10 bg-slate-800/50 border border-slate-700 rounded-2xl p-8 text-center">
            <Shield className="w-10 h-10 text-blue-400 mx-auto mb-4" />
            <h3 className="text-xl font-bold text-white mb-2">
              Does your resume contain AI-generated content?
            </h3>
            <p className="text-slate-400 mb-6 max-w-md mx-auto text-sm">
              Run the same resume through our AI detector to make sure
              it reads as authentically human before submitting.
            </p>
            {aiCheckError && (
              <p className="text-red-400 text-sm mb-4">{aiCheckError}</p>
            )}
            <button
              onClick={async () => {
                if (!results.document_id) return;
                setAiCheckLoading(true);
                setAiCheckError("");
                try {
                  const res = await fetch(`${config.apiV1}/documents/detect`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ document_id: results.document_id }),
                  });
                  if (!res.ok) throw new Error("Detection failed");
                  const data = await res.json();
                  setAiCheckResults(data);
                } catch (err: any) {
                  setAiCheckError(err.message || "Failed to run AI detection");
                } finally {
                  setAiCheckLoading(false);
                }
              }}
              disabled={aiCheckLoading}
              className="px-8 py-3 bg-blue-500 text-white rounded-lg font-semibold hover:bg-blue-600 transition-colors disabled:bg-slate-700 disabled:cursor-not-allowed inline-flex items-center"
            >
              {aiCheckLoading ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Checking...
                </>
              ) : (
                <>
                  <Shield className="w-5 h-5 mr-2" />
                  Check for AI Content
                </>
              )}
            </button>
          </div>
        )}

        {/* AI Detection Results inline */}
        {aiCheckResults && (
          <div className="mt-10">
            <AIDetectorResults
              results={aiCheckResults}
              onReset={() => setAiCheckResults(null)}
            />
          </div>
        )}
      </div>
    </main>
  );
}
