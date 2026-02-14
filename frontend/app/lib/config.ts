/**
 * Application configuration.
 * Centralizes all environment-dependent settings.
 */

export const config = {
  /** Backend API base URL — set via NEXT_PUBLIC_API_URL env var */
  apiUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",

  /** API v1 prefix */
  apiV1: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1`,
} as const;
