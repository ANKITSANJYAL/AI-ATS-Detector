import { config } from "../app/lib/config";

describe("config", () => {
  it("should have apiUrl and apiV1 defined", () => {
    expect(config.apiUrl).toBeDefined();
    expect(config.apiV1).toBeDefined();
  });

  it("apiV1 should end with /api/v1", () => {
    expect(config.apiV1).toMatch(/\/api\/v1$/);
  });
});
