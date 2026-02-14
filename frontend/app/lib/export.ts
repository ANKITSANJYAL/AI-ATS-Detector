/**
 * Result export utilities.
 * Handles PDF and CSV export of analysis results.
 */

/**
 * Export AI detection results as a CSV file.
 */
export function exportDetectionCSV(results: any): void {
  const lines: string[] = [
    "Document ID,Detection Result,AI Probability,Confidence Score,Timestamp",
    [
      results.document_id,
      results.detection_result,
      `${(results.ai_probability * 100).toFixed(1)}%`,
      `${(results.confidence_score * 100).toFixed(1)}%`,
      results.analysis_timestamp || new Date().toISOString(),
    ].join(","),
    "",
    "Sentence,Is AI,Confidence,Reason",
  ];

  (results.sentence_analysis || []).forEach((s: any) => {
    const text = `"${(s.text || "").replace(/"/g, '""')}"`;
    lines.push(
      [text, s.is_ai ? "Yes" : "No", `${(s.confidence * 100).toFixed(1)}%`, `"${s.reason || ""}"`].join(",")
    );
  });

  downloadFile(lines.join("\n"), `ai-detection-${results.document_id}.csv`, "text/csv");
}

/**
 * Export ATS scoring results as a CSV file.
 */
export function exportATSCSV(results: any): void {
  const lines: string[] = [
    "Document ID,Job ID,Overall Score,Keyword Score,Semantic Score,Format Score,Timestamp",
    [
      results.document_id,
      results.job_id,
      results.overall_score?.toFixed(1),
      results.keyword_match_score?.toFixed(1),
      results.semantic_similarity_score?.toFixed(1),
      results.format_score?.toFixed(1),
      results.analysis_timestamp || new Date().toISOString(),
    ].join(","),
    "",
    "Skill,Matched,Relevance",
  ];

  (results.skill_matches || []).forEach((sm: any) => {
    lines.push(
      [`"${sm.skill}"`, sm.matched ? "Yes" : "No", `${(sm.relevance * 100).toFixed(0)}%`].join(",")
    );
  });

  lines.push("", "Missing Required Skills");
  (results.gap_analysis?.missing_required_skills || []).forEach((s: string) => {
    lines.push(`"${s}"`);
  });

  lines.push("", "Recommendations");
  (results.gap_analysis?.recommendations || results.recommendations || []).forEach((r: string) => {
    lines.push(`"${r.replace(/"/g, '""')}"`);
  });

  downloadFile(lines.join("\n"), `ats-score-${results.document_id}.csv`, "text/csv");
}

/**
 * Export results as a plain-text report.
 */
export function exportDetectionReport(results: any): void {
  const prob = (results.ai_probability * 100).toFixed(1);
  const conf = (results.confidence_score * 100).toFixed(1);

  let report = `AI CONTENT DETECTION REPORT
${"=".repeat(50)}
Document ID: ${results.document_id}
Detection Result: ${results.detection_result?.toUpperCase()}
AI Probability: ${prob}%
Confidence: ${conf}%
Generated: ${new Date().toISOString()}

LINGUISTIC FEATURES
${"─".repeat(50)}
Sentence Complexity: ${(results.linguistic_features?.sentence_complexity * 100).toFixed(0)}%
Vocabulary Diversity: ${(results.linguistic_features?.vocabulary_diversity * 100).toFixed(0)}%
Coherence Score: ${(results.linguistic_features?.coherence_score * 100).toFixed(0)}%
Transition Patterns: ${(results.linguistic_features?.transition_patterns * 100).toFixed(0)}%
Stylistic Consistency: ${(results.linguistic_features?.stylistic_consistency * 100).toFixed(0)}%
Burstiness: ${(results.linguistic_features?.burstiness_score * 100).toFixed(0)}%

SENTENCE-LEVEL ANALYSIS
${"─".repeat(50)}
`;

  (results.sentence_analysis || []).forEach((s: any, i: number) => {
    report += `[${i + 1}] ${s.is_ai ? "🤖 AI" : "✅ Human"} (${(s.confidence * 100).toFixed(0)}%) ${s.text}\n`;
    if (s.reason) report += `    Reason: ${s.reason}\n`;
    report += "\n";
  });

  downloadFile(report, `ai-detection-report-${results.document_id}.txt`, "text/plain");
}

function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
