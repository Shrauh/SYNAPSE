import pytest
from app.api.alerts import _processed_alerts

@pytest.fixture(autouse=True)
def clear_processed_alerts():
    _processed_alerts.clear()
    yield

@pytest.mark.asyncio
async def test_alert_webhook_firing(client):
    payload = {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "HighLatency",
                    "service": "payment-service",
                    "severity": "critical"
                },
                "fingerprint": "fp123"
            }
        ]
    }
    response = await client.post("/api/v1/alerts/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["firing"] == 1
    assert len(data["triggered"]) == 1
    assert "fp123" in _processed_alerts

@pytest.mark.asyncio
async def test_alert_webhook_duplicate(client):
    payload = {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "ErrorSpike"},
                "fingerprint": "dup123"
            }
        ]
    }
    await client.post("/api/v1/alerts/webhook", json=payload)
    response = await client.post("/api/v1/alerts/webhook", json=payload)
    data = response.json()
    assert data["firing"] == 1
    assert len(data["skipped_duplicates"]) == 1
    assert data["skipped_duplicates"][0] == "dup123"

@pytest.mark.asyncio
async def test_alert_webhook_resolved(client):
    _processed_alerts["res123"] = "incident_id"
    payload = {
        "status": "resolved",
        "alerts": [
            {
                "status": "resolved",
                "labels": {"alertname": "MemoryLeak"},
                "fingerprint": "res123"
            }
        ]
    }
    response = await client.post("/api/v1/alerts/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["resolved"] == 1
    assert "res123" not in _processed_alerts

@pytest.mark.asyncio
async def test_alert_test_endpoint(client):
    response = await client.post("/api/v1/alerts/test?service=auth-service&fault_type=latency_spike")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["firing"] == 1
    assert len(data["triggered"]) == 1
    assert data["triggered"][0]["service"] == "auth-service"

@pytest.mark.asyncio
async def test_alert_status_endpoint(client):
    response = await client.get("/api/v1/alerts/status")
    assert response.status_code == 200
    data = response.json()
    assert "active_alerts" in data
    assert "tracked" in data
