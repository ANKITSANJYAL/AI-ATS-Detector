/**
 * API response validation schemas using Zod.
 *
 * Validates backend responses at runtime to catch contract violations
 * early instead of silently rendering broken data.
 */
import { z } from "zod";

// ── AI Detection ──────────────────────────────────────────────────────

export const LinguisticFeaturesSchema = z.object({
  sentence_complexity: z.number().min(0).max(1),
  vocabulary_diversity: z.number().min(0).max(1),
  coherence_score: z.number().min(0).max(1),
  transition_patterns: z.number().min(0).max(1),
  stylistic_consistency: z.number().min(0).max(1),
  burstiness_score: z.number().min(0).max(1).optional().default(0.5),
});

export const SentenceAnalysisSchema = z.object({
  text: z.string(),
  is_ai: z.boolean(),
  confidence: z.number().min(0).max(1),
  reason: z.string().optional().default(""),
  features: z.record(z.string(), z.unknown()).optional().default({}),
  block_index: z.number().optional(),
});

export const StructuredBlockSchema = z.object({
  text: z.string(),
  type: z.string().optional(),
  level: z.number().optional(),
});

export const AIDetectionResponseSchema = z.object({
  document_id: z.string(),
  detection_result: z.enum(["human", "ai_generated", "mixed"]),
  confidence_score: z.number().min(0).max(1),
  ai_probability: z.number().min(0).max(1),
  linguistic_features: LinguisticFeaturesSchema,
  flagged_sections: z.array(z.string()).default([]),
  sentence_analysis: z.array(SentenceAnalysisSchema).default([]),
  structured_blocks: z.array(z.record(z.string(), z.unknown())).default([]),
  detailed_analysis: z.array(z.string()).default([]),
  model_versions: z.record(z.string(), z.string()).default({}),
  analysis_timestamp: z.string(),
});

export type AIDetectionResponse = z.infer<typeof AIDetectionResponseSchema>;
export type SentenceAnalysis = z.infer<typeof SentenceAnalysisSchema>;
export type LinguisticFeatures = z.infer<typeof LinguisticFeaturesSchema>;

// ── ATS Scoring ───────────────────────────────────────────────────────

export const SkillMatchSchema = z.object({
  skill: z.string(),
  matched: z.boolean(),
  relevance: z.number().min(0).max(1),
});

export const GapAnalysisSchema = z.object({
  missing_required_skills: z.array(z.string()),
  missing_preferred_skills: z.array(z.string()),
  recommendations: z.array(z.string()),
});

export const ATSScoringResponseSchema = z.object({
  document_id: z.string(),
  job_id: z.string(),
  overall_score: z.number().min(0).max(100),
  keyword_match_score: z.number().min(0).max(100),
  semantic_similarity_score: z.number().min(0).max(100),
  format_score: z.number().min(0).max(100),
  skill_matches: z.array(SkillMatchSchema),
  gap_analysis: GapAnalysisSchema,
  analysis_timestamp: z.string(),
});

export type ATSScoringResponse = z.infer<typeof ATSScoringResponseSchema>;

// ── Document Upload ───────────────────────────────────────────────────

export const DocumentUploadResponseSchema = z.object({
  document_id: z.string(),
  upload_url: z.string().optional(),
  expires_at: z.string().optional(),
  text_content: z.string().optional(),
});

export type DocumentUploadResponse = z.infer<typeof DocumentUploadResponseSchema>;

// ── Health Check ──────────────────────────────────────────────────────

export const HealthCheckResponseSchema = z.object({
  status: z.enum(["healthy", "degraded", "unhealthy"]),
  version: z.string(),
  timestamp: z.string(),
  services: z.record(z.string(), z.boolean()),
});

export type HealthCheckResponse = z.infer<typeof HealthCheckResponseSchema>;

// ── AI Humanizer ──────────────────────────────────────────────────────

export const RewriteOptionSchema = z.object({
  text: z.string(),
  approach: z.string(),
});

export const HumanizeResponseSchema = z.object({
  original_text: z.string(),
  rewrites: z.array(RewriteOptionSchema),
  explanation: z.string(),
  ai_tells: z.array(z.string()).default([]),
});

export const HumanizeBatchResponseSchema = z.object({
  document_id: z.string(),
  results: z.array(HumanizeResponseSchema),
  tone: z.string(),
});

export type RewriteOption = z.infer<typeof RewriteOptionSchema>;
export type HumanizeResponse = z.infer<typeof HumanizeResponseSchema>;
export type HumanizeBatchResponse = z.infer<typeof HumanizeBatchResponseSchema>;

// ── Resume Optimizer ──────────────────────────────────────────────────

export const DiffStatsSchema = z.object({
  words_added: z.number(),
  words_removed: z.number(),
  original_line_count: z.number(),
  optimized_line_count: z.number(),
  original_word_count: z.number(),
  optimized_word_count: z.number(),
});

export const ChangeItemSchema = z.object({
  section: z.string(),
  change: z.string(),
  reason: z.string(),
});

export const SectionImprovementSchema = z.object({
  section: z.string(),
  before: z.string(),
  after: z.string(),
  impact: z.enum(["high", "medium", "low"]),
});

export const ResumeOptimizeResponseSchema = z.object({
  document_id: z.string(),
  job_id: z.string(),
  optimized_resume: z.string(),
  changes: z.array(ChangeItemSchema),
  section_improvements: z.array(SectionImprovementSchema),
  keywords_added: z.array(z.string()),
  estimated_score_improvement: z.number(),
  diff_stats: DiffStatsSchema,
  generated_at: z.string(),
});

export type DiffStats = z.infer<typeof DiffStatsSchema>;
export type ChangeItem = z.infer<typeof ChangeItemSchema>;
export type SectionImprovement = z.infer<typeof SectionImprovementSchema>;
export type ResumeOptimizeResponse = z.infer<typeof ResumeOptimizeResponseSchema>;

// ── Validation helper ─────────────────────────────────────────────────

/**
 * Validate and parse an API response against a Zod schema.
 * Returns the parsed data or throws a descriptive error.
 */
export function validateResponse<T>(schema: z.ZodType<T>, data: unknown, endpoint: string): T {
  const result = schema.safeParse(data);
  if (!result.success) {
    console.error(
      `API contract violation from ${endpoint}:`,
      result.error.format()
    );
    throw new Error(
      `Invalid response from ${endpoint}: ${result.error.issues.map(i => i.message).join(", ")}`
    );
  }
  return result.data;
}
