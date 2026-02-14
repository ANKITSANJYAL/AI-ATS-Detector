"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Upload, Link as LinkIcon, FileText, Loader2 } from "lucide-react";
import ATSResults from "../components/ATSResults";

export default function ATSChecker() {
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [resumeText, setResumeText] = useState("");
  const [jobUrl, setJobUrl] = useState("");
  const [jobText, setJobText] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState("");

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setResumeFile(file);
      setResumeText(""); // Clear text if file is uploaded
    }
  };

  const handleSubmit = async () => {
    if ((!resumeFile && !resumeText) || (!jobUrl && !jobText)) {
      setError("Please provide both resume and job description");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const formData = new FormData();

      if (resumeFile) {
        formData.append("file", resumeFile);
      } else {
        // Create a blob from text
        const blob = new Blob([resumeText], { type: "text/plain" });
        formData.append("file", blob, "resume.txt");
      }

      // First upload the document
      const uploadResponse = await fetch("http://localhost:8000/api/v1/documents/upload", {
        method: "POST",
        body: formData,
      });

      if (!uploadResponse.ok) {
        throw new Error("Failed to upload document");
      }

      const uploadData = await uploadResponse.json();

      // Then score it
      const scoreResponse = await fetch("http://localhost:8000/api/v1/documents/score", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          document_id: uploadData.document_id,
          job_description: jobText || undefined,
          job_url: jobUrl || undefined,
        }),
      });

      if (!scoreResponse.ok) {
        const errorData = await scoreResponse.json().catch(() => ({}));

        // Check if it's a URL fetch blocked error with instructions
        if (errorData.detail?.error === "url_fetch_blocked") {
          const detail = errorData.detail;
          setError(
            `${detail.message}\n\n` +
            detail.instructions.join('\n')
          );
        } else {
          throw new Error(errorData.detail?.message || errorData.detail || "Failed to score document");
        }
        return;
      }

      const scoreData = await scoreResponse.json();

      // Transform backend response to match frontend expectations
      const transformedData = {
        ...scoreData,
        matched_skills: scoreData.skill_matches
          ?.filter((sm: any) => sm.matched)
          .map((sm: any) => sm.skill) || [],
        missing_skills: [
          ...(scoreData.gap_analysis?.missing_required_skills || []),
          ...(scoreData.gap_analysis?.missing_preferred_skills || []),
        ],
        recommendations: scoreData.gap_analysis?.recommendations || [],
      };

      setResults(transformedData);
    } catch (err: any) {
      setError(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  if (results) {
    return <ATSResults results={results} onReset={() => setResults(null)} />;
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-emerald-900 via-slate-900 to-slate-900">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <Link
          href="/"
          className="inline-flex items-center text-emerald-400 hover:text-emerald-300 mb-8"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          Back to Home
        </Link>

        <h1 className="text-4xl font-bold text-white mb-2">ATS Score Checker</h1>
        <p className="text-slate-400 mb-12">
          Upload your resume and job description to get your ATS compatibility score
        </p>

        {/* Error Message */}
        {error && (
          <div className="bg-red-500/10 border border-red-500 rounded-lg mb-6 overflow-hidden">
            <div className="px-6 py-4">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <div className="ml-4 flex-1">
                  <h3 className="text-lg font-semibold text-red-400 mb-2">
                    {error.includes('blocking automated access') ? 'Site Protection Detected' : 'Error'}
                  </h3>
                  <div className="text-red-300 whitespace-pre-line text-sm leading-relaxed">
                    {error}
                  </div>
                  {error.includes('blocking automated access') && (
                    <div className="mt-4 p-4 bg-slate-900/50 rounded-lg border border-slate-700">
                      <p className="text-slate-300 text-sm font-medium mb-2">💡 Quick Tip:</p>
                      <p className="text-slate-400 text-sm">
                        Job sites protect against bots. Simply copy the job description text and paste it in the "Job Description" field below, then try again!
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-8 mb-8">
          {/* Resume Upload */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center">
              <FileText className="w-6 h-6 mr-3 text-emerald-500" />
              Your Resume
            </h2>

            {/* File Upload */}
            <div className="mb-6">
              <label className="block text-slate-300 mb-3">Upload File (PDF, DOC, DOCX, JPG)</label>
              <div className="relative">
                <input
                  type="file"
                  accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.txt"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="resume-upload"
                />
                <label
                  htmlFor="resume-upload"
                  className="flex items-center justify-center w-full px-6 py-4 border-2 border-dashed border-slate-600 rounded-lg cursor-pointer hover:border-emerald-500 transition-colors"
                >
                  <Upload className="w-5 h-5 mr-2 text-slate-400" />
                  <span className="text-slate-300">
                    {resumeFile ? resumeFile.name : "Click to upload"}
                  </span>
                </label>
              </div>
            </div>

            <div className="text-center text-slate-500 mb-6">OR</div>

            {/* Text Input */}
            <div>
              <label className="block text-slate-300 mb-3">Paste Resume Text</label>
              <textarea
                value={resumeText}
                onChange={(e) => {
                  setResumeText(e.target.value);
                  setResumeFile(null); // Clear file if text is entered
                }}
                placeholder="Paste your resume content here..."
                className="w-full h-64 px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none"
              />
            </div>
          </div>

          {/* Job Description */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center">
              <LinkIcon className="w-6 h-6 mr-3 text-emerald-500" />
              Job Description
            </h2>

            {/* URL Input */}
            <div className="mb-6">
              <label className="block text-slate-300 mb-3">Job Posting URL</label>
              <input
                type="url"
                value={jobUrl}
                onChange={(e) => {
                  setJobUrl(e.target.value);
                  setJobText(""); // Clear text if URL is entered
                }}
                placeholder="https://example.com/job-posting"
                className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
              <p className="text-slate-500 text-sm mt-2">
                💡 Tip: Indeed and LinkedIn block automated access. For best results, copy the job description text and paste below.
              </p>
            </div>

            <div className="text-center text-slate-500 mb-6">OR</div>

            {/* Text Input */}
            <div>
              <label className="block text-slate-300 mb-3">Paste Job Description</label>
              <textarea
                value={jobText}
                onChange={(e) => {
                  setJobText(e.target.value);
                  setJobUrl(""); // Clear URL if text is entered
                }}
                placeholder="Paste the job description here..."
                className="w-full h-64 px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none"
              />
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="text-center">
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="px-12 py-4 bg-emerald-500 text-white rounded-lg font-semibold hover:bg-emerald-600 transition-colors disabled:bg-slate-700 disabled:cursor-not-allowed inline-flex items-center"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Analyzing...
              </>
            ) : (
              "Analyze ATS Score"
            )}
          </button>
        </div>
      </div>
    </main>
  );
}
