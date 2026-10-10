import pytest

@pytest.mark.asyncio
async def test_get_active_system(client):
    response = await client.get("/api/v1/system/active")
    assert response.status_code == 200
    data = response.json()
    assert "system" in data
    assert "services" in data

@pytest.mark.asyncio
async def test_list_available_systems(client):
    response = await client.get("/api/v1/system/available")
    assert response.status_code == 200
    data = response.json()
    assert "available" in data
    
    systems = [s["id"] for s in data["available"]]
    assert "online-boutique" in systems
    assert "fintech" in systems
    assert "healthcare" in systems

@pytest.mark.asyncio
async def test_switch_to_fintech(client):
    response = await client.post("/api/v1/system/switch", json={"system": "fintech"})
    assert response.status_code == 200
    data = response.json()
    assert data["system"] == "fintech"
    assert "transaction-service" in data["services"]

@pytest.mark.asyncio
async def test_switch_to_healthcare(client):
    response = await client.post("/api/v1/system/switch", json={"system": "healthcare"})
    assert response.status_code == 200
    data = response.json()
    assert data["system"] == "healthcare"
    assert "patient-gateway" in data["services"]

@pytest.mark.asyncio
async def test_invalid_system_switch(client):
    response = await client.post("/api/v1/system/switch", json={"system": "invalid-sys"})
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data

@pytest.mark.asyncio
async def test_switch_back_to_default(client):
    response = await client.post("/api/v1/system/switch", json={"system": "default"})
    assert response.status_code == 200
    data = response.json()
    assert data["system"] == "default"
