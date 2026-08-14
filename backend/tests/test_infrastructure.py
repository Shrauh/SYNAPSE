"""
SYNAPSE Health Check Integration Tests.

Tests the complete system health including Docker services,
Prometheus connection, and Ollama availability.
"""
import httpx
import pytest


SERVICES = {
    "api-gateway": "http://localhost:8080",
    "auth-service": "http://localhost:8081",
    "user-service": "http://localhost:8082",
    "order-service": "http://localhost:8083",
    "payment-service": "http://localhost:8085",
}


@pytest.mark.skipif(True, reason="Requires Docker services running")
class TestInfrastructureHealth:
    """Integration tests for Docker infrastructure."""

    @pytest.mark.asyncio
    async def test_all_services_healthy(self):
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, url in SERVICES.items():
                resp = await client.get(f"{url}/health")
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "healthy"
                assert data["service"] == name

    @pytest.mark.asyncio
    async def test_metrics_endpoints(self):
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, url in SERVICES.items():
                resp = await client.get(f"{url}/metrics")
                assert resp.status_code == 200
                assert "http_requests_total" in resp.text

    @pytest.mark.asyncio
    async def test_prometheus_scraping(self):
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://localhost:9090/api/v1/targets")
            assert resp.status_code == 200
            targets = resp.json()["data"]["activeTargets"]
            assert len(targets) >= 5

    @pytest.mark.asyncio
    async def test_fault_injection(self):
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Inject
            resp = await client.post(
                "http://localhost:8083/fault",
                params={"latency_ms": 500},
            )
            assert resp.status_code == 200
            # Clear
            resp = await client.post("http://localhost:8083/fault/clear")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_ollama_connection(self):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://localhost:11434/api/tags")
                assert resp.status_code == 200
                models = resp.json().get("models", [])
                assert len(models) > 0
        except httpx.ConnectError:
            pytest.skip("Ollama not running")
