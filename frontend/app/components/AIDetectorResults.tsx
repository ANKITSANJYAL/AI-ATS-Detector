"use client";

import { ArrowLeft, AlertCircle, ChevronDown, ChevronUp, Download } from "lucide-react";
import { useState, useMemo } from "react";
import { exportDetectionCSV, exportDetectionReport } from "../lib/export";

interface SentenceFeatures {
  word_count?: number;
  avg_word_length?: number;
  vocabulary_diversity?: number;
  formality_score?: number;
  has_passive_voice?: boolean;
  sentence_length_class?: string;
  complexity_score?: number;
  personal_voice?: boolean;
  contraction_count?: number;
  punctuation_variety?: number;
}

interface SentenceItem {
  text: string;
  is_ai: boolean;
  confidence: number;
  reason?: string;
  block_index?: number;
  features?: SentenceFeatures;
}

interface AIDetectorResultsProps {
  results: any;
  onReset: () => void;
}

export default function AIDetectorResults({ results, onReset }: AIDetectorResultsProps) {
  const [hoveredSentence, setHoveredSentence] = useState<number | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const [isAnalysisExpanded, setIsAnalysisExpanded] = useState(true);

  // Calculate AI probability percentage
  const aiProbability = Math.round((results.ai_probability || 0) * 100);

  // Sentence analysis from API — authoritative per-sentence classification
  const sentenceAnalysis: SentenceItem[] = useMemo(
    () => (results.sentence_analysis || []).filter((s: any) => s && s.text),
    [results.sentence_analysis]
  );

  // Structured blocks for document formatting (headings, bold, paragraphs)
  const structuredBlocks: any[] = results.structured_blocks || [];
  const useStructured = structuredBlocks.length > 0;
  const hasSentenceAnalysis = sentenceAnalysis.length > 0;

  // Group sentences by their block_index (set by the backend per-block
  // classification).  Each sentence carries a `block_index` property that
  // maps directly to the structured_blocks array index.
  const blockMappings: { sentence: SentenceItem; analysisIndex: number }[][] =
    useMemo(() => {
      if (!useStructured || !hasSentenceAnalysis) return [];

      // Initialise one empty array per block
      const groups: { sentence: SentenceItem; analysisIndex: number }[][] =
        structuredBlocks.map(() => []);

      sentenceAnalysis.forEach((item, idx) => {
        const bi = (item as any).block_index;
        if (bi !== undefined && bi >= 0 && bi < groups.length) {
          groups[bi].push({ sentence: item, analysisIndex: idx });
        }
      });

      return groups;
    }, [structuredBlocks, sentenceAnalysis, useStructured, hasSentenceAnalysis]);

  // Use structured rendering when we have both blocks and sentences
  const shouldUseStructured = useStructured && hasSentenceAnalysis;

  // Safe accessor for tooltip data
  const getTooltipData = (index: number): SentenceItem | null => {
    if (index >= 0 && index < sentenceAnalysis.length) {
      return sentenceAnalysis[index];
    }
    return null;
  };

  const handleMouseEnter = (index: number, event: React.MouseEvent) => {
    if (index < 0 || index >= sentenceAnalysis.length) return;
    setHoveredSentence(index);
    const rect = (event.target as HTMLElement).getBoundingClientRect();
    setTooltipPosition({
      x: rect.left + rect.width / 2,
      y: rect.top - 10,
    });
  };

  const handleMouseLeave = () => {
    setHoveredSentence(null);
  };

  /** Render a single highlighted sentence span */
  const renderSentenceSpan = (
    item: SentenceItem,
    analysisIndex: number,
    trailingSpace: boolean,
    key: string
  ) => (
    <span key={key}>
      <span
        onMouseEnter={(e) => handleMouseEnter(analysisIndex, e)}
        onMouseLeave={handleMouseLeave}
        className={`cursor-pointer transition-all duration-200 ${
          item.is_ai
            ? "bg-red-500/20 text-red-100 hover:bg-red-500/30 border-b-2 border-red-500/50"
            : "bg-green-500/20 text-green-100 hover:bg-green-500/30 border-b-2 border-green-500/50"
        } px-1 py-0.5 rounded`}
      >
        {item.text}
      </span>
      {trailingSpace && " "}
    </span>
  );

  /** Render the tooltip */
  const renderTooltip = () => {
    if (hoveredSentence === null) return null;
    const data = getTooltipData(hoveredSentence);
    if (!data) return null;

    const confidencePct = Math.round(data.confidence * 100);
    // P(AI) for the bar position: if is_ai, P(AI) = confidence; else P(AI) = 1 - confidence
    const aiPct = Math.round((data.is_ai ? data.confidence : 1 - data.confidence) * 100);
    const feats = data.features || {};

    /** Small feature bar component */
    const FeatureBar = ({ label, value, invert }: { label: string; value: number; invert?: boolean }) => {
      // invert: when true, low value = AI signal (shown in red zone)
      const displayPct = Math.round(value * 100);
      const barColor = invert
        ? value < 0.4 ? "bg-red-400" : value > 0.65 ? "bg-green-400" : "bg-yellow-400"
        : value > 0.65 ? "bg-red-400" : value < 0.4 ? "bg-green-400" : "bg-yellow-400";

      return (
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 w-24 shrink-0 truncate">{label}</span>
          <div className="flex-1 bg-slate-700 rounded-full h-1.5 min-w-[60px]">
            <div
              className={`h-1.5 rounded-full ${barColor}`}
              style={{ width: `${displayPct}%` }}
            />
          </div>
          <span className="text-xs text-slate-500 w-8 text-right">{displayPct}%</span>
        </div>
      );
    };

    const hasFeatures =
      feats.vocabulary_diversity !== undefined ||
      feats.complexity_score !== undefined ||
      feats.formality_score !== undefined;

    return (
      <div
        className="fixed z-50 bg-slate-800 border-2 rounded-lg shadow-2xl p-4 max-w-md transform -translate-x-1/2 -translate-y-full pointer-events-none"
        style={{
          left: `${tooltipPosition.x}px`,
          top: `${tooltipPosition.y}px`,
          borderColor: data.is_ai ? "rgb(239 68 68 / 0.6)" : "rgb(34 197 94 / 0.6)",
        }}
      >
        {/* Classification label */}
        <div className="flex items-center justify-between mb-3">
          <span
            className={`font-bold text-sm ${
              data.is_ai ? "text-red-400" : "text-green-400"
            }`}
          >
            {data.is_ai ? "⚠️ AI-Generated" : "✓ Human-Written"}
          </span>
          <span className={`text-xs font-mono px-2 py-0.5 rounded ${
            data.is_ai ? "bg-red-500/20 text-red-300" : "bg-green-500/20 text-green-300"
          }`}>
            {confidencePct}%
          </span>
        </div>

        {/* AI probability bar — position shows P(AI) on the Human↔AI axis */}
        <div className="mb-3">
          <div className="w-full bg-slate-700 rounded-full h-1.5">
            <div
              className={`h-1.5 rounded-full transition-all ${
                aiPct > 50 ? "bg-red-500" : "bg-green-500"
              }`}
              style={{ width: `${aiPct}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-slate-500 mt-0.5">
            <span>Human</span>
            <span>AI</span>
          </div>
        </div>

        {/* Per-sentence linguistic features */}
        {hasFeatures && (
          <div className="border-t border-slate-700 pt-2 mb-2 space-y-1.5">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">
              Linguistic Features
            </div>
            {feats.vocabulary_diversity !== undefined && (
              <FeatureBar label="Vocab Diversity" value={feats.vocabulary_diversity} invert />
            )}
            {feats.complexity_score !== undefined && (
              <FeatureBar label="Complexity" value={feats.complexity_score} />
            )}
            {feats.formality_score !== undefined && (
              <FeatureBar label="Formality" value={feats.formality_score} />
            )}
            {feats.punctuation_variety !== undefined && (
              <FeatureBar label="Punct. Variety" value={feats.punctuation_variety} invert />
            )}
            {/* Small tags for boolean features */}
            <div className="flex flex-wrap gap-1 mt-1">
              {feats.has_passive_voice && (
                <span className="text-xs bg-red-500/15 text-red-300 px-1.5 py-0.5 rounded">
                  Passive Voice
                </span>
              )}
              {feats.personal_voice && (
                <span className="text-xs bg-green-500/15 text-green-300 px-1.5 py-0.5 rounded">
                  Personal Voice
                </span>
              )}
              {(feats.contraction_count ?? 0) > 0 && (
                <span className="text-xs bg-green-500/15 text-green-300 px-1.5 py-0.5 rounded">
                  {feats.contraction_count} Contraction{(feats.contraction_count ?? 0) > 1 ? "s" : ""}
                </span>
              )}
              {feats.sentence_length_class && (
                <span className="text-xs bg-slate-600/50 text-slate-300 px-1.5 py-0.5 rounded">
                  {feats.word_count} words · {feats.sentence_length_class}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Reasoning */}
        {data.reason && (
          <div className="border-t border-slate-700 pt-2">
            <div className="text-xs font-semibold text-slate-400 mb-1 uppercase tracking-wide">
              Why?
            </div>
            <p className="text-slate-300 text-sm leading-relaxed">
              {data.reason}
            </p>
          </div>
        )}

        {/* Tooltip arrow */}
        <div
          className="absolute left-1/2 bottom-0 transform -translate-x-1/2 translate-y-full w-0 h-0 border-l-8 border-r-8 border-t-8 border-l-transparent border-r-transparent"
          style={{
            borderTopColor: data.is_ai ? "rgb(239 68 68 / 0.6)" : "rgb(34 197 94 / 0.6)",
          }}
        />
      </div>
    );
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-900 via-slate-900 to-slate-900">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <button
          onClick={onReset}
          className="inline-flex items-center text-blue-400 hover:text-blue-300 mb-8"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          New Analysis
        </button>

        <div className="flex items-center justify-between mb-12">
          <h1 className="text-4xl font-bold text-white">AI Detection Results</h1>
          <div className="flex gap-2">
            <button
              onClick={() => exportDetectionCSV(results)}
              className="inline-flex items-center px-3 py-2 text-sm bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 transition-colors"
            >
              <Download className="w-4 h-4 mr-1.5" />
              CSV
            </button>
            <button
              onClick={() => exportDetectionReport(results)}
              className="inline-flex items-center px-3 py-2 text-sm bg-slate-700 text-slate-300 rounded-lg hover:bg-slate-600 transition-colors"
            >
              <Download className="w-4 h-4 mr-1.5" />
              Report
            </button>
          </div>
        </div>

        {/* AI Probability Score */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-12 mb-8">
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
                  strokeDashoffset={`${2 * Math.PI * 120 * (1 - aiProbability / 100)}`}
                  className={`transition-all duration-1000 ease-out ${
                    aiProbability > 70 ? "text-red-500" : aiProbability > 40 ? "text-yellow-500" : "text-green-500"
                  }`}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-6xl font-bold text-white">{aiProbability}%</span>
                <span className="text-lg text-slate-400 mt-2">AI Detected</span>
              </div>
            </div>
            <h2 className="text-2xl font-bold text-white mt-8">
              {aiProbability > 70 ? "High AI Probability" : aiProbability > 40 ? "Moderate AI Content" : "Likely Human-Written"}
            </h2>
            <p className="text-slate-400 mt-2 text-center max-w-md">
              {results.explanation || "The document has been analyzed for AI-generated content"}
            </p>
          </div>
        </div>

        {/* Sentence-by-Sentence Analysis */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8 mb-8">
          <button
            onClick={() => setIsAnalysisExpanded(!isAnalysisExpanded)}
            className="w-full flex items-center justify-between text-left group mb-6"
          >
            <h2 className="text-2xl font-bold text-white flex items-center">
              <AlertCircle className="w-6 h-6 mr-3 text-blue-500" />
              Sentence-Level Analysis
            </h2>
            <div className="text-slate-400 group-hover:text-slate-300 transition-colors">
              {isAnalysisExpanded ? (
                <ChevronUp className="w-6 h-6" />
              ) : (
                <ChevronDown className="w-6 h-6" />
              )}
            </div>
          </button>

          {isAnalysisExpanded && hasSentenceAnalysis ? (
            <div className="relative">
              <div className="bg-slate-900/50 border border-slate-600 rounded-lg p-8 leading-relaxed">
                {shouldUseStructured ? (
                  /* ── Structured blocks: preserves headings, paragraphs, bold ── */
                  structuredBlocks.map((block: any, blockIdx: number) => {
                    const mapped = blockMappings[blockIdx] || [];

                    return (
                      <div
                        key={blockIdx}
                        className={`${
                          block.type === "heading"
                            ? "font-bold text-xl mt-8 mb-4"
                            : "mb-6"
                        } ${
                          block.font_size === "large"
                            ? "text-lg"
                            : block.font_size === "medium"
                            ? "text-base"
                            : "text-base"
                        }`}
                        style={{
                          fontWeight: block.bold ? "bold" : "normal",
                          whiteSpace: "pre-wrap",
                          lineHeight: block.type === "heading" ? "1.4" : "1.8",
                        }}
                      >
                        {mapped.length > 0 ? (
                          mapped.map(({ sentence, analysisIndex }, sentIdx) =>
                            renderSentenceSpan(
                              sentence,
                              analysisIndex,
                              sentIdx < mapped.length - 1,
                              `block-${blockIdx}-sent-${sentIdx}`
                            )
                          )
                        ) : (
                          <span className="text-slate-300">{block.text}</span>
                        )}
                      </div>
                    );
                  })
                ) : (
                  /* ── Flat fallback: render sentences directly ── */
                  sentenceAnalysis.map((item, index) =>
                    renderSentenceSpan(
                      item,
                      index,
                      index < sentenceAnalysis.length - 1,
                      `flat-${index}`
                    )
                  )
                )}
              </div>

              {/* Hover tooltip */}
              {renderTooltip()}

              {/* Legend */}
              <div className="mt-6 flex items-center justify-center gap-6 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-red-500/30 border-b-2 border-red-500/50 rounded"></div>
                  <span className="text-slate-400">AI-Generated</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-green-500/30 border-b-2 border-green-500/50 rounded"></div>
                  <span className="text-slate-400">Human-Written</span>
                </div>
                <div className="text-slate-500 italic">
                  (Hover over text for details)
                </div>
              </div>
            </div>
          ) : isAnalysisExpanded ? (
            <div className="text-center py-12">
              <p className="text-slate-400 mb-2">No sentence-level analysis available</p>
              <p className="text-slate-500 text-sm">The document may be too short or analysis failed</p>
            </div>
          ) : null}
        </div>

        {/* Detailed Analysis */}
        <div className="grid md:grid-cols-2 gap-8">
          {/* Features */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8">
            <h3 className="text-xl font-bold text-white mb-6">Detection Features</h3>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-300">Sentence Complexity</span>
                  <span className="text-slate-400">
                    {Math.round((results.linguistic_features?.sentence_complexity || 0.5) * 100)}%
                  </span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${(results.linguistic_features?.sentence_complexity || 0.5) * 100}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-300">Vocabulary Diversity</span>
                  <span className="text-slate-400">
                    {Math.round((results.linguistic_features?.vocabulary_diversity || 0.6) * 100)}%
                  </span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${(results.linguistic_features?.vocabulary_diversity || 0.6) * 100}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-300">Stylistic Consistency</span>
                  <span className="text-slate-400">
                    {Math.round((results.linguistic_features?.stylistic_consistency || 0.7) * 100)}%
                  </span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${(results.linguistic_features?.stylistic_consistency || 0.7) * 100}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-300">Coherence Score</span>
                  <span className="text-slate-400">
                    {Math.round((results.linguistic_features?.coherence_score || 0.8) * 100)}%
                  </span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${(results.linguistic_features?.coherence_score || 0.8) * 100}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-300">Transition Patterns</span>
                  <span className="text-slate-400">
                    {Math.round((results.linguistic_features?.transition_patterns || 0.5) * 100)}%
                  </span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${(results.linguistic_features?.transition_patterns || 0.5) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Explanation */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8">
            <h3 className="text-xl font-bold text-white mb-6">Why This Score?</h3>
            <div className="space-y-4 text-slate-300">
              {(results.detailed_analysis && results.detailed_analysis.length > 0
                ? results.detailed_analysis
                : [
                  "The text shows patterns consistent with the analysis",
                  "Sentence structure reveals computational or human characteristics",
                  "Vocabulary usage indicates authorship style",
                  "Transition patterns suggest composition method"
                ]).map((reason: string, index: number) => (
                <div key={index} className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-6 h-6 bg-blue-500/20 rounded-full flex items-center justify-center mt-1">
                    <span className="text-blue-400 text-xs font-bold">{index + 1}</span>
                  </div>
                  <p className="flex-1 leading-relaxed">{reason}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
