/**
 * Lightweight error reporting utility.
 * In production, configure NEXT_PUBLIC_SENTRY_DSN to enable Sentry.
 * For full instrumentation, install @sentry/nextjs and run its setup wizard.
 */

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

interface ErrorContext {
  component?: string;
  action?: string;
  userId?: string;
  extra?: Record<string, unknown>;
}

/**
 * Report an error to the console (and Sentry if configured via @sentry/nextjs).
 * This is a thin abstraction so the app never needs to import Sentry directly.
 */
export function captureError(error: Error | unknown, context?: ErrorContext) {
  const err = error instanceof Error ? error : new Error(String(error));

  // Always log locally
  console.error("[Error]", context?.component ?? "unknown", err.message, context);

  // If @sentry/nextjs is installed and initialized, delegate to it
  if (SENTRY_DSN) {
    try {
      // Dynamic import to avoid build errors when @sentry/nextjs isn't installed
      import("@sentry/nextjs").then((Sentry) => {
        Sentry.captureException(err, {
          tags: {
            component: context?.component,
            action: context?.action,
          },
          extra: context?.extra,
          ...(context?.userId && { user: { id: context.userId } }),
        });
      }).catch(() => {
        // @sentry/nextjs not installed — already logged to console
      });
    } catch {
      // Fallback: do nothing, error was already logged to console
    }
  }
}

/**
 * Log a breadcrumb for debugging context.
 */
export function addBreadcrumb(message: string, data?: Record<string, unknown>) {
  if (process.env.NODE_ENV === "development") {
    console.debug("[Breadcrumb]", message, data);
  }

  if (SENTRY_DSN) {
    try {
      import("@sentry/nextjs").then((Sentry) => {
        Sentry.addBreadcrumb({ message, data, level: "info" });
      }).catch(() => {});
    } catch {
      // noop
    }
  }
}
