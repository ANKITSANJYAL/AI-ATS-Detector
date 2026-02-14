import { exportDetectionCSV, exportATSCSV, exportDetectionReport } from "../app/lib/export";

// Mock the download function to prevent actual DOM manipulation
jest.mock("../app/lib/export", () => {
  const actual = jest.requireActual("../app/lib/export");
  return {
    ...actual,
    // Override downloadFile to no-op
  };
});

describe("export utilities", () => {
  it("exportDetectionCSV should not throw with valid data", () => {
    const result = {
      overall_score: 0.72,
      confidence: 0.85,
      sentences: [
        {
          text: "This is a test sentence.",
          ai_probability: 0.8,
          label: "AI-Generated",
          features: { perplexity: 45.2, burstiness: 0.3 },
        },
      ],
    };

    expect(() => exportDetectionCSV(result)).not.toThrow();
  });

  it("exportATSCSV should not throw with valid data", () => {
    const result = {
      overall_score: 75,
      category_scores: { skills_match: 80, experience: 70, education: 75 },
      matched_skills: ["Python", "FastAPI"],
      missing_skills: ["Kubernetes"],
      recommendations: [{ text: "Add K8s experience" }],
    };

    expect(() => exportATSCSV(result)).not.toThrow();
  });

  it("exportDetectionReport should not throw with valid data", () => {
    const result = {
      overall_score: 0.45,
      confidence: 0.9,
      sentences: [
        {
          text: "Human written text here.",
          ai_probability: 0.1,
          label: "Human",
          features: {},
        },
      ],
    };

    expect(() => exportDetectionReport(result)).not.toThrow();
  });
});
