"use client";

/**
 * ResumeOptimizer — side-by-side resume optimization panel.
 *
 * Shows original vs optimized resume, change annotations,
 * section-by-section improvements, keyword additions, and download.
 *
 * Part of the Diagnose → Fix → Verify closed loop.
 */

import { useState, useCallback } from "react";
import { config } from "../lib/config";
import type { ResumeOptimizeResponse, SectionImprovement, ChangeItem } from "../lib/schemas";
import {
  ResumeOptimizeResponseSchema,
  validateResponse,
} from "../lib/schemas";

interface ResumeOptimizerProps {
  /** Resume document ID from upload */
  documentId: string;
  /** Job description ID from ATS scoring */
  jobId: string;
  /** Called when user wants to re-scan the optimized resume */
  onRescan?: (optimizedText: string) => void;
}

export default function ResumeOptimizer({
  documentId,
  jobId,
  onRescan,
}: ResumeOptimizerProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ResumeOptimizeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"diff" | "changes" | "sections">("diff");

  const generateOptimized = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(`${config.apiV1}/documents/optimize-resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          document_id: documentId,
          job_id: jobId,
        }),
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail?.detail || `Server error ${res.status}`);
      }

      const data = await res.json();
      const validated = validateResponse(
        ResumeOptimizeResponseSchema,
        data,
        "/documents/optimize-resume"
      );
      setResult(validated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Optimization failed");
    } finally {
      setLoading(false);
    }
  }, [documentId, jobId]);

  const handleDownload = () => {
    if (!result) return;
    const blob = new Blob([result.optimized_resume], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `optimized-resume-${documentId.slice(0, 8)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const impactColor = (impact: string) => {
    switch (impact) {
      case "high":
        return "bg-green-100 text-green-800 border-green-200";
      case "medium":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "low":
        return "bg-gray-100 text-gray-600 border-gray-200";
      default:
        return "bg-gray-100 text-gray-600 border-gray-200";
    }
  };

  // Not yet generated
  if (!result && !loading && !error) {
    return (
      <div className="mt-6 rounded-xl border-2 border-dashed border-indigo-200 bg-gradient-to-br from-indigo-50 to-white p-6 text-center">
        <div className="text-3xl mb-3">🚀</div>
        <h3 className="text-lg font-semibold text-indigo-900 mb-2">
          Resume Optimizer
        </h3>
        <p className="text-sm text-gray-600 mb-4 max-w-md mx-auto">
          Generate a tailored, ATS-optimized version of your resume
          for this specific job description. See exactly what changed and why.
        </p>
        <button
          onClick={generateOptimized}
          className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 text-white text-sm font-medium hover:from-indigo-700 hover:to-purple-700 transition-all shadow-md hover:shadow-lg"
        >
          ✨ Generate Optimized Resume
        </button>
      </div>
    );
  }

  return (
    <div className="mt-6 rounded-xl border border-indigo-200 bg-white shadow-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-5 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">🚀</span>
            <h3 className="text-white font-semibold">Optimized Resume</h3>
          </div>
          {result && (
            <div className="flex items-center gap-3">
              {onRescan && (
                <button
                  onClick={() => onRescan(result.optimized_resume)}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg bg-white/20 text-white hover:bg-white/30 transition-colors"
                >
                  🔍 Re-scan with ATS
                </button>
              )}
              <button
                onClick={handleDownload}
                className="px-3 py-1.5 text-xs font-medium rounded-lg bg-white/20 text-white hover:bg-white/30 transition-colors"
              >
                📥 Download
              </button>
            </div>
          )}
        </div>

        {/* Score improvement badge */}
        {result && (
          <div className="mt-3 flex items-center gap-4">
            <div className="px-3 py-1 rounded-full bg-white/20 text-white text-sm">
              <span className="font-semibold text-green-200">
                +{result.estimated_score_improvement}
              </span>{" "}
              estimated score improvement
            </div>
            <div className="px-3 py-1 rounded-full bg-white/20 text-white text-sm">
              <span className="font-semibold">{result.keywords_added.length}</span> keywords added
            </div>
            <div className="px-3 py-1 rounded-full bg-white/20 text-white text-sm">
              <span className="font-semibold">{result.changes.length}</span> changes
            </div>
          </div>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="p-12 text-center">
          <div className="inline-flex items-center gap-3 px-6 py-3 rounded-full bg-indigo-50 text-indigo-700">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span className="text-sm font-medium">
              Optimizing your resume for this role…
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-3">
            This typically takes 10-20 seconds
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-6">
          <div className="rounded-lg bg-red-50 border border-red-200 p-4">
            <p className="text-sm text-red-700">{error}</p>
            <button
              onClick={generateOptimized}
              className="mt-3 px-4 py-1.5 text-xs font-medium text-red-600 bg-red-100 rounded-lg hover:bg-red-200 transition-colors"
            >
              Try again
            </button>
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div>
          {/* Tabs */}
          <div className="border-b border-gray-200 px-5">
            <nav className="flex gap-6">
              {[
                { id: "diff" as const, label: "Side-by-side", icon: "📄" },
                { id: "changes" as const, label: "Change Log", icon: "📝" },
                { id: "sections" as const, label: "Section Details", icon: "🔍" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`py-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? "border-indigo-600 text-indigo-600"
                      : "border-transparent text-gray-500 hover:text-gray-700"
                  }`}
                >
                  {tab.icon} {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Diff Stats Bar */}
          <div className="px-5 py-3 bg-gray-50 border-b border-gray-200 flex items-center gap-6 text-xs text-gray-600">
            <span>
              <span className="font-semibold text-green-600">+{result.diff_stats.words_added}</span> words added
            </span>
            <span>
              <span className="font-semibold text-red-600">-{result.diff_stats.words_removed}</span> words removed
            </span>
            <span>
              {result.diff_stats.original_word_count} → {result.diff_stats.optimized_word_count} total words
            </span>
          </div>

          <div className="p-5">
            {/* Side-by-side tab */}
            {activeTab === "diff" && (
              <div className="rounded-lg border border-gray-200 overflow-hidden">
                <div className="bg-gray-100 p-3 text-center">
                  <p className="text-sm font-medium text-gray-700">
                    Optimized Resume Preview
                  </p>
                </div>
                <pre className="p-4 text-sm text-gray-800 whitespace-pre-wrap leading-relaxed max-h-[600px] overflow-y-auto font-sans">
                  {result.optimized_resume}
                </pre>
              </div>
            )}

            {/* Change Log tab */}
            {activeTab === "changes" && (
              <div className="space-y-3">
                {result.changes.map((change: ChangeItem, i: number) => (
                  <div
                    key={i}
                    className="rounded-lg border border-gray-200 p-4 hover:border-indigo-200 transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <span className="shrink-0 w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold flex items-center justify-center">
                        {i + 1}
                      </span>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded bg-indigo-50 text-indigo-600">
                            {change.section}
                          </span>
                        </div>
                        <p className="text-sm text-gray-800 mb-1">
                          {change.change}
                        </p>
                        <p className="text-xs text-gray-500 italic">
                          {change.reason}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Section Details tab */}
            {activeTab === "sections" && (
              <div className="space-y-4">
                {result.section_improvements.map(
                  (section: SectionImprovement, i: number) => (
                    <div
                      key={i}
                      className="rounded-lg border border-gray-200 overflow-hidden"
                    >
                      <div className="flex items-center justify-between bg-gray-50 px-4 py-2 border-b border-gray-200">
                        <span className="text-sm font-semibold text-gray-800">
                          {section.section}
                        </span>
                        <span
                          className={`px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded border ${impactColor(section.impact)}`}
                        >
                          {section.impact} impact
                        </span>
                      </div>
                      <div className="grid grid-cols-2 divide-x divide-gray-200">
                        <div className="p-3">
                          <p className="text-[10px] font-medium text-red-500 uppercase tracking-wider mb-1">
                            Before
                          </p>
                          <p className="text-sm text-gray-700 leading-relaxed">
                            {section.before}
                          </p>
                        </div>
                        <div className="p-3">
                          <p className="text-[10px] font-medium text-green-500 uppercase tracking-wider mb-1">
                            After
                          </p>
                          <p className="text-sm text-gray-700 leading-relaxed">
                            {section.after}
                          </p>
                        </div>
                      </div>
                    </div>
                  )
                )}
              </div>
            )}

            {/* Keywords Added */}
            {result.keywords_added.length > 0 && (
              <div className="mt-5 pt-4 border-t border-gray-200">
                <p className="text-xs font-medium text-gray-600 mb-2">
                  📌 Keywords Added
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {result.keywords_added.map((kw, i) => (
                    <span
                      key={i}
                      className="px-2.5 py-1 text-xs rounded-full bg-green-50 text-green-700 border border-green-200"
                    >
                      + {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
