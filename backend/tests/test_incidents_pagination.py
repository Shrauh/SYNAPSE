import pytest
import asyncio
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_incident_pagination_page_1(client):
    response = await client.get("/api/v1/incidents?page=1")
    assert response.status_code == 200
    data = response.json()
    assert "incidents" in data
    assert "total" in data
    assert isinstance(data["total"], int)
    assert data["page"] == 1

@pytest.mark.asyncio
async def test_incident_pagination_page_0(client):
    response = await client.get("/api/v1/incidents?page=0")
    # validation error for ge=1
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_incident_pagination_per_page_100(client):
    response = await client.get("/api/v1/incidents?page=1&per_page=100")
    assert response.status_code == 200
    data = response.json()
    assert data["per_page"] == 100
    assert isinstance(data["total"], int)
