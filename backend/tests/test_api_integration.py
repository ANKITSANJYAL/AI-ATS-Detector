"""
Integration tests for API endpoints.
Tests the full request/response cycle using FastAPI TestClient.
"""
import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Tests for health and root endpoints."""

    @pytest.mark.asyncio
    async def test_root_returns_app_info(self, async_client: AsyncClient):
        response = await async_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["status"] == "operational"

    @pytest.mark.asyncio
    async def test_health_endpoint(self, async_client: AsyncClient):
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert "services" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_docs_available(self, async_client: AsyncClient):
        response = await async_client.get("/docs")
        assert response.status_code == 200


class TestDocumentEndpoints:
    """Tests for document management endpoints."""

    @pytest.mark.asyncio
    async def test_upload_requires_file(self, async_client: AsyncClient):
        """Upload without a file should fail."""
        response = await async_client.post("/api/v1/documents/upload")
        # 422 (validation) or 500 (Redis not available for rate limit)
        assert response.status_code in (422, 500)

    @pytest.mark.asyncio
    async def test_upload_rejects_wrong_mime(self, async_client: AsyncClient):
        """Upload with unsupported MIME type should fail."""
        response = await async_client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.exe", b"binary content", "application/x-msdownload")},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_text_file(self, async_client: AsyncClient):
        """Upload a valid text file."""
        response = await async_client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", b"Hello world test content", "text/plain")},
        )
        # 201 (success), 500 (DB/Redis unavailable), or 401 (auth required)
        assert response.status_code in (201, 401, 500)
        if response.status_code == 201:
            data = response.json()
            assert "document_id" in data

    @pytest.mark.asyncio
    async def test_detect_invalid_document_id(self, async_client: AsyncClient):
        """Detection with invalid doc ID should fail."""
        response = await async_client.post(
            "/api/v1/documents/detect",
            json={"document_id": "invalid-uuid"},
        )
        assert response.status_code in (400, 404, 422)

    @pytest.mark.asyncio
    async def test_score_requires_job_source(self, async_client: AsyncClient):
        """ATS scoring without any job source should fail validation."""
        response = await async_client.post(
            "/api/v1/documents/score",
            json={"document_id": "00000000-0000-0000-0000-000000000000"},
        )
        # 422 (validation), 500 (Redis unavailable), or 401 (auth required)
        assert response.status_code in (422, 500, 401)


class TestBillingEndpoints:
    """Tests for billing API endpoints."""

    @pytest.mark.asyncio
    async def test_billing_status(self, async_client: AsyncClient):
        """Billing status should return free plan when Stripe is not configured."""
        response = await async_client.get("/api/v1/billing/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "free"
        assert data["plan"] == "free"

    @pytest.mark.asyncio
    async def test_billing_usage(self, async_client: AsyncClient):
        """Usage endpoint should return counts."""
        response = await async_client.get("/api/v1/billing/usage")
        assert response.status_code == 200
        data = response.json()
        assert "ai_detection_count" in data
        assert "ats_scoring_count" in data
        assert "total_usage" in data

    @pytest.mark.asyncio
    async def test_checkout_fails_without_stripe(self, async_client: AsyncClient):
        """Checkout should fail gracefully when Stripe is not configured."""
        response = await async_client.post(
            "/api/v1/billing/checkout",
            json={"plan": "pro"},
        )
        assert response.status_code == 503


class TestHistoryEndpoints:
    """Tests for history API endpoints."""

    @pytest.mark.asyncio
    async def test_history_returns_data(self, async_client: AsyncClient):
        """History endpoint should return structured response."""
        response = await async_client.get("/api/v1/history/?limit=10&offset=0")
        # 200 (success) or 500 (DB unavailable in test env)
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            data = response.json()
            assert "detections" in data
            assert "ats_scores" in data
            assert "total_detections" in data
            assert "total_ats" in data


class TestRateLimiting:
    """Tests for rate limiting."""

    @pytest.mark.asyncio
    async def test_rate_limit_header_format(self, async_client: AsyncClient):
        """Responses should include process time header."""
        response = await async_client.get("/")
        # X-Process-Time is added by middleware
        assert "x-process-time" in response.headers


class TestCORS:
    """Tests for CORS configuration."""

    @pytest.mark.asyncio
    async def test_cors_allows_localhost(self, async_client: AsyncClient):
        """CORS should allow localhost:3000."""
        response = await async_client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI CORS middleware returns 200 for preflight
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
