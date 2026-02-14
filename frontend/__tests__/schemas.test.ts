/**
 * Contract tests for frontend Zod schemas.
 * Validates that schemas correctly accept valid data and reject invalid data.
 */
import {
  AIDetectionResponseSchema,
  ATSScoringResponseSchema,
  DocumentUploadResponseSchema,
  HealthCheckResponseSchema,
  LinguisticFeaturesSchema,
  validateResponse,
} from "../app/lib/schemas";

describe("AIDetectionResponseSchema", () => {
  const validResponse = {
    document_id: "abc-123",
    detection_result: "human",
    confidence_score: 0.85,
    ai_probability: 0.15,
    linguistic_features: {
      sentence_complexity: 0.7,
      vocabulary_diversity: 0.6,
      coherence_score: 0.5,
      transition_patterns: 0.4,
      stylistic_consistency: 0.3,
      burstiness_score: 0.6,
    },
    flagged_sections: [],
    sentence_analysis: [
      {
        text: "Hello world.",
        is_ai: false,
        confidence: 0.8,
        reason: "Looks human.",
        features: {},
      },
    ],
    structured_blocks: [],
    detailed_analysis: ["Point 1"],
    model_versions: {
      "roberta-base-openai-detector": "latest",
      "fakespot-ai/roberta-base-ai-text-detection-v1": "latest",
    },
    analysis_timestamp: "2025-01-01T00:00:00Z",
  };

  it("should accept valid response", () => {
    const result = AIDetectionResponseSchema.safeParse(validResponse);
    expect(result.success).toBe(true);
  });

  it("should reject invalid detection_result", () => {
    const result = AIDetectionResponseSchema.safeParse({
      ...validResponse,
      detection_result: "invalid",
    });
    expect(result.success).toBe(false);
  });

  it("should reject confidence out of range", () => {
    const result = AIDetectionResponseSchema.safeParse({
      ...validResponse,
      confidence_score: 1.5,
    });
    expect(result.success).toBe(false);
  });

  it("should default model_versions to empty when missing", () => {
    const { model_versions, ...rest } = validResponse;
    const result = AIDetectionResponseSchema.safeParse(rest);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.model_versions).toEqual({});
    }
  });

  it("should include model_versions when present", () => {
    const result = AIDetectionResponseSchema.safeParse(validResponse);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(Object.keys(result.data.model_versions).length).toBe(2);
    }
  });
});

describe("ATSScoringResponseSchema", () => {
  const validResponse = {
    document_id: "doc-1",
    job_id: "job-1",
    overall_score: 75,
    keyword_match_score: 80,
    semantic_similarity_score: 70,
    format_score: 75,
    skill_matches: [
      { skill: "Python", matched: true, relevance: 0.9 },
    ],
    gap_analysis: {
      missing_required_skills: ["Go"],
      missing_preferred_skills: ["Rust"],
      recommendations: ["Add Go experience"],
    },
    analysis_timestamp: "2025-01-01T00:00:00Z",
  };

  it("should accept valid response", () => {
    const result = ATSScoringResponseSchema.safeParse(validResponse);
    expect(result.success).toBe(true);
  });

  it("should reject score > 100", () => {
    const result = ATSScoringResponseSchema.safeParse({
      ...validResponse,
      overall_score: 101,
    });
    expect(result.success).toBe(false);
  });
});

describe("LinguisticFeaturesSchema", () => {
  it("should accept valid features", () => {
    const result = LinguisticFeaturesSchema.safeParse({
      sentence_complexity: 0.5,
      vocabulary_diversity: 0.6,
      coherence_score: 0.7,
      transition_patterns: 0.8,
      stylistic_consistency: 0.9,
    });
    expect(result.success).toBe(true);
  });

  it("should reject out-of-range values", () => {
    const result = LinguisticFeaturesSchema.safeParse({
      sentence_complexity: 1.5,
      vocabulary_diversity: 0.6,
      coherence_score: 0.7,
      transition_patterns: 0.8,
      stylistic_consistency: 0.9,
    });
    expect(result.success).toBe(false);
  });
});

describe("HealthCheckResponseSchema", () => {
  it("should accept valid health check", () => {
    const result = HealthCheckResponseSchema.safeParse({
      status: "healthy",
      version: "1.0.0",
      timestamp: "2025-01-01T00:00:00Z",
      services: { database: true, redis: true },
    });
    expect(result.success).toBe(true);
  });

  it("should accept degraded and unhealthy statuses", () => {
    for (const status of ["healthy", "degraded", "unhealthy"]) {
      const result = HealthCheckResponseSchema.safeParse({
        status,
        version: "1.0.0",
        timestamp: "2025-01-01T00:00:00Z",
        services: {},
      });
      expect(result.success).toBe(true);
    }
  });

  it("should reject unknown status", () => {
    const result = HealthCheckResponseSchema.safeParse({
      status: "broken",
      version: "1.0.0",
      timestamp: "2025-01-01T00:00:00Z",
      services: {},
    });
    expect(result.success).toBe(false);
  });
});

describe("validateResponse helper", () => {
  it("should return parsed data on valid input", () => {
    const data = validateResponse(
      DocumentUploadResponseSchema,
      { document_id: "abc" },
      "/test"
    );
    expect(data.document_id).toBe("abc");
  });

  it("should throw on invalid input", () => {
    expect(() =>
      validateResponse(
        DocumentUploadResponseSchema,
        { invalid: true },
        "/test"
      )
    ).toThrow("Invalid response");
  });
});
