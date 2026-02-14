"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Upload, FileText, Loader2 } from "lucide-react";
import AIDetectorResults from "../components/AIDetectorResults";
import { config } from "../lib/config";
import {
  AIDetectionResponseSchema,
  DocumentUploadResponseSchema,
  validateResponse,
} from "../lib/schemas";

/** Analysis progress stages for skeleton UX */
const PROGRESS_STAGES = [
  "Uploading document...",
  "Extracting text...",
  "Running 3-model ensemble (GPT-2, ChatGPT, Modern LLM)...",
  "Applying log-odds pooling and calibration...",
  "Computing linguistic features...",
  "Generating explanations...",
];

export default function AIDetector() {
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [documentText, setDocumentText] = useState("");
  const [loading, setLoading] = useState(false);
  const [progressStage, setProgressStage] = useState(0);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState("");

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setDocumentFile(file);
      setDocumentText(""); // Clear text if file is uploaded
    }
  };

  const handleSubmit = async () => {
    if (!documentFile && !documentText) {
      setError("Please provide a document to analyze");
      return;
    }

    setLoading(true);
    setError("");
    setProgressStage(0);

    try {
      const formData = new FormData();

      if (documentFile) {
        formData.append("file", documentFile);
      } else {
        // Create a blob from text
        const blob = new Blob([documentText], { type: "text/plain" });
        formData.append("file", blob, "document.txt");
      }

      // Stage 1: Upload
      setProgressStage(0);
      const uploadResponse = await fetch(`${config.apiV1}/documents/upload`, {
        method: "POST",
        body: formData,
      });

      if (!uploadResponse.ok) {
        throw new Error("Failed to upload document");
      }

      const uploadRaw = await uploadResponse.json();
      const uploadData = validateResponse(
        DocumentUploadResponseSchema,
        uploadRaw,
        "/documents/upload"
      );

      // Stage 2: Detect
      setProgressStage(2);
      const detectResponse = await fetch(`${config.apiV1}/documents/detect`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          document_id: uploadData.document_id,
          text: documentText || uploadData.text_content,
        }),
      });

      if (!detectResponse.ok) {
        throw new Error("Failed to analyze document");
      }

      setProgressStage(4);
      const detectRaw = await detectResponse.json();
      const detectData = validateResponse(
        AIDetectionResponseSchema,
        detectRaw,
        "/documents/detect"
      );

      setProgressStage(5);
      setResults(detectData);
    } catch (err: any) {
      setError(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  if (results) {
    return <AIDetectorResults results={results} onReset={() => setResults(null)} />;
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-900 via-slate-900 to-slate-900">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <Link
          href="/"
          className="inline-flex items-center text-blue-400 hover:text-blue-300 mb-8"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          Back to Home
        </Link>

        <h1 className="text-4xl font-bold text-white mb-2">AI Content Detector</h1>
        <p className="text-slate-400 mb-12">
          Upload or paste your document to detect AI-generated content
        </p>

        {/* Error Message */}
        {error && (
          <div className="bg-red-500/10 border border-red-500 text-red-400 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Loading Skeleton */}
        {loading && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8 mb-8">
            <h2 className="text-xl font-bold text-white mb-6">Analyzing Document</h2>
            <div className="space-y-4">
              {PROGRESS_STAGES.map((stage, i) => (
                <div key={i} className="flex items-center gap-3">
                  {i < progressStage ? (
                    <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center">
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  ) : i === progressStage ? (
                    <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
                  ) : (
                    <div className="w-5 h-5 rounded-full border border-slate-600" />
                  )}
                  <span className={i <= progressStage ? "text-white" : "text-slate-500"}>
                    {stage}
                  </span>
                </div>
              ))}
            </div>
            {/* Skeleton bars */}
            <div className="mt-8 space-y-3">
              <div className="h-4 bg-slate-700 rounded animate-pulse w-3/4" />
              <div className="h-4 bg-slate-700 rounded animate-pulse w-1/2" />
              <div className="h-4 bg-slate-700 rounded animate-pulse w-5/6" />
              <div className="h-4 bg-slate-700 rounded animate-pulse w-2/3" />
            </div>
          </div>
        )}

        {/* Document Upload — hidden when loading */}
        {!loading && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8 mb-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center">
              <FileText className="w-6 h-6 mr-3 text-blue-500" />
              Your Document
            </h2>

            {/* File Upload */}
            <div className="mb-6">
              <label className="block text-slate-300 mb-3">Upload File (PDF, DOC, DOCX, JPG, PNG)</label>
              <div className="relative">
                <input
                  type="file"
                  accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.txt"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="document-upload"
                />
                <label
                  htmlFor="document-upload"
                  className="flex items-center justify-center w-full px-6 py-4 border-2 border-dashed border-slate-600 rounded-lg cursor-pointer hover:border-blue-500 transition-colors"
                >
                  <Upload className="w-5 h-5 mr-2 text-slate-400" />
                  <span className="text-slate-300">
                    {documentFile ? documentFile.name : "Click to upload"}
                  </span>
                </label>
              </div>
            </div>

            <div className="text-center text-slate-500 mb-6">OR</div>

            {/* Text Input */}
            <div>
              <label className="block text-slate-300 mb-3">Paste Document Text</label>
              <textarea
                value={documentText}
                onChange={(e) => {
                  setDocumentText(e.target.value);
                  setDocumentFile(null); // Clear file if text is entered
                }}
                placeholder="Paste your document content here..."
                className="w-full h-96 px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>
          </div>
        )}

        {/* Submit Button */}
        {!loading && (
          <div className="text-center">
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="px-12 py-4 bg-blue-500 text-white rounded-lg font-semibold hover:bg-blue-600 transition-colors disabled:bg-slate-700 disabled:cursor-not-allowed inline-flex items-center"
            >
              Detect AI Content
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
