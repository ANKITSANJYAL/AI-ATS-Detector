"use client";

/**
 * HumanizerPanel — AI sentence humanizer inline panel.
 *
 * Displays rewrite suggestions for AI-flagged sentences.
 * Users can click a flagged sentence → see 3 rewrite options → apply one → re-scan.
 *
 * Part of the Diagnose → Fix → Verify closed loop.
 */

import { useState, useCallback } from "react";
import { config } from "../lib/config";
import type { HumanizeResponse, RewriteOption } from "../lib/schemas";
import {
  HumanizeResponseSchema,
  validateResponse,
} from "../lib/schemas";

type Tone = "natural" | "casual" | "professional" | "academic";

interface HumanizerPanelProps {
  /** The AI-flagged sentence text */
  sentence: string;
  /** Context: 1-2 sentences before */
  contextBefore?: string;
  /** Context: 1-2 sentences after */
  contextAfter?: string;
  /** Called when user picks a rewrite */
  onApply: (original: string, replacement: string) => void;
  /** Called when panel is dismissed */
  onClose: () => void;
}

export default function HumanizerPanel({
  sentence,
  contextBefore = "",
  contextAfter = "",
  onApply,
  onClose,
}: HumanizerPanelProps) {
  const [tone, setTone] = useState<Tone>("natural");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<HumanizeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [appliedIndex, setAppliedIndex] = useState<number | null>(null);

  const fetchRewrites = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setAppliedIndex(null);

    try {
      const res = await fetch(`${config.apiV1}/documents/humanize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sentence,
          context_before: contextBefore,
          context_after: contextAfter,
          tone,
        }),
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail?.detail || `Server error ${res.status}`);
      }

      const data = await res.json();
      const validated = validateResponse(
        HumanizeResponseSchema,
        data,
        "/documents/humanize"
      );
      setResult(validated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to humanize");
    } finally {
      setLoading(false);
    }
  }, [sentence, contextBefore, contextAfter, tone]);

  const handleApply = (rewrite: RewriteOption, index: number) => {
    setAppliedIndex(index);
    onApply(sentence, rewrite.text);
  };

  const tones: { value: Tone; label: string; icon: string }[] = [
    { value: "natural", label: "Natural", icon: "🌿" },
    { value: "casual", label: "Casual", icon: "💬" },
    { value: "professional", label: "Professional", icon: "💼" },
    { value: "academic", label: "Academic", icon: "🎓" },
  ];

  return (
    <div className="mt-3 rounded-xl border border-purple-200 bg-gradient-to-br from-purple-50 to-white p-4 shadow-lg animate-in slide-in-from-top-2 duration-300">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">✨</span>
          <h4 className="text-sm font-semibold text-purple-900">
            AI Humanizer
          </h4>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 transition-colors p-1"
          aria-label="Close humanizer panel"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Original sentence */}
      <div className="mb-3 rounded-lg bg-red-50 border border-red-200 p-3">
        <p className="text-xs font-medium text-red-600 mb-1">AI-flagged sentence</p>
        <p className="text-sm text-gray-800 leading-relaxed">{sentence}</p>
      </div>

      {/* Tone selector */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs text-gray-500 font-medium">Tone:</span>
        <div className="flex gap-1">
          {tones.map((t) => (
            <button
              key={t.value}
              onClick={() => setTone(t.value)}
              className={`px-2.5 py-1 text-xs rounded-full transition-all ${
                tone === t.value
                  ? "bg-purple-600 text-white shadow-sm"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Generate button */}
      {!result && (
        <button
          onClick={fetchRewrites}
          disabled={loading}
          className="w-full py-2.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 text-white text-sm font-medium hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Generating rewrites…
            </span>
          ) : (
            "🔄 Generate Human Rewrites"
          )}
        </button>
      )}

      {/* Error */}
      {error && (
        <div className="mt-2 p-3 rounded-lg bg-red-50 border border-red-200">
          <p className="text-sm text-red-700">{error}</p>
          <button
            onClick={fetchRewrites}
            className="mt-2 text-xs text-red-600 underline hover:text-red-800"
          >
            Try again
          </button>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-3">
          {/* Explanation */}
          <div className="rounded-lg bg-amber-50 border border-amber-200 p-3">
            <p className="text-xs font-medium text-amber-700 mb-1">
              Why it sounds AI-generated
            </p>
            <p className="text-sm text-gray-700">{result.explanation}</p>
            {result.ai_tells.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {result.ai_tells.map((tell, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 text-xs rounded-full bg-amber-100 text-amber-800 border border-amber-200"
                  >
                    {tell}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Rewrite options */}
          <div className="space-y-2">
            <p className="text-xs font-medium text-gray-600">
              Rewrite suggestions
            </p>
            {result.rewrites.map((rewrite, i) => (
              <div
                key={i}
                className={`rounded-lg border p-3 transition-all ${
                  appliedIndex === i
                    ? "border-green-400 bg-green-50 ring-1 ring-green-300"
                    : "border-gray-200 bg-white hover:border-purple-300 hover:shadow-sm"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <span className="inline-block px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded bg-gray-100 text-gray-500 mb-1.5">
                      {rewrite.approach}
                    </span>
                    <p className="text-sm text-gray-800 leading-relaxed">
                      {rewrite.text}
                    </p>
                  </div>
                  <button
                    onClick={() => handleApply(rewrite, i)}
                    disabled={appliedIndex === i}
                    className={`shrink-0 px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
                      appliedIndex === i
                        ? "bg-green-100 text-green-700 cursor-default"
                        : "bg-purple-100 text-purple-700 hover:bg-purple-200"
                    }`}
                  >
                    {appliedIndex === i ? "✓ Applied" : "Apply"}
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Re-generate */}
          <button
            onClick={fetchRewrites}
            disabled={loading}
            className="w-full py-2 text-xs text-purple-600 hover:text-purple-800 font-medium transition-colors"
          >
            {loading ? "Regenerating…" : "🔄 Regenerate with different approach"}
          </button>
        </div>
      )}
    </div>
  );
}
