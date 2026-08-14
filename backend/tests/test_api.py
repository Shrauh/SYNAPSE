"""
SYNAPSE Tests — API endpoint and pipeline tests.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.database import Base, engine
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    """Async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ──────────────────────────────────────────────
# Health & System
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "SYNAPSE"


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "components" in data


@pytest.mark.asyncio
async def test_metrics(client):
    response = await client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_incidents" in data


# ──────────────────────────────────────────────
# Graph
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_graph_current(client):
    response = await client.get("/api/v1/graph/current")
    assert response.status_code == 200
    data = response.json()
    assert len(data["nodes"]) == 10
    assert len(data["edges"]) == 15
    assert data["metadata"]["total_services"] == 10


# ──────────────────────────────────────────────
# Incidents
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_incidents_empty(client):
    response = await client.get("/api/v1/incidents")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_create_incident(client):
    response = await client.post("/api/v1/incidents", json={
        "title": "Test incident",
        "description": "Test description",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "analyzing"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_incident(client):
    # Create first
    create_resp = await client.post("/api/v1/incidents", json={
        "title": "Test incident for get",
    })
    inc_id = create_resp.json()["id"]

    # Fetch
    response = await client.get(f"/api/v1/incidents/{inc_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Test incident for get"


@pytest.mark.asyncio
async def test_get_incident_not_found(client):
    response = await client.get("/api/v1/incidents/nonexistent")
    assert response.status_code == 404


# ──────────────────────────────────────────────
# RCA
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rca_report_not_found(client):
    response = await client.get("/api/v1/incidents/fake_id/report")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_model_status(client):
    response = await client.get("/api/v1/model/status")
    assert response.status_code == 200
    data = response.json()
    assert "deic_gnn" in data
    assert "maml" in data
    assert "continual_learning" in data
