#!/usr/bin/env bash
# =============================================================================
# generate_sdk.sh — Generate a TypeScript client SDK from the backend OpenAPI spec.
#
# Prerequisites:
#   - The backend server must be running on http://localhost:8000
#   - npx (Node.js) must be available
#
# Usage:
#   chmod +x scripts/generate_sdk.sh
#   ./scripts/generate_sdk.sh
#
# The generated client will be placed in frontend/app/lib/api-client/
# =============================================================================

set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
OUTPUT_DIR="frontend/app/lib/api-client"
SPEC_FILE="openapi.json"

echo "📥 Fetching OpenAPI spec from ${BACKEND_URL}/openapi.json ..."
curl -sS "${BACKEND_URL}/openapi.json" -o "${SPEC_FILE}"

echo "🏗️  Generating TypeScript client SDK ..."
npx @openapitools/openapi-generator-cli generate \
  -i "${SPEC_FILE}" \
  -g typescript-fetch \
  -o "${OUTPUT_DIR}" \
  --additional-properties=supportsES6=true,npmName=docguard-api-client,typescriptThreePlus=true

echo "🧹 Cleaning up temp spec file ..."
rm -f "${SPEC_FILE}"

echo "✅ SDK generated at ${OUTPUT_DIR}"
echo ""
echo "Usage in frontend:"
echo "  import { DocumentsApi, Configuration } from '@/app/lib/api-client';"
echo "  const api = new DocumentsApi(new Configuration({ basePath: config.apiUrl }));"
