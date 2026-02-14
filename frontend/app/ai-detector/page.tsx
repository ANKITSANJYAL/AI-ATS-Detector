"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Upload, FileText, Loader2 } from "lucide-react";
import AIDetectorResults from "../components/AIDetectorResults";
import { config } from "../lib/config";

export default function AIDetector() {
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [documentText, setDocumentText] = useState("");
  const [loading, setLoading] = useState(false);
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

    try {
      const formData = new FormData();

      if (documentFile) {
        formData.append("file", documentFile);
      } else {
        // Create a blob from text
        const blob = new Blob([documentText], { type: "text/plain" });
        formData.append("file", blob, "document.txt");
      }

      // First upload the document
      const uploadResponse = await fetch(`${config.apiV1}/documents/upload`, {
        method: "POST",
        body: formData,
      });

      if (!uploadResponse.ok) {
        throw new Error("Failed to upload document");
      }

      const uploadData = await uploadResponse.json();

      // Then detect AI content
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

      const detectData = await detectResponse.json();
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

        {/* Document Upload */}
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

        {/* Submit Button */}
        <div className="text-center">
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="px-12 py-4 bg-blue-500 text-white rounded-lg font-semibold hover:bg-blue-600 transition-colors disabled:bg-slate-700 disabled:cursor-not-allowed inline-flex items-center"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Analyzing...
              </>
            ) : (
              "Detect AI Content"
            )}
          </button>
        </div>
      </div>
    </main>
  );
}
