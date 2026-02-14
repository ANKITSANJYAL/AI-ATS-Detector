"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Clock,
  FileText,
  Target,
  Shield,
  Loader2,
  ChevronRight,
} from "lucide-react";
import { config } from "../lib/config";

interface DetectionItem {
  id: string;
  document_id: string;
  filename: string;
  detection_result: string;
  confidence_score: number;
  ai_probability: number;
  created_at: string;
}

interface ATSItem {
  id: string;
  document_id: string;
  filename: string;
  job_title: string;
  overall_score: number;
  keyword_match_score: number;
  semantic_similarity_score: number;
  format_score: number;
  created_at: string;
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

function resultColor(result: string): string {
  switch (result) {
    case "human":
      return "text-green-400";
    case "ai_generated":
      return "text-red-400";
    case "mixed":
      return "text-yellow-400";
    default:
      return "text-slate-400";
  }
}

function resultBadge(result: string): string {
  switch (result) {
    case "human":
      return "bg-green-500/15 text-green-400 border-green-500/30";
    case "ai_generated":
      return "bg-red-500/15 text-red-400 border-red-500/30";
    case "mixed":
      return "bg-yellow-500/15 text-yellow-400 border-yellow-500/30";
    default:
      return "bg-slate-500/15 text-slate-400 border-slate-500/30";
  }
}

function resultLabel(result: string): string {
  switch (result) {
    case "human":
      return "Human";
    case "ai_generated":
      return "AI Generated";
    case "mixed":
      return "Mixed";
    default:
      return result;
  }
}

function scoreColor(score: number): string {
  if (score >= 80) return "text-emerald-400";
  if (score >= 60) return "text-yellow-400";
  return "text-red-400";
}

export default function HistoryPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [detections, setDetections] = useState<DetectionItem[]>([]);
  const [atsScores, setAtsScores] = useState<ATSItem[]>([]);
  const [totalDetections, setTotalDetections] = useState(0);
  const [totalAts, setTotalAts] = useState(0);
  const [activeTab, setActiveTab] = useState<"detections" | "ats">("detections");

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${config.apiV1}/history/?limit=50&offset=0`);
      if (!res.ok) throw new Error("Failed to fetch history");
      const data = await res.json();
      setDetections(data.detections || []);
      setAtsScores(data.ats_scores || []);
      setTotalDetections(data.total_detections || 0);
      setTotalAts(data.total_ats || 0);
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <Link
          href="/"
          className="inline-flex items-center text-blue-400 hover:text-blue-300 mb-8"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          Back to Home
        </Link>

        <div className="flex items-center gap-3 mb-2">
          <Clock className="w-8 h-8 text-blue-400" />
          <h1 className="text-4xl font-bold text-white">Analysis History</h1>
        </div>
        <p className="text-slate-400 mb-10">
          All your past AI detection and ATS scoring results
        </p>

        {/* Tabs */}
        <div className="flex space-x-4 mb-8 border-b border-slate-700">
          <button
            onClick={() => setActiveTab("detections")}
            className={`px-6 py-3 font-semibold transition-colors ${
              activeTab === "detections"
                ? "text-blue-400 border-b-2 border-blue-400"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Shield className="w-5 h-5 inline-block mr-2" />
            AI Detections ({totalDetections})
          </button>
          <button
            onClick={() => setActiveTab("ats")}
            className={`px-6 py-3 font-semibold transition-colors ${
              activeTab === "ats"
                ? "text-emerald-400 border-b-2 border-emerald-400"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Target className="w-5 h-5 inline-block mr-2" />
            ATS Scores ({totalAts})
          </button>
        </div>

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
            <span className="ml-3 text-slate-400">Loading history...</span>
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div className="bg-red-500/10 border border-red-500 text-red-400 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Detections tab */}
        {!loading && !error && activeTab === "detections" && (
          <div className="space-y-4">
            {detections.length === 0 ? (
              <div className="text-center py-20">
                <Shield className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                <p className="text-slate-400 mb-2">No detection results yet</p>
                <Link href="/ai-detector" className="text-blue-400 hover:text-blue-300 text-sm">
                  Run your first analysis
                </Link>
              </div>
            ) : (
              detections.map((item) => (
                <div
                  key={item.id}
                  className="bg-slate-800/50 border border-slate-700 rounded-xl p-5 flex items-center gap-4 hover:border-slate-600 transition-colors"
                >
                  <div className="flex-shrink-0">
                    <FileText className="w-8 h-8 text-blue-400/60" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-white font-medium truncate">
                        {item.filename}
                      </span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded border ${resultBadge(
                          item.detection_result
                        )}`}
                      >
                        {resultLabel(item.detection_result)}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-slate-500">
                      <span>
                        AI Probability:{" "}
                        <span className={resultColor(item.detection_result)}>
                          {Math.round(item.ai_probability * 100)}%
                        </span>
                      </span>
                      <span>
                        Confidence:{" "}
                        <span className="text-slate-300">
                          {Math.round(item.confidence_score * 100)}%
                        </span>
                      </span>
                      <span>{timeAgo(item.created_at)}</span>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-600" />
                </div>
              ))
            )}
          </div>
        )}

        {/* ATS tab */}
        {!loading && !error && activeTab === "ats" && (
          <div className="space-y-4">
            {atsScores.length === 0 ? (
              <div className="text-center py-20">
                <Target className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                <p className="text-slate-400 mb-2">No ATS scoring results yet</p>
                <Link href="/ats-checker" className="text-emerald-400 hover:text-emerald-300 text-sm">
                  Score your first resume
                </Link>
              </div>
            ) : (
              atsScores.map((item) => (
                <div
                  key={item.id}
                  className="bg-slate-800/50 border border-slate-700 rounded-xl p-5 flex items-center gap-4 hover:border-slate-600 transition-colors"
                >
                  <div className="flex-shrink-0">
                    <div className="w-12 h-12 rounded-full bg-slate-700 flex items-center justify-center">
                      <span className={`text-lg font-bold ${scoreColor(item.overall_score)}`}>
                        {Math.round(item.overall_score)}
                      </span>
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-white font-medium truncate">
                        {item.filename}
                      </span>
                      <span className="text-xs text-slate-500">
                        vs. {item.job_title}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-slate-500">
                      <span>
                        Semantic:{" "}
                        <span className="text-indigo-400">
                          {Math.round(item.semantic_similarity_score)}
                        </span>
                      </span>
                      <span>
                        Keywords:{" "}
                        <span className="text-amber-400">
                          {Math.round(item.keyword_match_score)}
                        </span>
                      </span>
                      <span>
                        Format:{" "}
                        <span className="text-cyan-400">
                          {Math.round(item.format_score)}
                        </span>
                      </span>
                      <span>{timeAgo(item.created_at)}</span>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-600" />
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </main>
  );
}
