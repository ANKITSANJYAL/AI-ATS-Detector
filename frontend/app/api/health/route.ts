import { NextResponse } from "next/server";

/**
 * Frontend health check endpoint.
 * Used by Docker HEALTHCHECK and load balancers to verify the frontend is serving.
 */
export async function GET() {
  return NextResponse.json(
    {
      status: "healthy",
      service: "frontend",
      timestamp: new Date().toISOString(),
    },
    { status: 200 }
  );
}
