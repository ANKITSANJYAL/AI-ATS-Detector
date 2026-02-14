// Type declaration for optional @sentry/nextjs dependency
// This module is only used at runtime when NEXT_PUBLIC_SENTRY_DSN is set
declare module "@sentry/nextjs" {
  export function captureException(
    error: Error,
    context?: {
      tags?: Record<string, string | undefined>;
      extra?: Record<string, unknown>;
      user?: { id: string };
    }
  ): void;

  export function addBreadcrumb(breadcrumb: {
    message: string;
    data?: Record<string, unknown>;
    level?: string;
  }): void;
}
